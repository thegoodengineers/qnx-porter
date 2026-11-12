"""The on-target test runner: ctest's rules, path handling, and every ctest command going to QNX."""
import json
import subprocess
from types import SimpleNamespace

from qnx_porter import target
from qnx_porter.target import Target, link_command, remote_command, verdict


def test_verdict_follows_ctest_rules():
    assert verdict(0, "", {}) == "pass" and verdict(1, "", {}) == "fail" and verdict(None, "", {}) == "fail"
    assert verdict(1, "", {"WILL_FAIL": True}) == "pass"
    assert verdict(77, "", {"SKIP_RETURN_CODE": "77"}) == "skip"
    assert verdict(0, "all good", {"PASS_REGULAR_EXPRESSION": ["good"]}) == "pass"
    assert verdict(0, "meh", {"PASS_REGULAR_EXPRESSION": ["good"]}) == "fail"
    assert verdict(0, "ERROR x", {"FAIL_REGULAR_EXPRESSION": ["ERROR"]}) == "fail"
    # cmocka's XML tests: CMake's `.` matches newlines (the run on QNX passed, our first verdict said fail)
    xml = '<testcase name="a" time="0.0" >\n        </testcase>'
    assert verdict(0, xml, {"PASS_REGULAR_EXPRESSION": ['<testcase name="a" time="[0-9.]+" >.*</testcase>']}) == "pass"


def test_same_path_runs_unchanged_and_otherwise_remaps():
    t = Target.parse("root@q")
    argv = ["/home/u/w/src/tests/test1.test"]
    assert remote_command(t, "/home/u/w", "/home/u/w/build", argv, True) == \
        "cd /home/u/w/build && exec /home/u/w/src/tests/test1.test"
    assert remote_command(t, "/home/u/w", "/home/u/w/build", argv, True, limit=300) == \
        "cd /home/u/w/build && exec timeout -s KILL 300 /home/u/w/src/tests/test1.test"
    assert remote_command(t, "/home/u/w", "/home/u/w/build", argv, False, ["A=/home/u/w/x"]) == \
        "cd /data/qnx-porter/home/u/w/build && exec env A=/data/qnx-porter/home/u/w/x " \
        "/data/qnx-porter/home/u/w/src/tests/test1.test"


def test_link_command_uses_qnx_path_space_links():
    cmd = link_command("/data/qnx-porter", ["home/u/w/src", "home/u/w/build"])
    assert cmd.count("ln -sP /data/qnx-porter/home /home") == 1 and "pwd -P" in cmd


def test_every_ctest_command_runs_on_the_target_including_scripts(tmp_path, monkeypatch):
    listing = {"tests": [
        {"name": "test1", "command": ["/w/src/tests/test1.test"],
         "properties": [{"name": "WORKING_DIRECTORY", "value": "/w/build/tests"}]},
        {"name": "unit", "command": ["/w/qnx-run", "/w/build/unit"], "properties": []},
        {"name": "xfail", "command": ["/w/build/bad"], "properties": [{"name": "WILL_FAIL", "value": True}]},
        {"name": "off", "command": ["/w/build/off"], "properties": [{"name": "DISABLED", "value": True}]},
    ]}
    monkeypatch.setattr(target.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(stdout=json.dumps(listing), returncode=0))
    sent = []

    def fake_ssh(self, command, **kw):
        sent.append(command)
        return subprocess.CompletedProcess(command, 1 if "bad" in command else 0, "", "")
    monkeypatch.setattr(Target, "ssh", fake_ssh)
    r = target.ctest_on_target(Target.parse("root@q"), tmp_path, tmp_path, "/w/qnx-run", True,
                               tmp_path / "tests.log")
    assert (r["passed"], r["total"], r["not_runnable"]) == (3, 3, [])
    assert sent[0] == "cd /w/build/tests && exec timeout -s KILL 300 /w/src/tests/test1.test"
    assert sent[1].endswith("exec timeout -s KILL 300 /w/build/unit")  # our emulator prefix is stripped: the command runs on QNX
    assert "3/3 tests passed on the QNX target" in (tmp_path / "tests.log").read_text()


def test_missing_interpreters_bash_retries_with_ksh_python_is_not_runnable(tmp_path, monkeypatch):
    # Real cases from the 61-library campaign: expat's tests start with /usr/bin/bash, cmark's with python3.
    tests = [
        {"name": "runtests", "cmd": ["/usr/bin/bash", "/w/run.sh"], "cwd": "/w", "env": [], "props": {}},
        {"name": "spectest", "cmd": ["/usr/bin/python3.10", "/w/spec.py"], "cwd": "/w", "env": [], "props": {}},
    ]
    sent = []

    def fake_ssh(self, command, **kw):
        sent.append(command)
        missing = next((p for p in ("/usr/bin/bash", "/usr/bin/python3.10") if f" {p} " in command), None)
        if missing:
            return subprocess.CompletedProcess(command, 127, "", f"timeout: exec {missing}: No such file or directory")
        return subprocess.CompletedProcess(command, 0, "ok", "")
    monkeypatch.setattr(Target, "ssh", fake_ssh)
    r = target.run_tests(Target.parse("root@q"), tests, tmp_path, True, tmp_path / "t.log", "")
    assert (r["passed"], r["total"]) == (1, 1)
    assert r["not_runnable"] == [{"name": "spectest", "needs": "python3.10"}]
    assert any("exec timeout -s KILL 300 ksh /w/run.sh" in c for c in sent)
    log = (tmp_path / "t.log").read_text()
    assert "N/A   spectest (needs python3.10 on the target)" in log and "run with ksh" in log
