import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("run_campaign", ROOT / "scripts" / "run_campaign.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)
sys.path.insert(0, str(ROOT / "scripts"))
import ports_csv  # noqa: E402


def test_campaign_pins_50_plus_libraries_with_tags():
    c = rc.load(ROOT / "campaign.yaml")
    assert len(c["libraries"]) >= 50
    assert all(lib["tag"] and lib["url"].startswith("https://") for lib in c["libraries"])
    assert len({lib["name"] for lib in c["libraries"]}) == len(c["libraries"])
    assert c["arch"] == "x86_64" and c["target"]


def test_missing_sdp_points_to_setup(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    with pytest.raises(SystemExit, match="SETUP.md step 3"):
        rc.preflight({"QNX_SDP": str(tmp_path)})


def test_sdp_without_qcc_points_to_setup(tmp_path):
    env = {"QNX_HOST": str(tmp_path / "host"), "QNX_TARGET": str(tmp_path / "target")}
    with pytest.raises(SystemExit, match="qcc not found.*SETUP.md"):
        rc.preflight(env)


def test_sdp_with_qcc_passes(tmp_path):
    qcc = tmp_path / "host" / "usr" / "bin" / "qcc"
    qcc.parent.mkdir(parents=True)
    qcc.write_text("")
    env = {"QNX_HOST": str(tmp_path / "host"), "QNX_TARGET": str(tmp_path / "target")}
    assert rc.preflight(env)["QNX_HOST"] == env["QNX_HOST"]


def test_libraries_now_on_oss_are_skipped():
    libs = [{"name": "json-c", "url": "https://github.com/json-c/json-c.git"},
            {"name": "nng", "url": "https://github.com/nanomsg/nng.git"},
            {"name": "yyjson", "url": "https://github.com/ibireme/yyjson.git"}]
    assert rc.already_on_oss(libs, {"json-c-dev", "nngx"}, {"https://github.com/ibireme/yyjson"}) == \
        ["json-c", "yyjson"]


def test_agent_error_still_lands_in_the_csv(tmp_path):
    rc.error_report(tmp_path, {"name": "x", "url": "u", "tag": "v1"}, "x86_64", "clone failed", 0.2)
    [row] = ports_csv.rows(tmp_path)
    assert row["build_result"] == "error" and row["tests_total"] == ""
    assert json.loads((tmp_path / "x" / "report.json").read_text())["blocked_on"][0]["error"] == "clone failed"


def test_weekly_head_history_appends_one_row_per_library(tmp_path, monkeypatch):
    import head_history
    (tmp_path / "ports-head/zlib").mkdir(parents=True)
    (tmp_path / "ports-head/zlib/report.json").write_text(json.dumps({
        "library": "zlib", "version": "develop", "commit": "51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf",
        "arch": "x86_64", "build_result": "built", "rounds": 1, "patches_kept": 0, "minutes": 0.3}))
    monkeypatch.setattr(head_history, "DEST", tmp_path / "history.csv")
    head_history.main([str(tmp_path / "ports-head")])
    head_history.main([str(tmp_path / "ports-head")])
    lines = (tmp_path / "history.csv").read_text().splitlines()
    assert lines[0].startswith("run,library,branch,commit") and len(lines) == 3
    assert ",zlib,develop,51b7f2abdade,x86_64,built,1,0,0.3" in lines[1]
def test_resume_skips_finished_libraries_but_not_errors(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "a/report.json").write_text(json.dumps({"build_result": "failed"}))
    (tmp_path / "b").mkdir()
    (tmp_path / "b/report.json").write_text(json.dumps({"build_result": "error"}))
    assert rc.finished(tmp_path / "a/report.json")
    assert not rc.finished(tmp_path / "b/report.json") and not rc.finished(tmp_path / "c/report.json")


def test_dead_target_is_restarted_once(monkeypatch):
    class T:
        answers = iter(["", "", "QNX qnx-porter 8.0.0"])
        def uname(self):
            return next(self.answers)
    ran = []
    monkeypatch.setattr(rc.subprocess, "run", lambda cmd, shell: ran.append(cmd))
    monkeypatch.setattr(rc.time, "sleep", lambda s: None)
    assert rc.alive(T(), "qemu_target.sh restart") and ran == ["qemu_target.sh restart"]
    assert not rc.alive(type("D", (), {"uname": lambda self: ""})(), None)


def test_clone_retries_only_when_the_network_is_down(tmp_path, monkeypatch):
    import subprocess
    from qnx_porter import agent
    calls = []
    def run(cmd, **kw):
        calls.append(cmd)
        err = "fatal: unable to access 'https://x/': Could not resolve host: github.com" if len(calls) < 3 else ""
        return subprocess.CompletedProcess(cmd, 128 if err else 0, "", err)
    monkeypatch.setattr(agent.subprocess, "run", run)
    monkeypatch.setattr(agent.time, "sleep", lambda s: None)
    agent.clone("https://x/y.git", "v1", tmp_path / "src", log=lambda m: None)
    assert len(calls) == 3
    calls.clear()
    monkeypatch.setattr(agent.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 128, "", "fatal: Remote branch v9 not found in upstream origin"))
    with pytest.raises(subprocess.CalledProcessError):
        agent.clone("https://x/y.git", "v9", tmp_path / "src", log=lambda m: None)


def test_tests_can_run_as_another_target_user():
    # libuv's test suite refuses root ("The libuv test suite cannot be run as root."); QNX's `on -u` drops it.
    from qnx_porter.target import Target, remote_command
    t = rc.for_library(Target("root@q"), {"run_as": "qnxuser"})
    assert t.run_as == "qnxuser" and rc.for_library(Target("root@q"), {"run_as": ""}).run_as == ""
    assert t.test_timeout == 300 and rc.for_library(Target("root@q"), {"test_timeout": 900}).test_timeout == 900
    cmd = remote_command(t, "/w", "/w/b", ["/w/b/uv_run_tests"], same_path=True, limit=300)
    assert "exec timeout -s KILL 300 on -u qnxuser /w/b/uv_run_tests" in cmd


def test_uses_must_name_a_library_listed_before(tmp_path):
    f = tmp_path / "c.yaml"
    f.write_text("libraries:\n  - {name: a, url: https://x/a.git, tag: v1, uses: [b]}\n"
                 "  - {name: b, url: https://x/b.git, tag: v1}\n")
    with pytest.raises(SystemExit, match="a uses b, which must be listed before it"):
        rc.load(f)
    f.write_text("libraries:\n  - {name: b, url: https://x/b.git, tag: v1}\n"
                 "  - {name: a, url: https://x/a.git, tag: v1, uses: [b]}\n")
    assert rc.load(f)["libraries"][1]["uses"] == ["b"]


def test_tidy_deletes_a_finished_build_tree_but_keeps_sources_and_builds_others_use(tmp_path):
    for name in ("zlib", "cJSON"):
        (tmp_path / name / "work" / "build").mkdir(parents=True)
        (tmp_path / name / "work" / "src").mkdir(parents=True)
    rc.tidy(tmp_path, "zlib", keep={"cJSON"})
    rc.tidy(tmp_path, "cJSON", keep={"cJSON"})  # mosquitto `uses: [cJSON]`: it links cJSON's build
    assert not (tmp_path / "zlib" / "work" / "build").exists() and (tmp_path / "zlib" / "work" / "src").exists()
    assert (tmp_path / "cJSON" / "work" / "build").exists()


def test_the_campaign_pauses_while_a_watched_disk_is_low(monkeypatch, capsys):
    real = rc.low_disk
    assert real(["/"], 0) == [] and real(["/no/such/path"], 10**9) == []
    free = iter([[("/mnt/d", 2.5)], [("/mnt/d", 2.5)], []])
    monkeypatch.setattr(rc, "low_disk", lambda paths, min_gb: next(free))
    naps = []
    rc.wait_for_disk(["/mnt/d"], 5, sleep=naps.append)
    out = capsys.readouterr().out
    assert len(naps) == 2 and out.count("paused: /mnt/d has 2.5 GiB free (under 5 GiB)") == 1
    assert "disk space is back" in out
