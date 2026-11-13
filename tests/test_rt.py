import csv
import importlib.util
import json
from pathlib import Path

import pytest
import yaml

from qnx_porter import rt, rt_bench

LIB = """#include <stdlib.h>
/* malloc( in a comment is not a call */
static const char *s = "free(this string)";
int parse(struct ctx *c, const char *buf)
{
    char *copy = malloc(16);          /* heap */
    c->read(c, buf);                  /* a member call, not read(2) */
    int n = read(c->fd, copy, 16);    /* blocking I/O */
    usleep(10);
    pthread_mutex_lock(&c->lock);
    free(copy);
    return n;
}
"""


def test_scan_counts_real_calls_only(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "parse.c").write_text(LIB)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "t.c").write_text("int main(void){ fork(); system(\"x\"); return 0; }\n")
    r = rt.scan(tmp_path)
    h = r["hazards"]
    assert (h["heap"]["count"], h["blocking_io"]["count"], h["sleep"]["count"], h["locks"]["count"]) == (2, 1, 1, 1)
    assert h["process"]["count"] == 0  # tests are not the library
    assert h["heap"]["examples"][0] == "src/parse.c:6" and h["blocking_io"]["examples"] == ["src/parse.c:8"]
    assert r["files"] == 1
    assert r["static_score"] == 100 - 20 - 20 - 10 - 10


def test_scan_counts_lock_and_thread_use_not_type_names(tmp_path):
    (tmp_path / "q.cc").write_text("std::mutex m; std::thread worker_;\n"
                                   "void f(){ std::unique_lock<std::mutex> l(m); pthread_cond_wait(&c, &mu); }\n"
                                   "void g(){ worker_ = std::thread([]{}); std::thread t(run); }\n"
                                   "auto h(std::thread::id i) { return i; }\n")
    h = rt.scan(tmp_path)["hazards"]
    assert (h["locks"]["count"], h["threads"]["count"]) == (2, 2)


def test_scan_skips_tests_tools_and_demos_but_not_the_library_itself(tmp_path):
    for f in ("mptest/a.c", "test_libFLAC/a.c", "cli/a.c", "src/opus_demo.c", "src/conv_test.c",
              "googletest/src/gtest-death-test.cc", "src/util.c", "include/benchmark/benchmark.h",
              "src/benchmark_register.cc"):
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / f).write_text("int x;\n")
    def kept(keep=""):
        return [rel for _, rel in rt.sources(tmp_path, keep)]
    assert kept() == ["src/util.c"]
    assert kept("benchmark") == ["include/benchmark/benchmark.h", "src/benchmark_register.cc", "src/util.c"]
    assert kept("googletest") == ["googletest/src/gtest-death-test.cc", "src/util.c"]  # a test framework's own code


def test_clean_library_scores_100(tmp_path):
    (tmp_path / "m.c").write_text("int add(int a, int b) { return a + b; }\n")
    assert rt.scan(tmp_path)["static_score"] == 100


def test_bench_source_uses_qnx_timing_and_scheduling_apis():
    src = rt_bench.source({"includes": '#include "zlib.h"', "call": "return 0;"})
    for api in ("ClockCycles()", "SYSPAGE_ENTRY(qtime)->cycles_per_sec", "QTIME_FLAG_GLOBAL_CLOCKCYCLES",
                "SCHED_FIFO", "_NTO_TCTL_RUNMASK", '#include "zlib.h"', "static int one_call(void) { return 0; }",
                "p999_us"):
        assert api in src
    assert "@" not in src  # every placeholder filled


def test_rt_score_penalises_jitter_under_load():
    runs = {"idle": {"median_us": 10.0}, "loaded": {"p99_us": 40.0}}
    assert rt_bench.rt_score(80, runs) == 60          # p99 under load is 4x the idle median: 2 doublings
    assert rt_bench.rt_score(80, {"idle": {"median_us": 10.0}, "loaded": {"p99_us": 9.0}}) == 80
    assert rt_bench.rt_score(80, {"idle": {"median_us": 1.0}, "loaded": {"p99_us": 1e6}}) == 50  # capped at 30
    assert rt_bench.rt_score(80, {"idle": {"median_us": 1.0}, "loaded": {"error": "exit 3"}}) is None
    assert rt_bench.rt_score(80, None) is None


def test_every_bench_spec_has_a_call_and_what():
    specs = yaml.safe_load((Path(__file__).parents[1] / "bench" / "specs.yaml").read_text())
    libs = {k: v for k, v in specs.items() if not k.startswith("_")}
    assert len(libs) >= 15
    assert all("call" in v and "what" in v for v in libs.values())


