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
