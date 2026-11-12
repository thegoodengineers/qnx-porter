from qnx_porter import rt

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
    assert (h["heap"]["count"], h["blocking_io"]["count"], h["sleep"]["count"], h["mutexes"]["count"]) == (2, 1, 1, 1)
    assert h["process"]["count"] == 0  # tests are not the library
    assert h["heap"]["examples"][0] == "src/parse.c:6" and h["blocking_io"]["examples"] == ["src/parse.c:8"]
    assert r["files"] == 1
    assert r["static_score"] == 100 - 20 - 20 - 10 - 10


def test_clean_library_scores_100(tmp_path):
    (tmp_path / "m.c").write_text("int add(int a, int b) { return a + b; }\n")
    assert rt.scan(tmp_path)["static_score"] == 100


def test_bench_source_uses_qnx_timing_and_scheduling_apis():
    from qnx_porter import rt_bench
    src = rt_bench.source({"includes": '#include "zlib.h"', "call": "return 0;"})
    for api in ("ClockCycles()", "SYSPAGE_ENTRY(qtime)->cycles_per_sec", "SCHED_FIFO", "_NTO_TCTL_RUNMASK",
                '#include "zlib.h"', "static int one_call(void) { return 0; }"):
        assert api in src


def test_rt_score_penalises_jitter_under_load():
    from qnx_porter import rt_bench
    bench = {"idle": {"median_us": 10.0}, "loaded": {"p99_us": 40.0}}
    assert rt_bench.rt_score(80, bench) == 60          # p99 under load is 4x the idle median: 2 doublings
    assert rt_bench.rt_score(80, {"idle": {"median_us": 10.0}, "loaded": {"p99_us": 9.0}}) == 80
    assert rt_bench.rt_score(80, {"idle": {"median_us": 1.0}, "loaded": {"p99_us": 1e6}}) == 50  # capped at 30
    assert rt_bench.rt_score(80, None) is None


def test_every_bench_spec_has_a_call_and_what():
    import yaml
    from pathlib import Path
    specs = yaml.safe_load((Path(__file__).parents[1] / "bench" / "specs.yaml").read_text())
    libs = {k: v for k, v in specs.items() if not k.startswith("_")}
    assert len(libs) >= 15
    assert all("call" in v and "what" in v for v in libs.values())