def _rt_report(monkeypatch, root):
    spec = importlib.util.spec_from_file_location("rt_report", Path(__file__).parents[1] / "scripts" / "rt_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(mod, "ROOT", root)
    return mod


def test_scan_only_needs_no_target_and_reports_absent_sources(tmp_path, monkeypatch):
    ports = tmp_path / "ports"
    for lib in ("good", "gone"):
        (ports / lib).mkdir(parents=True)
        (ports / lib / "report.json").write_text(json.dumps({"library": lib, "arch": "x86_64", "commit": "abc"}))
    (ports / "good" / "work" / "src").mkdir(parents=True)
    (ports / "good" / "work" / "src" / "a.c").write_text(LIB)
    mod = _rt_report(monkeypatch, tmp_path)
    monkeypatch.setattr(mod.qnx, "sdp_env", lambda: pytest.fail("scan-only must not need the SDP"))
    assert mod.main(["--scan-only", "--ports", str(ports)]) == 0
    rows = {r["library"]: r for r in csv.DictReader((tmp_path / "results" / "rt_scan.csv").open())}
    assert rows["good"]["sources"] == "scanned" and rows["good"]["heap"] == "2" and rows["good"]["static_score"] == "40"
    assert rows["gone"]["sources"] == "absent" and rows["gone"]["heap"] == ""
    # a second run for one library keeps the other row
    assert mod.main(["--scan-only", "--ports", str(ports), "--only", "gone"]) == 0
    assert len(list(csv.DictReader((tmp_path / "results" / "rt_scan.csv").open()))) == 2
    assert not (ports / "good" / "rt.json").exists()


def test_full_run_writes_rt_json_and_csv_saying_what_was_measured(tmp_path, monkeypatch):
    """The target path with ssh and qcc replaced by fakes; the figures below are test data, not measurements."""
    ports = tmp_path / "campaign" / "ports"
    for lib in ("zlib", "nospec"):
        (ports / lib / "work" / "src").mkdir(parents=True)
        (ports / lib / "work" / "build").mkdir()
        (ports / lib / "work" / "src" / "a.c").write_text(LIB)
        (ports / lib / "report.json").write_text(json.dumps({"library": lib, "arch": "x86_64", "commit": "c1",
                                                             "build_result": "built"}))
    (tmp_path / "bench").mkdir()
    (tmp_path / "bench" / "specs.yaml").write_text((Path(__file__).parents[1] / "bench" / "specs.yaml").read_text())
    mod = _rt_report(monkeypatch, tmp_path)
    run = {"n": 1000, "cpus": 4, "min_us": 1.0, "median_us": 2.0, "p99_us": 3.0, "p999_us": 4.0, "max_us": 5.0}
    monkeypatch.setattr(mod.qnx, "sdp_env", lambda: {"QNX_HOST": "/x"})
    monkeypatch.setattr(mod.Target, "uname", lambda self: "QNX qnx-porter 8.0.0 x86pc x86_64")
    monkeypatch.setattr(mod.rt_bench, "compile_bench", lambda *a: (True, ""))
    monkeypatch.setattr(mod.rt_bench, "run_bench", lambda t, b, lib, n: {k: dict(run) for k in rt_bench.RUNS})
    assert mod.main(["--target", "root@10.0.0.1", "--ports", str(ports), "--n", "1000"]) == 0
    out = json.loads((tmp_path / "ports" / "zlib" / "rt.json").read_text())
    b = out["bench"]
    assert (b["iterations"], b["platform"], b["call"]) == (1000, "qemu", "compress 1 KB (default level)")
    assert "NOT representative" in b["timing_note"] and "1000 timed calls" in b["measured"]
    assert set(b["runs"]) == {"idle", "loaded", "loaded_isolated"} and out["score_basis"].startswith("static scan and")
    nospec = json.loads((tmp_path / "ports" / "nospec" / "rt.json").read_text())
    assert nospec["bench"]["error"].startswith("no call spec") and nospec["score_basis"] == "static scan only"
    rows = list(csv.DictReader((tmp_path / "results" / "rt.csv").open()))
    assert [r["library"] for r in rows] == ["zlib"]
    assert (rows[0]["loaded_isolated_p999_us"], rows[0]["cpus"], rows[0]["error"]) == ("4.0", "4", "")


def test_full_run_needs_a_target(tmp_path, monkeypatch):
    mod = _rt_report(monkeypatch, tmp_path)
    with pytest.raises(SystemExit):
        mod.main([])
