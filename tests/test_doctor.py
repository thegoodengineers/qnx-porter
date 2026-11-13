"""`qnx-porter doctor`: every miss names its fix and SETUP.md step; --target asks the target for uname. No SDP needed."""
import subprocess

from qnx_porter import cli, qnx
from qnx_porter.target import Target


def no_sdp(environ=None):
    raise SystemExit("QNX SDP 8.0 not found: source qnxsdp-env.sh ... See SETUP.md.")


def full_sdp(tmp_path):
    """A fake SDP 8.0 tree with every file doctor looks at."""
    host, target = tmp_path / "host", tmp_path / "target"
    for a in qnx.ARCHES.values():
        (host / "usr" / "bin").mkdir(parents=True, exist_ok=True)
        (host / "usr" / "bin" / f"{a.triplet}-gcc-12.2.0").write_text("x")
        for lib in ("libc.so", "libsocket.so"):
            (target / a.name / "lib").mkdir(parents=True, exist_ok=True)
            (target / a.name / "lib" / lib).write_text("ELF")
    (host / "usr" / "bin" / "qcc").write_text("x")
    return {"QNX_HOST": str(host), "QNX_TARGET": str(target), "PATH": "/usr/bin"}


def by_name(checks):
    return {what: (ok, detail, fix) for what, ok, detail, fix in checks}


def test_every_miss_has_a_one_line_fix_naming_the_setup_step(monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", no_sdp)
    monkeypatch.setattr(qnx.shutil, "which", lambda name: None if name == "ninja" else f"/usr/bin/{name}")
    c = by_name(qnx.doctor({}))
    assert c["SDP env"][0] is False and "SETUP.md step 3" in c["SDP env"][2]
    assert "qcc" not in c  # one SDP miss, one fix: no cascade of follow-on failures
    assert c["ninja"] == (False, "not on PATH", "sudo apt install -y ninja-build (SETUP.md step 2)")
    assert c["cmake"] == (True, "/usr/bin/cmake", "")
    for what, (ok, _, fix) in c.items():
        assert ok or ("SETUP.md step" in fix and "\n" not in fix), what


def test_a_complete_sdp_and_host_pass(monkeypatch, tmp_path):
    env = full_sdp(tmp_path)
    monkeypatch.setattr(qnx.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(qnx.subprocess, "run", lambda cmd, **kw: subprocess.CompletedProcess(
        cmd, 0, "cc: targets available in /q/etc/qcc:\n\t12.2.0,gcc_ntox86_64_cxx\n\t12.2.0,gcc_ntox86_64\t(default)\n"
                "\t12.2.0,gcc_ntoaarch64le\n", ""))
    c = by_name(qnx.doctor(env))
    assert [w for w, (ok, _, _) in c.items() if not ok] == []
    assert c["qcc targets"][1] == "gcc_ntoaarch64le gcc_ntox86_64"
    assert {"QNX_HOST", "QNX_TARGET", "qcc", "qcc targets", "x86_64 gcc", "aarch64le gcc", "SDP complete", "qcc builds hello",
            "cmake", "make", "ninja", "git", "ssh", "tar", "python"} <= set(c)
    assert "QNX target" not in c  # only with --target


def test_target_check_uses_uname(monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", no_sdp)
    t = Target.parse("root@172.31.1.11:2222")
    monkeypatch.setattr(Target, "uname", lambda self: "QNX qnx-porter 8.0.0 2026/06/05 x86pc x86_64")
    assert by_name(qnx.doctor({}, t))["QNX target"] == (True, "QNX qnx-porter 8.0.0 2026/06/05 x86pc x86_64", "")
    monkeypatch.setattr(Target, "uname", lambda self: "")
    ok, detail, fix = by_name(qnx.doctor({}, t))["QNX target"]
    assert not ok and "did not answer" in detail
    assert fix == "boot the target and check `ssh -p 2222 root@172.31.1.11 uname -a` (SETUP.md step 4)"

    def hang(self):
        raise subprocess.TimeoutExpired("ssh", 60)
    monkeypatch.setattr(Target, "uname", hang)
    assert by_name(qnx.doctor({}, t))["QNX target"][0] is False


def test_cli_prints_fixes_and_exits_nonzero(monkeypatch, capsys):
    seen = {}

    def fake(environ=None, target=None):
        seen["target"] = target
        return [("cmake", True, "/usr/bin/cmake", ""), ("QNX target", False, "no answer", "boot it (SETUP.md step 4)")]
    monkeypatch.setattr(qnx, "doctor", fake)
    assert cli.main(["doctor", "--target", "root@q:2222"]) == 1
    assert (seen["target"].host, seen["target"].port) == ("root@q", 2222)
    out = capsys.readouterr().out.splitlines()
    assert out[0].startswith("ok  cmake") and out[1].startswith("BAD QNX target")
    assert out[2] == "    fix: boot it (SETUP.md step 4)" and out[3].startswith("1 check(s) failed")
