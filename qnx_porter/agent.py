"""The porting loop: clone, configure and build for QNX, read the errors, fix, rebuild, then test on target."""
import json
import os
import platform
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from . import build, crash, errors, fixes, llm, patches, qnx
from .target import SAME_PATH_MARK, Target, ctest_on_target, meson_on_target, parse_results, write_wrapper

MODEL_TRIES = 2  # model attempts per error before the agent reports it as blocked
LLM_KINDS = ("error", "implicit_decl", "undeclared", "missing_header", "cmake_error", "werror", "hash_error")


def loose(d: errors.Diagnostic):
    """A diagnostic's identity across rebuilds (line numbers move when a patch adds lines)."""
    return (d.kind, d.file, d.symbol, d.header, d.message)


def port(url: str, tag: str, out_root: Path, arch: str | None = "x86_64", target: Target | None = None,
         max_rounds: int = 15, use_llm: bool = True, extra_args: tuple[str, ...] = (), name: str = "",
         log=print, note: str = "", subdir: str = "") -> dict:
    t0 = time.time()
    name = name or url.rstrip("/").removesuffix(".git").rsplit("/", 1)[-1]
    out = (out_root / name).resolve()
    work, logs = out / "work", out / "logs"
    for d in (out / "patches", logs, work):
        d.mkdir(parents=True, exist_ok=True)
    for old in [*(out / "patches").glob("*.patch"), *logs.glob("*.log")]:
        old.unlink()
    src, bdir = work / "src", work / "build"

    log(f"[1/5] fetch {url} @ {tag}")
    if (src / ".git").exists():
        patches.git(src, "reset", "-q", "--hard", "qnx-porter-base")
        patches.git(src, "clean", "-qfdx")
    else:
        subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "-q", "--depth", "1", "--branch", tag, "--recurse-submodules",
                        "--shallow-submodules", ("file://" + url) if Path(url).is_dir() else url, str(src)], check=True)
        patches.git(src, "tag", "qnx-porter-base")
    base = patches.git(src, "rev-parse", "HEAD").strip()
    shutil.rmtree(bdir, ignore_errors=True)
    bdir.mkdir()

    build_src = src / subdir if subdir else src  # some projects keep their build files in a subfolder
    system = build.detect(build_src)
    env = qnx.sdp_env() if arch else dict(os.environ)
    a = qnx.ARCHES[arch] if arch else None
    flags = qnx.Flags()
    if a:  # QNX keeps pthread, rt and dl in libc: empty stand-ins let `-ldl` and CMake's library checks succeed
        (work / "stubs").mkdir(exist_ok=True)
        for lib in fixes.IN_LIBC:
            (work / "stubs" / f"lib{lib}.a").write_bytes(b"!<arch>\n")
        flags.stub_dir = str(work / "stubs")
    job = build.Job(build_src, bdir, system, a, env, flags, extra_args=tuple(extra_args))
    if target:
        job.emulator = write_wrapper(work / "qnx-run", target, work)
    log(f"[2/5] build system: {system}; target: {a.triplet if a else 'host compiler (self-test)'}")

    applied: list[patches.Patch] = []
    tried: set = set()
    pending = None  # (patch, diagnostic it should clear, diagnostics before): a patch on probation
    blocked: list[dict] = []
    ok, rounds = False, 0
    for rounds in range(1, max_rounds + 1):
        tc = job.toolchain_path()
        if tc.exists() and tc.read_text(encoding="utf-8") != job.toolchain_text():
            # CMake reads CMAKE_*_INIT only into a fresh cache: a flag fix is invisible until it is wiped.
            (bdir / "CMakeCache.txt").unlink(missing_ok=True)
            shutil.rmtree(bdir / "CMakeFiles", ignore_errors=True)
        tc.write_text(job.toolchain_text(), encoding="utf-8")
        ok, text = build.run(job.steps(tests=True), work, env, logs / f"round-{rounds:02d}.log")
        diags = [] if ok else errors.parse(text) or [errors.Diagnostic("error", _tail(text))]
        if pending:
            p, want_gone, before = pending
            pending = None
            now = {loose(d) for d in diags}
            # New errors elsewhere are progress (a compile fix lets the linker run); new errors in the
            # files the patch touched, or the same error again, mean the patch did not work.
            touched = {loose(d) for d in diags if loose(d) not in before and d.file
                       and fixes.in_tree(src, d.file) in set(p.files)}
            if not ok and (want_gone in now or touched):
                patches.revert_last(src)
                p.kept = False
                log(f"      patch {p.number:04d} ({p.source}) did not clear the error: reverted")
                ok, text = build.run(job.steps(tests=True), work, env, logs / f"round-{rounds:02d}b.log")
                diags = [] if ok else errors.parse(text) or [errors.Diagnostic("error", _tail(text))]
        if ok:
            log(f"[3/5] build OK after {rounds} round(s)")
            break
        log(f"      round {rounds}: {len(diags)} error(s); first: {diags[0].raw or diags[0].message}"[:200])

        planned = fixes.plan(diags, src, flags, tried)
        safe = [f for f in planned if not f.verify]
        for f in safe or planned[:1]:  # a fix that needs proof goes alone, so its rebuild judges only it
            tried.add(f.key())
            n = len(applied) + 1
            applied.append(_apply(f, n, src, out, job, work))
            log(f"      fix {n:04d} [{f.rule}] {f.reason}"[:200])
            if f.verify:
                pending = (applied[-1], loose(f.diag), {loose(d) for d in diags})
        if planned:
            continue
        if use_llm and llm.configured():
            p = _ask_model(diags, src, out, len(applied) + 1, text, tried, log)
            if p:
                applied.append(p)
                pending = (p, p._diag, {loose(d) for d in diags})
                continue
        blocked = [{"kind": d.kind, "error": d.raw or d.message, "hint": fixes.hint(d)}
                   for d in diags[:8]]
        log("      no rule or model fix left for: " + (diags[0].raw or diags[0].message)[:160])
        break

    tests_passed = tests_total = 0
    uname = ""
    crashes: list[dict] = []
    not_runnable: list[dict] = []
    if ok and target and job.test_cmd():
        uname = target.uname()
        log(f"[4/5] tests on target {target.host}:{target.port} ({uname or 'uname failed'})")
        tests_passed, tests_total, crashes, not_runnable = _run_tests(job, target, src, bdir, work, env, logs)
        log(f"      {tests_passed}/{tests_total} tests passed")
        # A crash the backtrace explains mechanically gets a patch; it stays only if the re-run is better.
        crash_fixes = []
        for c in crashes:
            if (r := crash.printf_null(c["backtrace"], src, fixes.in_tree)) and r[0] not in {f[0] for f in crash_fixes}:
                crash_fixes.append(r)
        if crash_fixes:
            before = (tests_passed, tests_total, crashes, not_runnable)
            first = len(applied)
            for rel, reason, text in crash_fixes:
                (src / rel).write_text(text, encoding="utf-8", errors="surrogateescape")
                applied.append(patches.commit_source(src, out, len(applied) + 1, "printf-null", "rule", reason,
                                                     "Memory fault (SIGSEGV) in strlen <- printf on QNX", [rel]))
                log(f"      fix {len(applied):04d} [printf-null] {reason}"[:200])
            rebuilt, _ = build.run(job.steps(tests=True), work, env, logs / "rebuild-after-crash-fix.log")
            if rebuilt:
                tests_passed, tests_total, crashes, not_runnable = _run_tests(job, target, src, bdir, work, env, logs)
                log(f"      after crash fixes: {tests_passed}/{tests_total} tests passed")
            if not rebuilt or tests_passed <= before[0]:
                for p in applied[first:]:
                    patches.revert_last(src)
                    p.kept = False
                tests_passed, tests_total, crashes, not_runnable = before
                log("      crash fixes did not help: reverted")
    elif ok:
        log("[4/5] tests skipped: " + (note or ("no --target given" if not target
                                                 else "no test runner for " + system)))

    kept = [p for p in applied if p.kept]
    patches.export_series(src, base, out)
    report = {
        "library": name, "url": url, "version": tag, "commit": base, "build_system": system,
        "arch": arch or "host", "sdp": "QNX SDP 8.0" if arch else "none (host self-test)",
        "host": f"{platform.system()} {platform.release()}", "target": uname,
        "build_result": "built" if ok else "failed", "rounds": rounds,
        "tests_passed": tests_passed, "tests_total": tests_total, "tests_ran": bool(ok and target and uname),
        "patches_kept": len(kept), "patches_by_rule": sum(p.source == "rule" for p in kept),
        "patches_by_model": sum(p.source == "model" for p in kept),
        "patches": [p.to_dict() for p in applied], "blocked_on": blocked,
        "minutes": round((time.time() - t0) / 60, 1), "note": note,
        "tests_not_runnable": not_runnable,
        "crashes": [{"binary": Path(c["binary"]).name, "backtrace": c["backtrace"]} for c in crashes],
        "finished": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (out / job.toolchain_path().name).write_text(job.toolchain_text(), encoding="utf-8")
    if (work / "qnx-compat").is_dir():  # headers the toolchain -includes, kept with the port
        shutil.copytree(work / "qnx-compat", out / "qnx-compat", dirs_exist_ok=True)
    (out / "REPORT.md").write_text(render(report, job), encoding="utf-8")
    log(f"[5/5] report: {out / 'REPORT.md'}")
    return report


def _run_tests(job: build.Job, target: Target, src: Path, bdir: Path, work: Path, env: dict,
               logs: Path) -> tuple[int, int, list[dict]]:
    """Copy the trees to the target, run the library's tests there, and collect any core dumps."""
    if job.pretest_cmd():  # automake builds its test programs only in `make check`: build them first
        build.run([job.pretest_cmd()], work, env, logs / "tests-build.log")
    same = target.sync([src, bdir, work / "stubs"] if (work / "stubs").exists() else [src, bdir])
    (work / SAME_PATH_MARK).unlink(missing_ok=True)
    if same:
        (work / SAME_PATH_MARK).write_text("")
    crash.clear_cores(target)
    not_runnable = []
    if job.system in ("cmake", "meson"):
        r = (ctest_on_target(target, bdir, work, job.emulator, same, logs / "tests.log") if job.system == "cmake"
             else meson_on_target(target, bdir, work, same, logs / "tests.log"))
        passed, total, not_runnable = r["passed"], r["total"], r["not_runnable"]
    else:
        _, ttext = build.run([job.test_cmd()], work, env, logs / "tests.log")
        if job.system == "autotools":  # each test's own log has the QNX output
            ttext += "".join(f"\n--- {p.relative_to(bdir)}\n" + p.read_text(errors="replace")[-3000:]
                             for p in sorted(bdir.rglob("*.log")) if p.name not in ("config.log", "test-suite.log"))
            (logs / "tests.log").write_text(ttext, encoding="utf-8")
        passed, total = parse_results(job.system, ttext)
    crashes = crash.collect(target, bdir, env, job.arch.triplet, work / "cores") if job.arch else []
    target.remove([src, bdir, work / "stubs"])
    if crashes:
        (logs / "crashes.log").write_text("".join(
            f"=== {c['binary']}\n{c['backtrace'] or '(no backtrace: binary not found on the host)'}\n\n"
            for c in crashes), encoding="utf-8")
    return passed, total, crashes, not_runnable


def _tail(text: str) -> str:
    return "\n".join(text.strip().splitlines()[-15:])


def _apply(f: fixes.Fix, n: int, src: Path, out: Path, job: build.Job, work: Path) -> patches.Patch:
    error = f.diag.raw or f.diag.message
    if f.edits:
        for rel, text in f.edits.items():
            (src / rel).write_text(text, encoding="utf-8", errors="surrogateescape")
        return patches.commit_source(src, out, n, f.rule, "rule", f.reason, error, list(f.edits))
    before = job.toolchain_text()
    extra = ""
    for name, text in f.compat.items():
        d = work / "qnx-compat"
        d.mkdir(exist_ok=True)
        (d / name).write_text(text, encoding="utf-8")
        job.flags.cflags += ["-include", str(d / name)]
        extra += "".join(["--- /dev/null\n", f"+++ b/qnx-compat/{name}\n",
                          f"@@ -0,0 +1,{len(text.splitlines())} @@\n",
                          *[f"+{ln}\n" for ln in text.splitlines()]])
    job.flags.cflags += f.cflags
    for k, v in f.settings.items():
        setattr(job.flags, k, v)
    if f.late:
        job.flags.late += f.late
        if job.arch:  # cross builds: wrappers put these flags after the project's own
            qnx.write_wrappers(job.env, job.flags, work / "wrap", job.arch)
        else:  # host self-test: the host compiler takes them through CFLAGS
            job.flags.cflags += f.late
    job.flags.ldflags += f.ldflags
    job.flags.libs += f.libs
    for lib in f.stubs:
        stub = work / "stubs"
        stub.mkdir(exist_ok=True)
        (stub / f"lib{lib}.a").write_bytes(b"!<arch>\n")  # an empty ar archive
        job.flags.stub_dir = str(stub)
    return patches.record_flags(out, n, f.rule, f.reason, error, job.toolchain_path().name, before,
                                job.toolchain_text(), extra)


def _ask_model(diags, src: Path, out: Path, n: int, log_text: str, tried: set, log):
    for d in diags:
        rel = fixes.in_tree(src, d.file) if d.file else None
        attempt = sum(1 for k in tried if k[:2] == ("model", loose(d)))
        if d.kind not in LLM_KINDS or not rel or attempt >= MODEL_TRIES:
            continue
        tried.add(("model", loose(d), attempt))
        log(f"      asking the model about: {d.raw or d.message}"[:200])
        try:
            reply = llm.ask(llm.context(src, d, rel, fixes.hint(d), log_text))
        except Exception as e:  # network, quota, bad JSON: report it and fall through to "blocked"
            log(f"      model call failed: {e}")
            return None
        if not reply["diff"].strip():
            log(f"      model declined: {reply['reason']}")
            continue
        ok, why = patches.apply_diff(src, reply["diff"])
        if not ok:
            log(f"      model diff did not apply: {why[:160]}")
            continue
        files = patches.changed_files(reply["diff"])
        p = patches.commit_source(src, out, n, "model-fix", "model", reply["reason"], d.raw or d.message, files)
        p._diag = loose(d)
        log(f"      fix {n:04d} [model] {reply['reason']}"[:200])
        return p
    return None


def render(r: dict, job: build.Job) -> str:
    rows = "\n".join(f"| [{p['number']:04d}]({p['path']}) | {p['rule']} | {p['source']} | "
                     f"{'kept' if p['kept'] else 'reverted'} | {', '.join(p['files'])} | {p['reason']} |"
                     for p in r["patches"]) or "| - | - | - | - | - | no changes needed |"
    blocked = "\n".join(f"- `{b['error'][:200]}`" + (f"  \n  QNX note: {b['hint']}" if b["hint"] else "")
                        for b in r["blocked_on"]) or "- nothing"
    crashes = "".join(f"\n## Crash on QNX: {c['binary']}\nBacktrace from the core dump (SDP gdb):\n```\n"
                      f"{c['backtrace'] or 'no backtrace'}\n```\n" for c in r.get("crashes", []))
    tests = (f"{r['tests_passed']}/{r['tests_total']} passed on `{r['target']}`" if r["tests_ran"]
             else "not run")
    where = f"on QNX 8.0 ({r['arch']})" if r["arch"] != "host" else "(self-test with the host compiler, not QNX)"
    return f"""# {r['library']} {r['version']} {where}

| | |
|---|---|
| Upstream | {r['url']} at `{r['version']}` (`{r['commit'][:12]}`) |
| Build system | {r['build_system']} |
| Toolchain | {r['sdp']}, `{job.toolchain_path().name}` in this folder |
| Build | **{r['build_result']}** after {r['rounds']} round(s) |
| Library's own tests | {tests} |
| Patches kept | {r['patches_kept']} ({r['patches_by_rule']} by rule, {r['patches_by_model']} by model) |
| Time | {r['minutes']} min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
{rows}

{('Note: ' + r['note']) if r.get('note') else ''}

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
{blocked if r['build_result'] == 'failed' else '- nothing'}
{crashes}"""
