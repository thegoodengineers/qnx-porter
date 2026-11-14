"""Port every library in campaign.yaml to QNX 8.0, then write results/ports.csv and the README table.

The day the SDP is installed this is the only command to run:
    source ~/qnx800/qnxsdp-env.sh
    python3 scripts/run_campaign.py

It stops before doing anything if qcc or the QNX target is missing, and says which SETUP.md step fixes it.
Each library's patches, diff (qnx.patch), toolchain file and logs land in ports/<name>/.
"""
import argparse
import dataclasses
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from qnx_porter import agent, qnx  # noqa: E402
from qnx_porter.target import Target  # noqa: E402

REQUIRED = ("name", "url", "tag")


def load(path: Path) -> dict:
    c = yaml.safe_load(path.read_text(encoding="utf-8"))
    libs = c.get("libraries") or []
    for lib in libs:
        missing = [k for k in REQUIRED if not lib.get(k)]
        if missing:
            raise SystemExit(f"{path}: library {lib} is missing {', '.join(missing)}")
        lib["tag"] = str(lib["tag"])
        lib["args"] = [str(a) for a in lib.get("args", [])]
        lib["arch_args"] = {k: [str(a) for a in v] for k, v in (lib.get("arch_args") or {}).items()}
        lib["tests"] = lib.get("tests", True) is not False
        lib["note"] = str(lib.get("note", ""))
        lib["subdir"] = str(lib.get("subdir", ""))
        lib["run_as"] = str(lib.get("run_as", ""))
        lib["test_timeout"] = int(lib.get("test_timeout", 300))
        lib["uses"] = [str(u) for u in lib.get("uses", [])]
    names = [lib["name"] for lib in libs]
    for i, lib in enumerate(libs):
        late = [u for u in lib["uses"] if u not in names[:i]]
        if late:
            raise SystemExit(f"{path}: {lib['name']} uses {', '.join(late)}, which must be listed before it")
    return {"target": c.get("target"), "target_dir": c.get("target_dir", "/data/qnx-porter"),
            "arch": c.get("arch", "x86_64"), "max_rounds": int(c.get("max_rounds", 15)), "libraries": libs,
            "skip_ported": bool(c.get("skip_ported", True))}


def preflight(env_source=None) -> dict:
    """The SDP environment, or exit with the SETUP.md step that fixes what is missing."""
    try:
        env = qnx.sdp_env(env_source)
    except SystemExit:
        raise SystemExit("QNX SDP 8.0 not found (no QNX_HOST/QNX_TARGET and no ~/qnx800/qnxsdp-env.sh).\n"
                         "Install it with SETUP.md step 3, then run: source ~/qnx800/qnxsdp-env.sh") from None
    qcc = Path(qnx.tool(env, "qcc"))
    if not qcc.exists():
        raise SystemExit(f"qcc not found at {qcc}. QNX_HOST={env.get('QNX_HOST')} does not hold an SDP 8.0 "
                         "install. See SETUP.md step 3, and run `qnx-porter doctor`.")
    return env


def check_target(t: Target) -> str:
    uname = t.uname()
    if not uname:
        raise SystemExit(f"QNX target {t.host}:{t.port} did not answer over ssh. Start it with SETUP.md step 4 "
                         "(mkqnximage --run=-h), or pass --no-tests to build only.")
    return uname


def already_on_oss(libs: list[dict], names: set, urls: set) -> list[str]:
    """Libraries oss.qnx.com now lists: same package name (or name-<subpackage>) or same upstream URL."""
    def listed(lib):
        n, url = lib["name"].lower(), lib["url"].lower().rstrip("/").removesuffix(".git")
        return url in urls or any(x == n or x.startswith(n + "-") for x in names)
    return [lib["name"] for lib in libs if listed(lib)]


def default_branch(url: str) -> str:
    """The branch upstream's HEAD points at (`git ls-remote --symref`), or "" if it cannot be read."""
    r = subprocess.run(["git", "ls-remote", "--symref", url, "HEAD"], capture_output=True, text=True, timeout=120)
    m = re.search(r"^ref: refs/heads/(\S+)\s+HEAD", r.stdout, re.M)
    return m.group(1) if m else ""


