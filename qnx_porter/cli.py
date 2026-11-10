"""qnx-porter: port an open-source C/C++ library to QNX 8.0 and prove it with the library's own tests."""
import argparse
import json
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
    b = sub.add_parser("batch", help="port every library in a JSON list")
    b.add_argument("list", help='JSON file: [{"url": ..., "tag": ..., "args": [...]}]')
    for s in (p, b):
        s.add_argument("--arch", default="x86_64", choices=sorted(qnx.ARCHES))
        s.add_argument("--target", help="QNX target for tests, user@host[:port] (e.g. root@172.31.1.11)")
        s.add_argument("--target-dir", default="/data/qnx-porter", help="scratch folder on the target")
        s.add_argument("--out", default="ports", help="where port folders are written")
        s.add_argument("--max-rounds", type=int, default=15)
        s.add_argument("--no-model", action="store_true", help="deterministic rules only")

    d = sub.add_parser("detect", help="print the build system of a source folder")
    d.add_argument("path")
    sub.add_parser("doctor", help="check the QNX SDP 8.0 install and host tools")

    a = ap.parse_args(argv)
    if a.cmd == "detect":
        print(build.detect(Path(a.path)))
        return 0
    if a.cmd == "doctor":
        bad = 0
        for what, ok, detail in qnx.doctor(qnx.sdp_env()):
            print(f"{'ok ' if ok else 'BAD'} {what:12s} {detail}")
            bad += not ok
        return 1 if bad else 0
    target = Target.parse(a.target, a.target_dir) if a.target else None
    jobs = ([{"url": a.url, "tag": a.tag, "args": a.arg}] if a.cmd == "port"
            else json.loads(Path(a.list).read_text(encoding="utf-8")))
    failed = 0
    for j in jobs:
        r = agent.port(j["url"], j["tag"], Path(a.out), arch=a.arch, target=target,
                       max_rounds=a.max_rounds, use_llm=not a.no_model,
                       extra_args=tuple(j.get("args", [])), name=j.get("name", ""))
        failed += r["build_result"] != "built"
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
