"""Port a Rust crate to QNX 8.0 and prove it with the crate's own tests on a QNX target.

Rust's QNX 8.0 targets (`x86_64-pc-qnx`, `aarch64-unknown-qnx`) are Tier 3: no prebuilt standard library,
so cargo builds `std` from source (`-Zbuild-std`, nightly) and links with the SDP's `qcc`, as the rustc
book's QNX page describes (doc.rust-lang.org/nightly/rustc/platform-support/nto-qnx.html). C code built by a
crate's build.rs goes through the `cc` crate, which reads CC_<target>/AR_<target>; those point at the SDP.

The test binaries `cargo test --no-run` produces run on the target with the crate folder as working
directory, as `cargo test` would run them. Doc tests are not run: they need -Zdoctest-xcompile.
"""
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path

from . import qnx
from .target import SAME_PATH_MARK, Target, _run_one

RUST_TARGETS = {"x86_64": "x86_64-pc-qnx", "aarch64le": "aarch64-unknown-qnx"}
CRATES = "https://static.crates.io/crates/{n}/{n}-{v}.crate"
LIBTEST = re.compile(r"test result: \w+\. (\d+) passed; (\d+) failed; (\d+) ignored")
RUSTC_ERROR = re.compile(r"^error(?:\[(E\d+)\])?: (.+)$", re.M)
# where rustc points: a dependency's source in cargo's registry, e.g. .../libc-0.2.176/src/unix/mod.rs
IN_REGISTRY = re.compile(r"-->\s+(?P<root>\S*/registry/src/[^/\s]+/(?P<name>[A-Za-z0-9_-]+?)-(?P<ver>\d+\.\d+\.\d+[^/\s]*)/)")
NTO = re.compile(r'target_os\s*=\s*"nto"')
IN_CRATE = re.compile(r"-->\s+(?!/)\S+\.rs:\d+")  # the crate's own files: rustc prints them relative
# the linker names the dependency whose code needs a missing symbol: liberrno-4b2a85f8f3fcdda8.rlib(...)
IN_RLIB = re.compile(r"/lib(?P<name>[A-Za-z0-9_]+)-[0-9a-f]+\.rlib\([^)]*\): in function")
# the published .crate leaves out files its tests read (regex's testdata, zstd's assets)
NOT_PUBLISHED = re.compile(r"couldn't read `[^`]+`: No such file|file not found for module")


