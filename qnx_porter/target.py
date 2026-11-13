"""Run the library's own tests on a QNX 8.0 target (the SDP's QEMU image, or a board) over ssh.

The build and source trees are copied to --target-dir on the target, and a QNX path-space link
(`ln -sP`) makes them appear at the same absolute path as on the host, so generated test scripts with
host paths baked in work unchanged. If that top-level path already exists on the target, host paths in
arguments are remapped under --target-dir instead.

CMake tests are run by `ctest_on_target()`: it reads ctest's own test list and runs every command on QNX.
That includes tests whose command is a script (json-c's `test1.test`), which CMake's cross-compiling
emulator never wraps. Meson and automake use the generated wrapper (`exe_wrapper`, `LOG_COMPILER`).
"""
import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SSH_OPTS = ["-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
            "-o", "LogLevel=ERROR", "-o", "ConnectTimeout=15"]


@dataclass
class Target:
    host: str  # user@host
    port: int = 22
    root: str = "/data/qnx-porter"  # where the trees are copied on the target
    # run the tests as this target user (QNX `on -u`), for suites that refuse root (libuv); "" = the ssh user
    run_as: str = ""

    @classmethod
    def parse(cls, spec: str, root: str = "/data/qnx-porter") -> "Target":
        host, _, port = spec.partition(":")
        return cls(host, int(port or 22), root)

    def ssh(self, command: str, **kw) -> subprocess.CompletedProcess:
        return subprocess.run(["ssh", *SSH_OPTS, "-p", str(self.port), self.host, command], **kw)

    def uname(self) -> str:
        """The target's `uname -a`, or "" if it does not answer within a minute."""
        try:
            r = self.ssh("uname -a", capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return ""
        return r.stdout.strip() if r.returncode == 0 else ""

    def sync(self, paths: list[Path]) -> bool:
        """Copy host directories to root+path on the target (tar over ssh). True if they are also visible
        at their host paths, through a QNX path-space link from /<top> to root/<top>."""
        rel = [str(p.resolve()).lstrip("/") for p in paths]
        root = shlex.quote(self.root)
        self.ssh("rm -rf " + " ".join(shlex.quote(self.root + "/" + r) for r in rel), timeout=600)
        tar = subprocess.Popen(["tar", "-C", "/", "-cf", "-", *rel], stdout=subprocess.PIPE)
        self.ssh(f"mkdir -p {root} && tar -C {root} -xf -", stdin=tar.stdout, check=True, timeout=1800)
        tar.wait()
        if self.run_as:  # the tests write into their trees, so that user must own them
            owner = shlex.quote(self.run_as)
            self.ssh(" && ".join(f"chown -R {owner} {shlex.quote(self.root + '/' + r)}" for r in rel), timeout=600)
        return self.ssh(link_command(self.root, rel), capture_output=True, timeout=60).returncode == 0

    def remove(self, paths: list[Path]) -> None:
        """Delete copied trees from the target once their tests are done. The QEMU image's /data has a
        fixed number of inodes (mkqnximage --data-inodes), and source trees are many small files."""
        rel = [str(p.resolve()).lstrip("/") for p in paths]
        self.ssh("rm -rf " + " ".join(shlex.quote(self.root + "/" + r) for r in rel), capture_output=True,
                 timeout=600)


def link_command(root: str, rel: list[str]) -> str:
    """Shell that makes /<top> show root/<top> (QNX `ln -sP`), and fails if /<top> is something else."""
    checks = []
    for top in sorted({r.split("/", 1)[0] for r in rel}):
        src, dst = shlex.quote(f"{root}/{top}"), shlex.quote(f"/{top}")
        checks.append(f'{{ [ -e {dst} ] || ln -sP {src} {dst}; }} && '
                      f'[ "$(cd {dst} && pwd -P)" = "$(cd {src} && pwd -P)" ]')
    return " && ".join(checks)


def remote_command(t: Target, work: str, cwd: str, argv: list[str], same_path: bool = False,
                   env: list[str] = (), limit: int = 0) -> str:
    """The shell command that runs argv on the target. Unless the trees are visible at their host paths,
    host paths under `work` are moved under t.root. With a limit, QNX's own `timeout` kills the test on
    the target, so a hung test cannot outlive its ssh session."""
    def move(a: str) -> str:
        return a.replace(work, t.root + work) if (work in a and not same_path) else a
    prefix = f"timeout -s KILL {limit} " if limit else ""
    prefix += f"on -u {shlex.quote(t.run_as)} " if t.run_as else ""
    prefix += ("env " + " ".join(shlex.quote(move(e)) for e in env) + " ") if env else ""
    return f"cd {shlex.quote(move(cwd))} && exec {prefix}{' '.join(shlex.quote(move(a)) for a in argv)}"


SAME_PATH_MARK = ".qnx-same-path"  # written in the work folder when sync() linked the paths


def _regexes(v) -> list[str]:
    return [x for x in (v if isinstance(v, list) else [v]) if x] if v else []


def _on(v) -> bool:
    return v in (True, 1) or str(v).upper() in ("ON", "TRUE", "1", "YES")


def verdict(rc: int | None, out: str, props: dict) -> str:
    """ctest's pass/fail/skip rules for one finished test: 'pass', 'fail' or 'skip'."""
    if rc is None:
        return "fail"  # timed out
    if "SKIP_RETURN_CODE" in props and rc == int(props["SKIP_RETURN_CODE"]):
        return "skip"
    def found(key):  # CMake regexes let `.` match newlines; Python needs DOTALL for the same meaning
        return any(re.search(r, out, re.S) for r in _regexes(props.get(key)))
    if found("SKIP_REGULAR_EXPRESSION"):
        return "skip"
    if found("FAIL_REGULAR_EXPRESSION"):
        ok = False
    elif _regexes(props.get("PASS_REGULAR_EXPRESSION")):
        ok = found("PASS_REGULAR_EXPRESSION")
    else:
        ok = rc == 0
    if _on(props.get("WILL_FAIL")):
        ok = not ok
    return "pass" if ok else "fail"


MISSING_EXEC = re.compile(r"exec (\S+): No such file or directory")

# `cmake -E <cmd>` steps in test suites (copying fixtures, comparing outputs). The target has no cmake, so these
# portable helpers run as the QNX shell commands that do the same; the log says so.
CMAKE_E = {"copy": ["cp", "-f"], "copy_if_different": ["cp", "-f"], "remove": ["rm", "-f"], "rm": ["rm", "-rf"],
           "make_directory": ["mkdir", "-p"], "compare_files": ["cmp", "-s"], "echo": ["echo"],
           "touch": ["touch"], "true": ["true"], "false": ["false"]}


def cmake_e(cmd: list[str]) -> list[str] | None:
    """The QNX equivalent of a `cmake -E <helper> args` test command, or None if it is not one we translate."""
    if len(cmd) >= 3 and Path(cmd[0]).name == "cmake" and cmd[1] == "-E" and cmd[2] in CMAKE_E:
        args = [a for a in cmd[3:] if not (cmd[2] == "rm" and a in ("-f", "-r", "-rf", "-fr"))]
        return CMAKE_E[cmd[2]] + args
    return None


def ctest_on_target(t: Target, build: Path, work: Path, emulator: str, same_path: bool, log_path: Path,
                    default_timeout: int = 300) -> dict:
    """Run every test ctest knows about on the QNX target."""
    listing = subprocess.run(["ctest", "--show-only=json-v1"], cwd=build, capture_output=True, text=True,
                             check=True).stdout
    tests = []
    for test in json.loads(listing).get("tests", []):
        props = {p["name"]: p["value"] for p in test.get("properties", [])}
        cmd = list(test.get("command") or [])
        if cmd and emulator and cmd[0] == emulator:
            cmd = cmd[1:]
        env = props.get("ENVIRONMENT") or []
        tests.append({"name": test["name"], "cmd": cmd, "cwd": props.get("WORKING_DIRECTORY", str(build)),
                      "env": env if isinstance(env, list) else [env], "props": props})
    return run_tests(t, tests, work, same_path, log_path,
                     f"$ ctest --show-only=json-v1 (in {build}); every test command runs on {t.host} over ssh\n",
                     default_timeout)


def meson_on_target(t: Target, build: Path, work: Path, same_path: bool, log_path: Path,
                    default_timeout: int = 300) -> dict:
    """Run every test meson knows about (meson introspect --tests) on the QNX target."""
    listing = subprocess.run(["meson", "introspect", "--tests", str(build)], capture_output=True, text=True,
                             check=True).stdout
    tests = [{"name": x["name"], "cmd": list(x.get("cmd") or []), "cwd": x.get("workdir") or str(build),
              "env": [f"{k}={v}" for k, v in (x.get("env") or {}).items()],
              "props": {"WILL_FAIL": bool(x.get("should_fail")), "TIMEOUT": x.get("timeout") or default_timeout}}
             for x in json.loads(listing)]
    return run_tests(t, tests, work, same_path, log_path,
                     f"$ meson introspect --tests {build}; every test command runs on {t.host} over ssh\n",
                     default_timeout)


def _run_one(t: Target, work: Path, cwd: str, cmd: list[str], same_path: bool, env: list[str], limit: int):
    try:
        r = t.ssh(remote_command(t, str(work), cwd, cmd, same_path, env, limit), capture_output=True,
                  text=True, errors="replace", timeout=limit + 60)
        rc, out = r.returncode, r.stdout + r.stderr
        if rc == 137:
            rc, out = None, out + f"\nkilled on the target after {limit} s"
    except subprocess.TimeoutExpired:
        rc, out = None, f"timed out after {limit} s"
    return rc, out


TAP = re.compile(r"^\s*(not ok|ok) \d+(?: -)? ?([^#\n]*)(#\s*(?:SKIP|TODO)[^\n]*)?$", re.M | re.I)


def tap_summary(out: str) -> str:
    """For a test binary that reports its own subtests in TAP (libuv, ...): the counts, and every failing name.
    The log keeps only the end of a long output, so the full list of failures is written here."""
    marks = TAP.findall(out)
    if not marks:
        return ""
    skip = sum(1 for _, _, d in marks if d)
    bad = [name.strip() for kind, name, d in marks if kind.lower() == "not ok" and not d]
    ok = len(marks) - skip - len(bad)
    text = f"; its own subtests (TAP): {ok} ok, {len(bad)} not ok, {skip} skipped"
    return text + (f"\n      not ok: {', '.join(bad)}" if bad else "")


def run_tests(t: Target, tests: list[dict], work: Path, same_path: bool, log_path: Path, header: str,
              default_timeout: int = 300) -> dict:
    """Run each test command on the target and judge it with ctest's rules.

    A test whose command starts with an interpreter the target does not have (the host's /usr/bin/python3,
    say) is not run on QNX at all: it is reported as "not runnable on the target", never as passed or failed.
    A bash script gets one retry with QNX's ksh, which is said in the log.
    """
    passed = total = 0
    not_runnable = []
    lines = [header]
    for test in tests:
        props, cmd = test["props"], test["cmd"]
        if _on(props.get("DISABLED")) or not cmd:
            lines.append(f"SKIP  {test['name']} (disabled or not built)\n")
            continue
        limit = int(min(float(props.get("TIMEOUT") or default_timeout), default_timeout))
        shim = cmake_e(cmd)
        if shim:
            cmd = shim
        rc, out = _run_one(t, work, test["cwd"], cmd, same_path, test["env"], limit)
        if shim:
            out = f"(cmake -E helper run on QNX as: {' '.join(shim[:2])})\n" + out
        m = MISSING_EXEC.search(out) if rc == 127 else None
        if m and m.group(1) == cmd[0]:
            interp = Path(cmd[0]).name
            if interp in ("bash", "sh"):
                rc, out = _run_one(t, work, test["cwd"], ["ksh", *cmd[1:]], same_path, test["env"], limit)
                out = f"(run with ksh: the target has no {interp})\n" + out
            else:
                not_runnable.append({"name": test["name"], "needs": interp})
                lines.append(f"N/A   {test['name']} (needs {interp} on the target)\n")
                continue
        v = verdict(rc, out, props)
        if v != "skip":
            total += 1
            passed += v == "pass"
        lines.append(f"{v.upper():5s} {test['name']} (exit {rc}){tap_summary(out)}\n")
        if v == "fail" or out.startswith("(run with ksh"):
            lines.append("".join(f"    {ln}\n" for ln in out.strip().splitlines()[-150:]))
    lines.append(f"\n{passed}/{total} tests passed on the QNX target"
                 + (f"; {len(not_runnable)} not runnable there" if not_runnable else "") + "\n")
    log_path.write_text("".join(lines), encoding="utf-8")
    return {"passed": passed, "total": total, "not_runnable": not_runnable}


def write_wrapper(path: Path, t: Target, work: Path) -> str:
    """A script usable as CMAKE_CROSSCOMPILING_EMULATOR, meson exe_wrapper and automake LOG_COMPILER."""
    py = shlex.quote(sys.executable)
    path.write_text("#!/bin/sh\n# Generated by qnx-porter: runs one test binary on the QNX target.\n"
                    f"PYTHONPATH={shlex.quote(str(Path(__file__).resolve().parents[1]))} exec {py} -m "
                    f"qnx_porter.target --target {shlex.quote(f'{t.host}:{t.port}')} "
                    f"--root {shlex.quote(t.root)} --work {shlex.quote(str(work.resolve()))} -- \"$@\"\n")
    path.chmod(0o755)
    return str(path)


def parse_results(system: str, log: str) -> tuple[int, int]:
    """(passed, total) from the test runner's own summary. Skipped tests are not counted in total."""
    if system == "cmake":
        m = re.search(r"(\d+)% tests passed, (\d+) tests? failed out of (\d+)", log)
        if m:
            total, failed = int(m[3]), int(m[2])
            skipped = len(re.findall(r"\*\*\*Skipped|\(Disabled\)", log))
            return total - failed - skipped, total - skipped
        return 0, 0
    if system == "meson":
        n = {k: int(v) for k, v in re.findall(r"^(Ok|Expected Fail|Fail|Unexpected Pass|Timeout):\s+(\d+)", log,
                                              re.M)}
        return n.get("Ok", 0) + n.get("Expected Fail", 0), sum(n.values())
    if system == "autotools":
        total = sum(int(x) for x in re.findall(r"^# TOTAL: +(\d+)", log, re.M))
        skip = sum(int(x) for x in re.findall(r"^# SKIP: +(\d+)", log, re.M))
        ok = sum(int(x) for x in re.findall(r"^# (?:PASS|XFAIL): +(\d+)", log, re.M))
        return ok, total - skip
    return 0, 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Run one binary on the QNX target (used by ctest/meson/make).")
    ap.add_argument("--target", required=True)
    ap.add_argument("--root", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("argv", nargs="+")
    a = ap.parse_args()
    t = Target.parse(a.target, a.root)
    same = (Path(a.work) / SAME_PATH_MARK).exists()
    return t.ssh(remote_command(t, a.work, os.getcwd(), a.argv, same)).returncode


if __name__ == "__main__":
    sys.exit(main())