def for_library(target: Target | None, lib: dict) -> Target | None:
    """The target as this library's tests need it: as another user (`run_as`) for suites that refuse root, and
    with a longer cap per test (`test_timeout`) for suites that are slow on QNX."""
    if not target:
        return target
    return dataclasses.replace(target, run_as=lib.get("run_as") or target.run_as,
                               test_timeout=lib.get("test_timeout") or target.test_timeout)


def finished(report: Path) -> bool:
    try:
        return json.loads(report.read_text(encoding="utf-8")).get("build_result") not in (None, "error")
    except (OSError, ValueError):
        return False


def alive(target: Target, restart: str | None) -> bool:
    """True if the target answers over ssh, restarting it once with `restart` if it does not."""
    if target.uname():
        return True
    if not restart:
        return False
    print(f"    the QNX target does not answer; restarting it: {restart}", flush=True)
    subprocess.run(restart, shell=True)
    for _ in range(30):  # a QEMU boot takes a while, an emulated aarch64 one longer
        if target.uname():
            return True
        time.sleep(20)
    return False


def error_report(out: Path, lib: dict, arch: str, err: str, minutes: float) -> None:
    """A report.json for a library the agent could not even start on, so the CSV still shows it."""
    d = out / lib["name"]
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.json").write_text(json.dumps({
        "library": lib["name"], "url": lib["url"], "version": lib["tag"], "commit": "", "build_system": "",
        "arch": arch, "sdp": "QNX SDP 8.0", "target": "", "build_result": "error", "rounds": 0,
        "tests_passed": 0, "tests_total": 0, "tests_ran": False, "patches_kept": 0, "patches_by_rule": 0,
        "patches_by_model": 0, "patches": [], "blocked_on": [{"kind": "error", "error": err[-2000:], "hint": ""}],
        "minutes": round(minutes, 1), "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }, indent=2), encoding="utf-8")


def low_disk(paths: list[str], min_gb: float) -> list[tuple[str, float]]:
    """(path, GiB free) for each existing path with less than min_gb free."""
    free = [(p, shutil.disk_usage(p).free / 2**30) for p in paths if Path(p).exists()]
    return [(p, gb) for p, gb in free if gb < min_gb]


def wait_for_disk(paths: list[str], min_gb: float, pause: float = 60, sleep=time.sleep) -> None:
    """Pause before the next library while a watched disk is low, and continue once there is room again.
    On WSL, watch the Windows drive that holds the distribution's ext4.vhdx (QNX_PORTER_DISK_WATCH=/mnt/d):
    when that drive filled up on 14 Nov 2026, the Linux filesystem went read-only and WSL stopped starting."""
    told = False
    while low := low_disk(paths, min_gb):
        if not told:
            print("    paused: " + ", ".join(f"{p} has {gb:.1f} GiB free" for p, gb in low)
                  + f" (under {min_gb:g} GiB). Free some space and the campaign continues.", flush=True)
            told = True
        sleep(pause)
    if told:
        print("    disk space is back: continuing", flush=True)