def fetch(name: str, version: str, work: Path) -> Path:
    """The published .crate (what `cargo publish` uploaded), unpacked under work/src."""
    req = urllib.request.Request(CRATES.format(n=name, v=version), headers={"User-Agent": "qnx-porter"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    src = work / "src"
    shutil.rmtree(src, ignore_errors=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
        t.extractall(src, filter="data")
    return src / f"{name}-{version}"


def cargo_env(arch: str, env: dict, target_dir: Path) -> dict:
    """cargo with the SDP: qcc/q++ for build.rs C code (the cc crate reads CC_<target>), one shared target
    folder per architecture so `std` is built once."""
    a, t = qnx.ARCHES[arch], RUST_TARGETS[arch].replace("-", "_")
    e = dict(env, CARGO_TARGET_DIR=str(target_dir), CARGO_TERM_COLOR="never")
    e.update({f"CC_{t}": qnx.tool(env, "qcc"), f"CXX_{t}": qnx.tool(env, "q++"),
              f"CFLAGS_{t}": f"-V{a.qcc_target}", f"CXXFLAGS_{t}": f"-V{a.qcc_target}_cxx",
              f"AR_{t}": qnx.gnu_tool(env, a.triplet, "ar")})
    return e


def build_tests(crate: Path, arch: str, env: dict, log: Path, config: list[str] = ()) -> tuple[bool, list[dict], str]:
    """`cargo test --no-run` for the QNX target. Returns (ok, test binaries, stderr)."""
    cmd = ["cargo", "+nightly", "test", "--release", "--no-run", "-Zbuild-std", "--target", RUST_TARGETS[arch],
           "--message-format=json-render-diagnostics", *(a for c in config for a in ("--config", c))]
    r = subprocess.run(cmd, cwd=crate, env=env, capture_output=True, text=True, errors="replace")
    log.write_text(f"$ {' '.join(cmd)}  (in {crate})\n\n{r.stderr}", encoding="utf-8")
    bins = []
    for line in r.stdout.splitlines():
        try:
            m = json.loads(line)
        except ValueError:
            continue
        if m.get("reason") == "compiler-artifact" and m.get("profile", {}).get("test") and m.get("executable"):
            kind = m["target"]["kind"][0]
            bins.append({"name": f"{kind}:{m['target']['name']}", "exe": m["executable"]})
    return r.returncode == 0, bins, r.stderr


def plan(stderr: str, done: set, crate: Path | None = None) -> list[dict]:
    """Rules for errors inside dependencies (the crate's own code is not edited):
    - libc-update: the crate's Cargo.lock pins a libc release older than the QNX 8.0 support in libc
      (libc 0.2.176, 0.2.180 and 0.2.186 fail to build for x86_64-pc-qnx, 0.2.191 builds): `cargo update` libc
      within the same semver range.
    - nto-to-qnx: a dependency handles QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`,
      e.g. getrandom: "target is not supported"): a vendored copy takes the QNX 7 code path on QNX 8.0 too,
      applied through cargo's [patch] table.
    """
    fixes = []
    found = [(m["name"], m["ver"], Path(m["root"])) for m in IN_REGISTRY.finditer(stderr)]
    if crate:
        found += [dep for m in IN_RLIB.finditer(stderr) for dep in _registry_dirs(crate, m["name"])]
    for name, ver, root in found:
        if f"{name}@{ver}" in done:
            continue
        done.add(f"{name}@{ver}")
        if name == "libc":
            fixes.append({"rule": "libc-update", "dep": f"libc@{ver}",
                          "reason": f"Cargo.lock pins libc {ver}, which does not build for QNX 8.0; newer libc "
                                    "releases in the same semver range do, so update it there."})
        elif root.is_dir() and _mentions(root, NTO) and not _mentions(root, QNX):
            fixes.append({"rule": "nto-to-qnx", "dep": f"{name}@{ver}", "root": str(root),
                          "reason": f"{name} {ver} supports QNX 7 (`target_os = \"nto\"`) but not QNX 8.0 "
                                    "(`target_os = \"qnx\"`); let QNX 8.0 take the QNX 7 code path."})
    if not fixes and "crate" not in done and crate and IN_CRATE.search(stderr) \
            and _mentions(crate, NTO) and not _mentions(crate, QNX):
        done.add("crate")
        fixes.append({"rule": "nto-to-qnx", "dep": crate.name, "in_crate": True,
                      "reason": "The crate supports QNX 7 (`target_os = \"nto\"`) but not QNX 8.0 "
                                "(`target_os = \"qnx\"`); let QNX 8.0 take the QNX 7 code path."})
    return fixes


QNX = re.compile(r'target_os\s*=\s*"qnx"')
LOCK_ENTRY = re.compile(r'^name = "(?P<name>[^"]+)"\nversion = "(?P<ver>[^"]+)"', re.M)


def _registry_dirs(crate: Path, rlib_name: str) -> list[tuple[str, str, Path]]:
    """The registry sources of the locked package an rlib came from (rlib names use _ for -)."""
    lock = crate / "Cargo.lock"
    if not lock.exists():
        return []
    home = Path(os.environ.get("CARGO_HOME", Path.home() / ".cargo"))
    return [(m["name"], m["ver"], d) for m in LOCK_ENTRY.finditer(lock.read_text(errors="replace"))
            if m["name"].replace("-", "_") == rlib_name
            for d in (home / "registry" / "src").glob(f"*/{m['name']}-{m['ver']}") if d.is_dir()]


def _sources(root: Path) -> list[Path]:
    """Files whose cfg(target_os) decides what builds: Rust sources and Cargo.toml's [target.'cfg(..)'] tables."""
    return sorted([*root.rglob("*.rs"), root / "Cargo.toml"])


def _mentions(root: Path, pattern: re.Pattern) -> bool:
    return any(pattern.search(f.read_text(errors="replace")) for f in _sources(root) if f.exists())


def nto_to_qnx(root: Path, label: str) -> str:
    """Rewrite `target_os = "nto"` as `any(target_os = "nto", target_os = "qnx")` under root; the diff."""
    diff = ""
    for f in _sources(root):
        text = f.read_text(errors="surrogateescape")
        new = NTO.sub('any(target_os = "nto", target_os = "qnx")', text)
        if new != text:
            f.write_text(new, errors="surrogateescape")
            rel = f"{label}/{f.relative_to(root).as_posix()}".lstrip("/")
            diff += "".join(difflib.unified_diff(text.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}"))
    return diff


def apply(fix: dict, crate: Path, env: dict, work: Path, out: Path, n: int, config: list[str]) -> str | None:
    """Apply one fix; returns the patch file (relative to out) that records it, or None if it changed nothing."""
    name = f"patches/{n:04d}-{fix['rule']}-{fix['dep'].replace('@', '-')}.patch"
    (out / "patches").mkdir(parents=True, exist_ok=True)
    head = f"Subject: [qnx-porter {n:04d}] {fix['rule']}\nSource: deterministic rule\nReason: {fix['reason']}\n---\n"
    if fix["rule"] == "nto-to-qnx" and fix.get("in_crate"):
        diff = nto_to_qnx(crate, "")
    elif fix["rule"] == "libc-update":
        lock = crate / "Cargo.lock"
        before = lock.read_text(errors="replace") if lock.exists() else ""
        subprocess.run(["cargo", "+nightly", "update", "-p", fix["dep"]], cwd=crate, env=env, check=True,
                       capture_output=True, text=True)
        diff = "".join(difflib.unified_diff(before.splitlines(True), lock.read_text(errors="replace").splitlines(True),
                                            "a/Cargo.lock", "b/Cargo.lock"))
    else:
        dep, ver = fix["dep"].split("@")
        dst = work / "vendor" / f"{dep}-{ver}"
        shutil.rmtree(dst, ignore_errors=True)
        shutil.copytree(fix["root"], dst)
        diff = nto_to_qnx(dst, f"{dep}-{ver}")
        if not diff:
            return None
        key = f"{dep}_{ver}".replace(".", "_").replace("-", "_")
        config += [f'patch.crates-io.{key}.path="{dst}"', f'patch.crates-io.{key}.package="{dep}"']
    if not diff:
        return None  # e.g. libc was already the newest release in its range
    (out / name).write_text(head + diff, encoding="utf-8")
    return name


def first_errors(stderr: str, n: int = 3) -> list[str]:
    return [m.group(0) for m in RUSTC_ERROR.finditer(stderr)
            if not m.group(2).startswith(("could not compile", "aborting due to"))][:n]


def run_tests(t: Target, crate: Path, bins: list[dict], work: Path, log: Path, limit: int = 600) -> dict:
    """Copy the test binaries and the crate folder to the target and run each binary there."""
    bindir = work / "bin"
    shutil.rmtree(bindir, ignore_errors=True)
    bindir.mkdir()
    for b in bins:
        b["copy"] = shutil.copy2(b["exe"], bindir / Path(b["exe"]).name)
    same = t.sync([crate, bindir])
    if same:
        (work / SAME_PATH_MARK).write_text("")
    passed = failed = ignored = 0
    lines = [f"every test binary runs on {t.host} over ssh, in {crate}\n"]
    for b in bins:
        rc, out = _run_one(t, work, str(crate), [str(b["copy"])], same, [], limit)
        counts = [tuple(map(int, m)) for m in LIBTEST.findall(out)]
        p, f, i = (sum(c[k] for c in counts) for k in range(3))
        if rc != 0 and not f:
            f = 1  # crashed, timed out or failed without a libtest summary: count the binary as one failure
        passed, failed, ignored = passed + p, failed + f, ignored + i
        lines.append(f"{'PASS' if rc == 0 else 'FAIL':5s} {b['name']} (exit {rc}): {p} passed, {f} failed, {i} ignored\n")
        if rc != 0:
            lines.append("".join(f"    {ln}\n" for ln in out.strip().splitlines()[-80:]))
    t.remove([crate, bindir])
    lines.append(f"\n{passed}/{passed + failed} tests passed on the QNX target ({ignored} ignored)\n")
    log.write_text("".join(lines), encoding="utf-8")
    return {"passed": passed, "total": passed + failed, "ignored": ignored}


def port(name: str, version: str, out_root: Path, arch: str = "x86_64", target: Target | None = None,
         tests: bool = True, max_rounds: int = 6, log=print) -> dict:
    t0 = time.time()
    out = out_root / name
    work, logs = out / "work", out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    work.mkdir(exist_ok=True)
    env = cargo_env(arch, qnx.sdp_env(), out_root / f".cargo-target-{arch}")
    log(f"[1/4] fetch {name} {version} from crates.io")
    crate = fetch(name, version, work)
    log(f"[2/4] cargo test --no-run -Zbuild-std --target {RUST_TARGETS[arch]}")
    shutil.rmtree(out / "patches", ignore_errors=True)
    applied, config, done = [], [], set()
    for rnd in range(1, max_rounds + 1):
        ok, bins, stderr = build_tests(crate, arch, env, logs / f"build-{rnd:02d}.log", config)
        fixes = [] if ok else plan(stderr, done, crate)
        if not fixes:
            break
        before = len(applied)
        for f in fixes:
            f["patch"] = apply(f, crate, env, work, out, len(applied) + 1, config)
            if f["patch"]:
                applied.append({k: v for k, v in f.items() if k != "root"})
                log(f"      fix {len(applied):04d} [{f['rule']}] {f['dep']}")
        if len(applied) == before:
            break
    note = ""
    if not ok and NOT_PUBLISHED.search(stderr):
        lib = subprocess.run(["cargo", "+nightly", "build", "--release", "-Zbuild-std", "--target", RUST_TARGETS[arch],
                              *(a for c in config for a in ("--config", c))], cwd=crate, env=env,
                             capture_output=True, text=True, errors="replace")
        (logs / "build-library.log").write_text(lib.stderr, encoding="utf-8")
        if lib.returncode == 0:
            ok, bins, stderr = True, [], ""
            note = "library only: the published crate does not include the files its tests read"
    r = {"crate": name, "version": version, "arch": arch, "rust_target": RUST_TARGETS[arch], "rounds": rnd, "note": note,
         "patches": applied, "build_result": "built" if ok else "failed", "errors": [] if ok else first_errors(stderr),
         "test_binaries": len(bins), "tests_passed": 0, "tests_total": 0, "tests_ignored": 0, "tests_ran": False,
         "target": target.uname() if target else ""}
    if not ok:
        tail = stderr.strip().splitlines()[-1:] or ["no output"]
        log(f"      {('; '.join(r['errors']) or tail[0])[:200]}")
    elif tests and target and bins:
        log(f"[3/4] {len(bins)} test binaries on {target.host}")
        res = run_tests(target, crate, bins, work, logs / "tests.log")
        r.update(tests_passed=res["passed"], tests_total=res["total"], tests_ignored=res["ignored"], tests_ran=True)
        log(f"      {res['passed']}/{res['total']} tests passed ({res['ignored']} ignored)")
    r["minutes"] = round((time.time() - t0) / 60, 1)
    log(f"[4/4] report: {out / 'REPORT.md'}")
    (out / "report.json").write_text(json.dumps(r, indent=2), encoding="utf-8")
    (out / "REPORT.md").write_text(render(r), encoding="utf-8")
    shutil.rmtree(work / "src", ignore_errors=True)
    return r


def render(r: dict) -> str:
    tests = (f"{r['tests_passed']}/{r['tests_total']} passed ({r['tests_ignored']} ignored) on `{r['target']}`"
             if r["tests_ran"] else "not run")
    rows = [("Crate", f"[{r['crate']} {r['version']}](https://crates.io/crates/{r['crate']}/{r['version']})"),
            ("Rust target", f"`{r['rust_target']}` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc)"),
            ("Build", f"**{r['build_result']}**"), ("Crate's own tests", tests),
            ("Test binaries", str(r["test_binaries"])), ("Rounds", str(r["rounds"])),
            ("Patches", str(len(r["patches"]))), ("Time", f"{r['minutes']} min")] + ([("Note", r["note"])] if r["note"] else [])
    s = f"# {r['crate']} {r['version']} on QNX 8.0 ({r['arch']})\n\n| | |\n|---|---|\n"
    s += "".join(f"| {k} | {v} |\n" for k, v in rows)
    if r["patches"]:
        s += "\n## Every change, with its reason\n| # | Rule | Dependency | Reason |\n|---|---|---|---|\n"
        s += "".join(f"| [{i:04d}]({p['patch']}) | {p['rule']} | {p['dep']} | {p['reason']} |\n"
                     for i, p in enumerate(r["patches"], 1))
    if r["errors"]:
        s += "\n## First errors\n" + "".join(f"- `{e}`\n" for e in r["errors"])
    return s + "\nBuild logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.\n"
