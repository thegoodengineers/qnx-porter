"""qnx-porter: port an open-source C/C++ library to QNX 8.0 and prove it with the library's own tests."""
import argparse
import json
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
    p.add_argument("url", help="git URL of the library, or a local git checkout")
    p.add_argument("--tag", default="", help="release tag or branch (default: the default branch)")
    p.add_argument("--subdir", default="", help="folder that holds the build files, if not the top level")
    p.add_argument("--name", default="", help="name of the port folder (default: from the URL)")
    p.add_argument("--arg", action="append", default=[], help="extra configure argument (repeatable)")
    for s in (p,):
        s.add_argument("--arch", default="x86_64", choices=sorted(qnx.ARCHES))
        s.add_argument("--target", help="QNX target for tests, user@host[:port] (e.g. root@172.31.1.11)")
        s.add_argument("--target-dir", default="/data/qnx-porter", help="scratch folder on the target")
        s.add_argument("--out", default="ports", help="where port folders are written")
        s.add_argument("--max-rounds", type=int, default=15)
        s.add_argument("--no-model", action="store_true", help="deterministic rules only")

    c = sub.add_parser("crate", help="port one Rust crate from crates.io and run its tests on QNX")
    c.add_argument("name")
    c.add_argument("--version", required=True, help="crate version, e.g. 1.0.154")
    c.add_argument("--arch", default="x86_64", choices=sorted(qnx.ARCHES))
    c.add_argument("--target", help="QNX target for tests, user@host[:port]")
    c.add_argument("--target-dir", default="/data/qnx-porter", help="scratch folder on the target")
    c.add_argument("--out", default="ports-rust", help="where crate folders are written")

    d = sub.add_parser("detect", help="print the build system of a source folder")
    d.add_argument("path")
    dr = sub.add_parser("doctor", help="check the QNX SDP 8.0 install, host tools and (optionally) the target")
    dr.add_argument("--target", help="also check this QNX target answers over ssh, user@host[:port]")
    st = sub.add_parser("selftest", help="run the loop on a deliberately broken library with the host "
                                         "compiler (no QNX needed)")
    st.add_argument("--out", default="ports-selftest")
    dg = sub.add_parser("diagnose", help="diagnose failures and recurring patterns across a port or campaign")
    dg.add_argument("path", nargs="?", default="ports", help="path to a ports folder, port folder, or report.json")
    dg.add_argument("--json", action="store_true", help="output structured JSON")

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
    if a.cmd == "diagnose":
        from . import intelligence
        p = Path(a.path)
        if not p.exists():
            print(f"qnx-porter diagnose: error: path '{p}' does not exist", file=sys.stderr)
            return 1

        report_file = None
        logs_dir = None
        if p.is_file():
            if not p.name.endswith(".json"):
                print(f"qnx-porter diagnose: error: file '{p}' is not a JSON report", file=sys.stderr)
                return 1
            report_file = p
            logs_dir = p.parent / "logs"
        elif (p / "report.json").is_file():
            report_file = p / "report.json"
            logs_dir = p / "logs"

        if report_file is not None:
            try:
                data = json.loads(report_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
                print(f"qnx-porter diagnose: error: malformed report JSON in '{report_file}': {e}", file=sys.stderr)
                return 1
            res = intelligence.analyze_report(data, logs_dir).to_dict()
            if a.json:
                print(json.dumps(res, indent=2))
            else:
                lib_name = data.get("library") or report_file.parent.name
                arch_name = data.get("arch", "unknown")
                print(f"Library: {lib_name} ({arch_name})")
                print(f"Overall Status: {res['overall_status']}")
                print(f"Stage: {res['primary_stage']}")
                print(f"Category: {res['primary_category']}")
                print(f"Actionability: {res['primary_actionability']}")
                print(f"Confidence: {res.get('confidence', 'medium')}")
                print(f"Signature: {res['primary_signature']}")
                print(f"Summary: {res['summary']}")
                if res.get("hypothesis"):
                    print(f"Hypothesis: {res['hypothesis']}")
                if res.get("evidence"):
                    print(f"Evidence: {res['evidence']}")
                print(f"Suggested Action: {res['suggested_action']}")
            return 0

        if not list(p.glob("*/report.json")):
            print(f"qnx-porter diagnose: error: no report.json files found under '{p}'", file=sys.stderr)
            return 1
        summary = intelligence.summarize_campaign(p)
        if summary.get("total_libraries", 0) == 0:
            print(f"qnx-porter diagnose: error: failed to parse any valid reports in '{p}'", file=sys.stderr)
            return 1
        if a.json:
            print(json.dumps(summary, indent=2))
        else:
            print(intelligence.render_campaign_summary(summary))
        return 0
    target = Target.parse(a.target, a.target_dir) if a.target else None
    if a.cmd == "crate":
        from . import crate
        r = crate.port(a.name, a.version, Path(a.out), arch=a.arch, target=target)
        return 0 if r["build_result"] == "built" else 1
    r = agent.port(a.url, a.tag, Path(a.out), arch=a.arch, target=target, max_rounds=a.max_rounds,
                   use_llm=not a.no_model, extra_args=tuple(a.arg), name=a.name, subdir=a.subdir)
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
