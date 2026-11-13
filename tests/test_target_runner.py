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


def test_cmake_e_helpers_run_as_qnx_shell_commands():
    # libjpeg-turbo 3.0.4: 8 `cmake -E copy_if_different` steps feed 410 dependent tests.
    from qnx_porter.target import cmake_e
    assert cmake_e(["/usr/bin/cmake", "-E", "copy_if_different", "a.ppm", "b.ppm"]) == ["cp", "-f", "a.ppm", "b.ppm"]
    assert cmake_e(["/usr/bin/cmake", "-E", "compare_files", "x", "y"]) == ["cmp", "-s", "x", "y"]
    assert cmake_e(["/usr/bin/cmake", "-E", "rm", "-f", "z"]) == ["rm", "-rf", "z"]
    assert cmake_e(["/usr/bin/cmake", "-E", "tar", "cf", "z"]) is None
    assert cmake_e(["/w/build/test1"]) is None


def test_tap_subtests_are_counted_and_every_failure_named():
    from qnx_porter.target import tap_summary
    out = ("1..4\nok 1 - fs_open\nnot ok 2 - udp_connect\n# exit code 1\n"
           "ok 3 - tcp_connect_timeout # SKIP Network unreachable.\nok 4 - timer\n")
    s = tap_summary(out)
    assert "2 ok, 1 not ok, 1 skipped" in s and "not ok: udp_connect" in s
    assert tap_summary("PASS\n") == ""


def test_leftover_test_processes_are_killed_before_the_tree_is_removed(tmp_path):
    # libuv's runner spawns children that outlive QNX's `timeout -s KILL`; they slowed every later library.
    import subprocess
    from qnx_porter.target import kill_leftovers_command
    cmd = kill_leftovers_command(["home/u/ports/nng/work/src", "home/u/ports/nng/work/build"])
    assert '/proc/[0-9]*' in cmd and 'exefile' in cmd and 'kill -9' in cmd
    # the shell is valid and matches only processes under those trees (fake /proc layout, echo instead of kill)
    for pid, exe in (("11", "/data/qnx-porter/home/u/ports/nng/work/build/uv_test"), ("12", "/proc/boot/sh")):
        (tmp_path / pid).mkdir()
        (tmp_path / pid / "exefile").write_text(exe)
    fake = cmd.replace("/proc/[0-9]*", f"{tmp_path}/[0-9]*").replace("${d#/proc/}", "${d##*/}").replace("kill -9", "echo")
    out = subprocess.run(["sh", "-c", fake], capture_output=True, text=True).stdout.split()
    assert out == ["11"]


def test_sync_shims_stages_scripts_and_echo_link():
    t = Target.parse("root@q", root="/custom/root")
    sent = []

    def fake_ssh(self, command, **kw):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    t.ssh = fake_ssh.__get__(t, Target)
    assert t.sync_shims() is True
    assert t.shims is True
    assert len(sent) == 1
    cmd = sent[0]
    assert "mkdir -p /custom/root/shims" in cmd
    assert "cat <<'EOF' > /custom/root/shims/killall" in cmd
    assert "chmod 755 /custom/root/shims/killall" in cmd
    assert "cat <<'EOF' > /custom/root/shims/ps" in cmd
    assert "chmod 755 /custom/root/shims/ps" in cmd
    assert "ln -sP /proc/boot/echo /bin/echo" in cmd
    assert "[ -e /bin/echo ]" in cmd


def test_sync_shims_sets_ownership_when_run_as():
    t = Target.parse("root@q", root="/data/qnx-porter")
    t.run_as = "qnxuser"
    sent = []

    def fake_ssh(self, command, **kw):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    t.ssh = fake_ssh.__get__(t, Target)
    t.sync_shims()
    cmd = sent[0]
    assert "chown -R qnxuser /data/qnx-porter/shims" in cmd


def test_remote_command_injects_shims_path():
    t = Target.parse("root@q", root="/data/qnx-porter")
    argv = ["/home/u/w/src/tests/test1.test"]

    # When shims=False, no PATH injection
    cmd_noshims = remote_command(t, "/home/u/w", "/home/u/w/build", argv, True, shims=False)
    assert cmd_noshims == "cd /home/u/w/build && exec /home/u/w/src/tests/test1.test"

    # When shims=True, PATH is injected with unquoted $PATH so target shell expands it
    cmd_shims = remote_command(t, "/home/u/w", "/home/u/w/build", argv, True, shims=True)
    assert cmd_shims == ("cd /home/u/w/build && exec env PATH=/data/qnx-porter/shims:$PATH "
                         "/home/u/w/src/tests/test1.test")

    # When env already has PATH, prepends shims directory
    cmd_env_path = remote_command(t, "/home/u/w", "/home/u/w/build", argv, True,
                                  env=["PATH=/custom/bin:/bin"], shims=True)
    assert cmd_env_path == ("cd /home/u/w/build && exec env PATH=/data/qnx-porter/shims:/custom/bin:/bin "
                            "/home/u/w/src/tests/test1.test")

    # When t.shims=True and shims=None, automatically injects PATH
    t.shims = True
    cmd_auto = remote_command(t, "/home/u/w", "/home/u/w/build", argv, True)
    assert "env PATH=/data/qnx-porter/shims:$PATH" in cmd_auto


def test_run_one_activates_shims_when_marker_or_target_active(tmp_path, monkeypatch):
    t = Target.parse("root@q", root="/data/qnx-porter")
    sent = []

    def fake_ssh(self, command, **kw):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(Target, "ssh", fake_ssh)

    # Without marker and without t.shims, no PATH injected
    target._run_one(t, tmp_path, str(tmp_path), ["/w/test"], True, [], 300)
    assert "PATH=" not in sent[0]

    # With .qnx-shims marker in work dir, PATH is injected
    (tmp_path / target.SHIMS_MARK).write_text("")
    target._run_one(t, tmp_path, str(tmp_path), ["/w/test"], True, [], 300)
    assert "PATH=/data/qnx-porter/shims:$PATH" in sent[1]


def test_target_sync_calls_sync_shims_and_writes_marker(tmp_path, monkeypatch):
    t = Target.parse("root@q", root="/data/qnx-porter")
    work = tmp_path / "work"
    src, bdir = work / "src", work / "build"
    src.mkdir(parents=True)
    bdir.mkdir(parents=True)

    sent = []

    def fake_ssh(self, command, **kw):
        sent.append(command)
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(Target, "ssh", fake_ssh)
    monkeypatch.setattr(target.subprocess, "Popen",
                        lambda *a, **k: SimpleNamespace(stdout=None, wait=lambda: 0))

    ok = t.sync([src, bdir])
    assert ok is True
    assert t.shims is True
    assert (work / target.SHIMS_MARK).exists()
    assert any("mkdir -p /data/qnx-porter/shims" in c for c in sent)


def test_killall_and_ps_shim_scripts_semantics():
    from qnx_porter.target import KILLALL_SHIM, PS_SHIM

    # killall shim validates: force slaying (-f), basename stripping (${1##*/}), signals, and quiet (-Q)
    assert "slay" in KILLALL_SHIM
    assert 'slay_args="-f"' in KILLALL_SHIM
    assert 'name="${1##*/}"' in KILLALL_SHIM
    assert "-s $sig" in KILLALL_SHIM
    assert "-Q" in KILLALL_SHIM

    # ps shim validates: pidin execution, -p filtering, and stripping full-system list options
    assert "pidin" in PS_SHIM
    assert "exec pidin -p" in PS_SHIM
    assert "exec pidin" in PS_SHIM
    assert "-ef" in PS_SHIM and "aux" in PS_SHIM