def tidy(out: Path, name: str, keep: set[str]) -> None:
    """Delete a finished library's build tree (work/build, the bulk of its disk use). work/src stays for
    scripts/sbom.py; libraries that others list under `uses` keep their build, which those link against."""
    if name not in keep:
        shutil.rmtree(out / name / "work" / "build", ignore_errors=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", default=str(ROOT / "campaign.yaml"))
    ap.add_argument("--out", help="default: ports/ for x86_64, ports-<arch>/ otherwise")
    ap.add_argument("--arch", help="override campaign.yaml (x86_64 or aarch64le)")
    ap.add_argument("--target", help="override campaign.yaml: user@host[:port], or 'none' to build only")
    ap.add_argument("--only", help="comma-separated library names")
    ap.add_argument("--no-tests", action="store_true", help="build only, do not use the QNX target")
    ap.add_argument("--no-model", action="store_true", help="deterministic rules only")
    ap.add_argument("--skip-oss-check", action="store_true", help="do not re-check oss.qnx.com first")
    ap.add_argument("--head", action="store_true",
                    help="port each library's upstream default branch (HEAD) instead of its pinned tag")
    ap.add_argument("--resume", action="store_true",
                    help="skip libraries that already have a report in the output folder (not 'error' ones)")
    ap.add_argument("--restart-target", metavar="CMD",
                    help="shell command that restarts a QNX target that stopped answering, e.g. "
                         "'QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh restart'")
    ap.add_argument("--keep-work", action="store_true",
                    help="keep each library's work/build tree (default: delete it once its report is written)")
    ap.add_argument("--min-free-gb", type=float, default=5,
                    help="pause before the next library while a watched disk has less free (default 5 GiB); "
                         "watched: / and the paths in QNX_PORTER_DISK_WATCH (colon-separated)")
    a = ap.parse_args(argv)
    watch = ["/", *filter(None, os.environ.get("QNX_PORTER_DISK_WATCH", "").split(":"))]

    c = load(Path(a.campaign))
    if a.arch:
        c["arch"] = a.arch
    if a.target:
        c["target"] = None if a.target == "none" else a.target
    libs = [lib for lib in c["libraries"] if not a.only or lib["name"] in a.only.split(",")]
    if a.head:
        for lib in libs:
            lib["tag"] = default_branch(lib["url"]) or lib["tag"]
    preflight()
    target = None
    if c["target"] and not a.no_tests:
        target = Target.parse(c["target"], c["target_dir"])
        print(f"target: {check_target(target)}")
    if not a.skip_oss_check:
        from check_candidates import oss_packages
        listed = ROOT / "results" / "oss_listed.json"  # read by ports_csv.py for the on_oss_qnx_com column
        old = set(json.loads(listed.read_text())) if listed.exists() else set()
        try:
            ported = already_on_oss(libs, *oss_packages())
        except OSError as e:  # the site is down or resets the connection: keep the last saved answer
            ported = sorted(old & {lib["name"] for lib in libs})
            print(f"oss.qnx.com check failed ({e}); using the last saved list in {listed.relative_to(ROOT)}")
        listed.write_text(json.dumps(sorted(old - {lib["name"] for lib in libs} | set(ported)), indent=1) + "\n")
        for name in ported:
            print(f"{'skip' if c['skip_ported'] else 'note'} {name}: oss.qnx.com lists it")
        if c["skip_ported"]:
            libs = [lib for lib in libs if lib["name"] not in ported]

    out = Path(a.out) if a.out else ROOT / ("ports" if c["arch"] == "x86_64" else f"ports-{c['arch']}")
    if a.resume:
        done = [lib["name"] for lib in libs if finished(out / lib["name"] / "report.json")]
        libs = [lib for lib in libs if lib["name"] not in done]
        print(f"resume: {len(done)} libraries already have a report in {out}; {len(libs)} to go")
    used = {u for lib in c["libraries"] for u in lib["uses"]}
    for i, lib in enumerate(libs, 1):
        wait_for_disk(watch, a.min_free_gb)
        print(f"\n=== [{i}/{len(libs)}] {lib['name']} {lib['tag']} ===")
        t0 = time.time()
        if target and lib["tests"] and not alive(target, a.restart_target):
            print("the QNX target does not answer and could not be restarted: stopping here; "
                  "re-run with --resume to continue from this library")
            break
        try:
            agent.port(lib["url"], lib["tag"], out, arch=c["arch"], target=for_library(target, lib) if lib["tests"] else None,
                       max_rounds=c["max_rounds"], use_llm=not a.no_model,
                       extra_args=tuple(lib["args"] + lib["arch_args"].get(c["arch"], [])),
                       name=lib["name"], note=lib["note"], subdir=lib["subdir"],
                       deps=[out / u / "work" / "build" for u in lib["uses"]])
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError, RuntimeError, ValueError) as e:
            print(f"    {lib['name']}: agent error: {e}")
            error_report(out, lib, c["arch"], str(e), (time.time() - t0) / 60)
        if not a.keep_work:
            tidy(out, lib["name"], used)
    subprocess.run([sys.executable, str(ROOT / "scripts" / "ports_csv.py")], check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
