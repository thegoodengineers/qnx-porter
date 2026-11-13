"""qnx-porter: port an open-source C/C++ library to QNX 8.0 and prove it with the library's own tests."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from . import agent, build, qnx
from .target import Target


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="qnx-porter", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("port", help="port one library")
    p.add_argument("url", help="git URL of the upstream library")
    p.add_argument("--tag", required=True, help="release tag or branch to port")
    p.add_argument("--arg", action="append", default=[], help="extra configure argument (repeatable)")
    for s in (p,):
        s.add_argument("--arch", default="x86_64", choices=sorted(qnx.ARCHES))
        s.add_argument("--target", help="QNX target for tests, user@host[:port] (e.g. root@172.31.1.11)")
        s.add_argument("--target-dir", default="/data/qnx-porter", help="scratch folder on the target")
        s.add_argument("--out", default="ports", help="where port folders are written")
        s.add_argument("--max-rounds", type=int, default=15)
        s.add_argument("--no-model", action="store_true", help="deterministic rules only")

    d = sub.add_parser("detect", help="print the build system of a source folder")
    d.add_argument("path")
    dr = sub.add_parser("doctor", help="check the QNX SDP 8.0 install, host tools and (optionally) the target")
    dr.add_argument("--target", help="also check this QNX target answers over ssh, user@host[:port]")
    st = sub.add_parser("selftest", help="run the loop on a deliberately broken library with the host "
                                         "compiler (no QNX needed)")
    st.add_argument("--out", default="ports-selftest")

    a = ap.parse_args(argv)
    if a.cmd == "detect":
        print(build.detect(Path(a.path)))
        return 0
    if a.cmd == "doctor":
        bad = 0
        for what, ok, detail, fix in qnx.doctor(target=Target.parse(a.target) if a.target else None):
            print(f"{'ok ' if ok else 'BAD'} {what:16s} {detail}")
            if fix:
                print(f"    fix: {fix}")
            bad += not ok
        print("all checks passed" if not bad else f"{bad} check(s) failed: fix them in order, then run doctor again")
        return 1 if bad else 0
    if a.cmd == "selftest":
        return selftest(Path(a.out))
    target = Target.parse(a.target, a.target_dir) if a.target else None
    r = agent.port(a.url, a.tag, Path(a.out), arch=a.arch, target=target, max_rounds=a.max_rounds,
                   use_llm=not a.no_model, extra_args=tuple(a.arg))
    return 0 if r["build_result"] == "built" else 1


def selftest(out: Path) -> int:
    """Copy the bundled broken library into a git repo and port it with the host compiler."""
    lib = (out / "upstream").resolve()
    shutil.rmtree(lib, ignore_errors=True)
    shutil.copytree(Path(__file__).parent / "brokenlib", lib)
    for cmd in (["init", "-q"], ["add", "-A"], ["-c", "user.name=selftest", "-c", "user.email=selftest@localhost",
                                                "commit", "-qm", "v1"], ["tag", "v1"]):
        subprocess.run(["git", "-C", str(lib), *cmd], check=True)
    r = agent.port(str(lib), "v1", out, arch=None, use_llm=False, name="brokenlib")
    return 0 if r["build_result"] == "built" and r["patches_kept"] == 2 else 1


if __name__ == "__main__":
    sys.exit(main())
