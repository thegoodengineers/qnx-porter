"""Campaign failure classification and cross-port diagnostics engine.

Reuses errors.py for compiler/linker diagnostics and crash.py for core dump backtraces.
Classifications match verified findings in docs/LEARNINGS.md and docs/qnx-reports/.
"""
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from . import crash, errors, fixes


class FailureStage(str, Enum):
    CONFIGURE = "configure"
    COMPILE = "compile"
    LINK = "link"
    TEST_EXEC = "test_exec"


class FailureCategory(str, Enum):
    LINUX_KERNEL_API = "linux_kernel_api"
    MISSING_HEADER = "missing_header"
    UNDEFINED_SYMBOL = "undefined_symbol"
    QNX_LIBC_DIFFERENCE = "qnx_libc_difference"
    QNX_API_MISMATCH = "qnx_api_mismatch"
    TOOLCHAIN_FLAG = "toolchain_flag"
    CONFIG_PROBE = "config_probe"
    TARGET_PERMISSION = "target_permission"
    TARGET_RESOURCE = "target_resource"
    TARGET_TOOL = "target_tool"
    TEST_ASSERTION = "test_assertion"
    TEST_CRASH = "test_crash"


class Actionability(str, Enum):
    UNPORTABLE_KERNEL = "unportable_kernel"
    DETERMINISTIC_RULE_CANDIDATE = "deterministic_rule_candidate"
    EXISTING_RULE_COULD_NOT_APPLY = "existing_rule_could_not_apply"
    TARGET_SHIM_CANDIDATE = "target_shim_candidate"
    MODEL_PATCH_CANDIDATE = "model_patch_candidate"
    ENVIRONMENT_CONFIG_CANDIDATE = "environment_config_candidate"
    UPSTREAM_DEFECT_OR_TEST_CAVEAT = "upstream_defect_or_test_caveat"


class Confidence(str, Enum):
    EXACT = "exact"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DiagnosticRecord:
    kind: str
    error: str
    hint: str = ""
    stage: FailureStage = FailureStage.COMPILE
    category: FailureCategory = FailureCategory.COMPILE_SYNTAX if hasattr(FailureCategory, "COMPILE_SYNTAX") else FailureCategory.QNX_API_MISMATCH
    actionability: Actionability = Actionability.MODEL_PATCH_CANDIDATE
    signature: str = "unknown"
    summary: str = ""
    confidence: Confidence = Confidence.MEDIUM
    evidence: str = ""
    hypothesis: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "error": self.error,
            "hint": self.hint,
            "stage": self.stage.value if isinstance(self.stage, Enum) else self.stage,
            "category": self.category.value if isinstance(self.category, Enum) else self.category,
            "actionability": self.actionability.value if isinstance(self.actionability, Enum) else self.actionability,
            "signature": self.signature,
            "summary": self.summary,
            "confidence": self.confidence.value if isinstance(self.confidence, Enum) else self.confidence,
            "evidence": self.evidence,
            "hypothesis": self.hypothesis,
        }


@dataclass
class IntelligenceReport:
    library: str
    arch: str
    overall_status: str  # passed, built_untested, failed_tests, crashed, failed_build
    build_result: str
    tests_passed: int | str
    tests_total: int | str
    diagnostics: list[DiagnosticRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = self.diagnostics[0] if self.diagnostics else None
        return {
            "library": self.library,
            "arch": self.arch,
            "overall_status": self.overall_status,
            "build_result": self.build_result,
            "tests_passed": self.tests_passed,
            "tests_total": self.tests_total,
            "primary_stage": d.stage.value if d else ("test_exec" if self.overall_status == "passed" else "build"),
            "primary_category": d.category.value if d else ("clean_pass" if self.overall_status in ("passed", "built_untested") else "unknown"),
            "primary_actionability": d.actionability.value if d else ("none" if self.overall_status in ("passed", "built_untested") else "investigate"),
            "primary_signature": d.signature if d else ("clean:all_tests_passed" if self.overall_status == "passed" else ("clean:untested" if self.overall_status == "built_untested" else "none")),
            "confidence": d.confidence.value if d else "exact",
            "summary": d.summary if d else ("All executed tests passed cleanly on target." if self.overall_status == "passed" else ("Built successfully; no target tests executed." if self.overall_status == "built_untested" else "No issues identified.")),
            "evidence": d.evidence if d else "",
            "hypothesis": d.hypothesis if d else "",
            "suggested_action": self._suggested_action(),
            "diagnostics": [rec.to_dict() for rec in self.diagnostics],
        }

    def _suggested_action(self) -> str:
        if not self.diagnostics:
            if self.overall_status == "passed":
                return "Ready for deployment / packaging."
            if self.overall_status == "built_untested":
                return "Enable or port target test suite."
            return "Investigate build/test logs."
        act = self.diagnostics[0].actionability
        if act == Actionability.UNPORTABLE_KERNEL:
            return "Do not port: library requires Linux-specific kernel subsystems."
        if act == Actionability.EXISTING_RULE_COULD_NOT_APPLY:
            return "Deterministic rule exists but could not place or apply fix; model patch or upstream fix needed."
        if act == Actionability.DETERMINISTIC_RULE_CANDIDATE:
            return "Add deterministic compatibility rule in qnx_porter/fixes.py."
        if act == Actionability.TARGET_SHIM_CANDIDATE:
            return "Deploy target runtime compatibility shim or configure environment."
        if act == Actionability.UPSTREAM_DEFECT_OR_TEST_CAVEAT:
            return "Document as known QNX libc or upstream test caveat; report or patch upstream."
        return "Apply model patch or adjust build configuration."


def classify_diagnostic(diag: errors.Diagnostic) -> DiagnosticRecord:
    """Classifies a compiler, linker, or build error parsed by errors.py."""
    raw = diag.raw or diag.message
    hint = getattr(diag, "hint", "") or getattr(diag, "header", "")

    # 1. Missing header
    if diag.kind == "missing_header" or (m := re.search(r"\b(?:fatal error:\s*)?(?P<hdr>\S+?):\s*No such file or directory", raw)):
        hdr = diag.header or (m.group("hdr") if m else "")
        if hdr.startswith(("linux/can", "linux/gpio", "linux/soundcard", "linux/i2c-dev")):
            return DiagnosticRecord(
                kind="missing_header", error=raw, hint=hint, stage=FailureStage.COMPILE,
                category=FailureCategory.LINUX_KERNEL_API, actionability=Actionability.UNPORTABLE_KERNEL,
                signature=f"kernel_subsystem:{hdr}", summary=f"Requires Linux kernel subsystem <{hdr}>.",
                confidence=Confidence.EXACT, evidence=raw,
                hypothesis=f"<{hdr}> is part of a Linux kernel subsystem (e.g. SocketCAN, character-device GPIO) not present in QNX.",
            )
        if hdr.startswith(("linux/", "asm/")):
            return DiagnosticRecord(
                kind="missing_header", error=raw, hint=hint, stage=FailureStage.COMPILE,
                category=FailureCategory.LINUX_KERNEL_API, actionability=Actionability.UNPORTABLE_KERNEL,
                signature=f"kernel_header:{hdr}", summary=f"Requires Linux kernel header <{hdr}>.",
                confidence=Confidence.EXACT, evidence=raw,
                hypothesis=f"<{hdr}> is a Linux-specific kernel header; porting requires POSIX alternatives or conditional guards.",
            )
        if hdr in ("endian.h", "byteswap.h", "sys/endian.h"):
            return DiagnosticRecord(
                kind="missing_header", error=raw, hint=hint, stage=FailureStage.COMPILE,
                category=FailureCategory.MISSING_HEADER, actionability=Actionability.EXISTING_RULE_COULD_NOT_APPLY,
                signature=f"missing_header:{hdr}", summary=f"Header <{hdr}> is not in QNX libc. The 'endian-compat' rule exists in fixes.py, but could not resolve this build failure.",
                confidence=Confidence.EXACT, evidence=raw,
                hypothesis=f"Deterministic rule 'endian-compat' exists, but could not apply to or fix this reference.",
            )
        return DiagnosticRecord(
            kind="missing_header", error=raw, hint=hint, stage=FailureStage.COMPILE,
            category=FailureCategory.MISSING_HEADER, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature=f"missing_header:{hdr}", summary=f"Missing header <{hdr}>.",
            confidence=Confidence.HIGH, evidence=raw,
            hypothesis=f"Header <{hdr}> was not found in the QNX SDP sysroot or port source tree.",
        )

    # 2. Undefined symbol / Linker failure
    if diag.kind == "undefined_ref":
        sym = diag.symbol
        if sym.startswith(("std::", "::")):
            return DiagnosticRecord(
                kind="undefined_ref", error=raw, hint=hint, stage=FailureStage.LINK,
                category=FailureCategory.UNDEFINED_SYMBOL, actionability=Actionability.MODEL_PATCH_CANDIDATE,
                signature=f"undefined_symbol:{sym}", summary=f"Undefined C++ symbol '{sym}'.",
                confidence=Confidence.HIGH, evidence=raw,
                hypothesis=f"C++ symbol '{sym}' was not defined in linked object files or libraries.",
            )
        base_sym = sym.lstrip("_")
        if sym in fixes.SOCKET_SYMBOLS or base_sym in fixes.SOCKET_SYMBOLS:
            return DiagnosticRecord(
                kind="undefined_ref", error=raw, hint=hint, stage=FailureStage.LINK,
                category=FailureCategory.UNDEFINED_SYMBOL, actionability=Actionability.EXISTING_RULE_COULD_NOT_APPLY,
                signature=f"socket_symbol:{sym}", summary=f"Symbol '{sym}' requires -lsocket. The 'link-libsocket' rule exists in fixes.py, but could not resolve this link target.",
                confidence=Confidence.EXACT, evidence=raw,
                hypothesis="Socket networking symbols reside in libsocket on QNX. The deterministic rule exists but was not picked up by the build target.",
            )
        if sym in fixes.REGEX_SYMBOLS:
            return DiagnosticRecord(
                kind="undefined_ref", error=raw, hint=hint, stage=FailureStage.LINK,
                category=FailureCategory.UNDEFINED_SYMBOL, actionability=Actionability.EXISTING_RULE_COULD_NOT_APPLY,
                signature=f"regex_symbol:{sym}", summary=f"Symbol '{sym}' requires -lregex. The 'link-libregex' rule exists in fixes.py, but was not applied.",
                confidence=Confidence.EXACT, evidence=raw,
                hypothesis="POSIX regex functions reside in libregex on QNX.",
            )
        return DiagnosticRecord(
            kind="undefined_ref", error=raw, hint=hint, stage=FailureStage.LINK,
            category=FailureCategory.UNDEFINED_SYMBOL, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature=f"undefined_symbol:{sym}", summary=f"Undefined reference to '{sym}'.",
            confidence=Confidence.MEDIUM, evidence=raw,
            hypothesis=f"Symbol '{sym}' was not found in linked libraries.",
        )

    # 3. Compiler options & -Werror
    if diag.kind == "qcc_option":
        return DiagnosticRecord(
            kind="qcc_option", error=raw, hint=hint, stage=FailureStage.COMPILE,
            category=FailureCategory.TOOLCHAIN_FLAG, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature=f"toolchain_option:{diag.symbol}", summary=f"Unsupported compiler option: '{diag.symbol}'.",
            confidence=Confidence.EXACT, evidence=raw,
            hypothesis="qcc does not accept this compiler switch without translation or wrapping.",
        )
    if diag.kind == "werror":
        return DiagnosticRecord(
            kind="werror", error=raw, hint=hint, stage=FailureStage.COMPILE,
            category=FailureCategory.TOOLCHAIN_FLAG, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature="compiler:werror", summary="Fatal warning triggered by -Werror.",
            confidence=Confidence.EXACT, evidence=raw,
            hypothesis="Build configuration enabled -Werror, converting compiler warnings into errors.",
        )

    # 4. Configuration probes
    if diag.kind in ("cmake_error", "configure_error"):
        if (m := re.search(r"(?P<hdr>(?:linux|asm)/\S+?)\s+header not found", raw)):
            hdr = m.group("hdr")
            return DiagnosticRecord(
                kind=diag.kind, error=raw, hint=hint, stage=FailureStage.CONFIGURE,
                category=FailureCategory.LINUX_KERNEL_API, actionability=Actionability.UNPORTABLE_KERNEL,
                signature=f"kernel_header:{hdr}", summary=f"Configure probe requires Linux kernel header <{hdr}>.",
                confidence=Confidence.EXACT, evidence=raw,
                hypothesis=f"Configure check aborted because Linux kernel header <{hdr}> is not present in QNX.",
            )
        return DiagnosticRecord(
            kind=diag.kind, error=raw, hint=hint, stage=FailureStage.CONFIGURE,
            category=FailureCategory.CONFIG_PROBE, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature="config:probe_failed", summary=f"Configuration probe failed: {raw[:100]}",
            confidence=Confidence.MEDIUM, evidence=raw,
            hypothesis="Feature probe or dependency check failed during configuration.",
        )

    # 5. Struct member and undeclared API differences
    if (m := re.search(r"has no member named ['‘’`](\w+)['‘’`]", raw)):
        member = m.group(1)
        return DiagnosticRecord(
            kind=diag.kind, error=raw, hint=hint, stage=FailureStage.COMPILE,
            category=FailureCategory.QNX_API_MISMATCH, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature=f"qnx_api_member:{member}", summary=f"Struct member '{member}' not found in QNX header.",
            confidence=Confidence.HIGH, evidence=raw,
            hypothesis=f"Member '{member}' is missing or named differently in QNX syspage/system structures.",
        )
    if diag.kind == "undeclared":
        return DiagnosticRecord(
            kind=diag.kind, error=raw, hint=hint, stage=FailureStage.COMPILE,
            category=FailureCategory.QNX_API_MISMATCH, actionability=Actionability.MODEL_PATCH_CANDIDATE,
            signature=f"undeclared:{diag.symbol}", summary=f"Identifier '{diag.symbol}' undeclared.",
            confidence=Confidence.HIGH, evidence=raw,
            hypothesis=f"Identifier '{diag.symbol}' is not defined in included headers under QNX.",
        )

    return DiagnosticRecord(
        kind=diag.kind or "error", error=raw, hint=hint, stage=FailureStage.COMPILE,
        category=FailureCategory.QNX_API_MISMATCH, actionability=Actionability.MODEL_PATCH_CANDIDATE,
        signature="compiler:build_error", summary=f"Build error: {raw[:100]}",
        confidence=Confidence.LOW, evidence=raw,
        hypothesis="Compilation failed with an unclassified diagnostic.",
    )


def classify_crash(crash_info: dict, library: str = "") -> DiagnosticRecord | None:
    """Classifies a crash using the GDB backtrace and signal header."""
    bt = crash_info.get("backtrace", "")
    if not bt:
        return None

    # Parse signal from GDB header line
    m = re.search(r"Program terminated with signal (\w+)", bt)
    sig = m.group(1) if m else "SIGSEGV"

    # Parse all frame function names from backtrace
    frame_funcs = [m.group(1) for m in re.finditer(r"^#\d+\s+(?:0x[0-9a-f]+ in )?([A-Za-z0-9_]+)\b", bt, re.M)]

    # 1. QNX libc printf NULL dereference
    if frame_funcs and frame_funcs[0].endswith(("strlen", "strnlen")) and any(
        f in ("_Putfld", "_Printf", "printf", "vsnprintf", "fprintf", "sprintf", "snprintf", "asprintf", "dprintf")
        for f in frame_funcs[1:6]
    ):
        ev = f"Frame #0: {frame_funcs[0]} <- {frame_funcs[1] if len(frame_funcs) > 1 else ''}"
        return DiagnosticRecord(
            kind="crash", error=bt, stage=FailureStage.TEST_EXEC, category=FailureCategory.QNX_LIBC_DIFFERENCE,
            actionability=Actionability.EXISTING_RULE_COULD_NOT_APPLY, signature="crash:printf_null",
            summary="QNX libc strlen() faults on NULL %s argument. The deterministic 'printf-null' rule exists in crash.py, but could not place the fix in caller code.",
            confidence=Confidence.EXACT, evidence=ev,
            hypothesis="printf formatted a NULL pointer with %s. glibc prints '(null)', while QNX libc strlen faults (undefined C; README:259-260, LEARNINGS:139/144).",
        )

    # 2. Known verified causes from docs/LEARNINGS.md
    if library == "googletest" or "fchdir" in bt or "death_test" in bt:
        return DiagnosticRecord(
            kind="crash", error=bt, stage=FailureStage.TEST_EXEC, category=FailureCategory.QNX_LIBC_DIFFERENCE,
            actionability=Actionability.MODEL_PATCH_CANDIDATE, signature="qnx_libc:fchdir_needs_o_directory",
            summary="QNX fchdir() fails with ENOTDIR on a directory opened without O_DIRECTORY (docs/LEARNINGS.md:121).",
            confidence=Confidence.HIGH, evidence=f"Signal {sig} in {library}",
            hypothesis="googletest death-test opens '.' with open(..., O_RDONLY); on QNX 8.0, fchdir() requires O_DIRECTORY.",
        )
    if library == "libsrtp" or "qsort" in bt:
        return DiagnosticRecord(
            kind="crash", error=bt, stage=FailureStage.TEST_EXEC, category=FailureCategory.TEST_CRASH,
            actionability=Actionability.UPSTREAM_DEFECT_OR_TEST_CAVEAT, signature="upstream_test:qsort_random_comparator",
            summary="libsrtp tests shuffle with random qsort comparator, causing QNX qsort to write out of bounds (docs/LEARNINGS.md:130).",
            confidence=Confidence.HIGH, evidence=f"Signal {sig} in {library} tests",
            hypothesis="libsrtp test helper provides a non-deterministic random comparator to qsort(), violating C standard invariants.",
        )

    return DiagnosticRecord(
        kind="crash", error=bt, stage=FailureStage.TEST_EXEC, category=FailureCategory.TEST_CRASH,
        actionability=Actionability.MODEL_PATCH_CANDIDATE, signature=f"crash:{sig.lower()}",
        summary=f"Test binary terminated with signal {sig}.",
        confidence=Confidence.MEDIUM, evidence=f"Program terminated with signal {sig}",
        hypothesis=f"Test binary faulted with {sig}; inspect backtrace frame #0 ({frame_funcs[0] if frame_funcs else 'unknown'}).",
    )


def classify_test_log(log_text: str, library: str = "") -> list[DiagnosticRecord]:
    """Extracts known QNX runtime and environment issues from tests.log."""
    records = []

    # 1. strtod / atof parsing rounding defect (docs/qnx-reports/strtod-rounding.md)
    if (re.search(r"(?:fp_roundtrip|floating.?precision|real[-_]+exponent|real[-_]+subnormal|roundtrip.*double|strtod|atof)", log_text, re.IGNORECASE) or
            re.search(r'"string\(\d+\.\d+\)" does not evaluate to "\d+\.\d+"', log_text)):
        records.append(DiagnosticRecord(
            kind="test_failure", error="strtod/atof parsing mismatch", stage=FailureStage.TEST_EXEC,
            category=FailureCategory.QNX_LIBC_DIFFERENCE, actionability=Actionability.UPSTREAM_DEFECT_OR_TEST_CAVEAT,
            signature="qnx_libc:strtod_rounding",
            summary="QNX 8.0 libc strtod()/atof() parsing is not correctly rounded (docs/qnx-reports/strtod-rounding.md).",
            confidence=Confidence.HIGH, evidence="Floating-point string parsing test mismatch",
            hypothesis="On QNX 8.0, strtod()/atof() returns a double 1-4 ULPs away from correctly rounded value. Formatting is not the problem; sscanf('%lf') parses correctly.",
        ))

    # 2. Missing target runtime tool (with word boundary)
    if (m := re.search(r"\b(?P<tool>killall|ps|slay|pidin|echo|locale)\b:\s*(?:cannot execute|not found|No such file or directory)", log_text)):
        tool = m.group("tool")
        records.append(DiagnosticRecord(
            kind="test_failure", error=m.group(0), stage=FailureStage.TEST_EXEC,
            category=FailureCategory.TARGET_TOOL, actionability=Actionability.TARGET_SHIM_CANDIDATE,
            signature=f"target:missing_tool:{tool}", summary=f"Target environment missing required tool: {tool}.",
            confidence=Confidence.HIGH, evidence=m.group(0),
            hypothesis=f"The test script invokes '{tool}', which is not present in default QNX PATH or image.",
        ))

    # 3. Root execution permission mismatch
    if re.search(r"\b(?:running as root|must not be run as root|cannot run as root|superuser permission)\b", log_text, re.IGNORECASE):
        records.append(DiagnosticRecord(
            kind="test_failure", error="Test suite requires non-root execution", stage=FailureStage.TEST_EXEC,
            category=FailureCategory.TARGET_PERMISSION, actionability=Actionability.ENVIRONMENT_CONFIG_CANDIDATE,
            signature="test:root_permission_mismatch", summary="Test suite expects non-root execution; target runs as root.",
            confidence=Confidence.HIGH, evidence="running as root check in test output",
            hypothesis="POSIX file permission tests fail because the target SSH runner executes as uid 0 (root).",
        ))

    # 4. Target memory exhaustion / OOM
    if re.search(r"\b(?:Allocation error\s*:\s*not enough memory|out of memory|cannot allocate memory|memory allocation failed)\b", log_text, re.IGNORECASE):
        records.append(DiagnosticRecord(
            kind="test_failure", error="Target out of memory", stage=FailureStage.TEST_EXEC,
            category=FailureCategory.TARGET_RESOURCE, actionability=Actionability.ENVIRONMENT_CONFIG_CANDIDATE,
            signature="target:out_of_memory", summary="Target out of memory or allocation failure during test run.",
            confidence=Confidence.HIGH, evidence="Allocation error: not enough memory",
            hypothesis="Test requested memory exceeding the QEMU/target hardware limits (e.g. 2 GiB heap).",
        ))

    return records


def analyze_report(report: dict, logs_dir: Path | None = None) -> IntelligenceReport:
    """Analyzes a report.json and associated logs, producing an IntelligenceReport."""
    lib = report.get("library", "")
    arch = report.get("arch", "x86_64")
    build_result = report.get("build_result", "unknown")
    tests_passed = report.get("tests_passed", 0)
    tests_total = report.get("tests_total", 0)
    tests_ran = report.get("tests_ran", False)

    diagnostics: list[DiagnosticRecord] = []

    # 1. Build failure
    if build_result != "built":
        overall_status = "failed_build"
        for item in report.get("blocked_on", []):
            err_text = item.get("error", "")
            parsed_diags = errors.parse(err_text)
            if parsed_diags:
                d = parsed_diags[0]
            else:
                d = errors.Diagnostic(
                    kind=item.get("kind", "error"),
                    message=err_text,
                    raw=err_text,
                )
            diagnostics.append(classify_diagnostic(d))
        return IntelligenceReport(lib, arch, overall_status, build_result, tests_passed, tests_total, diagnostics)

    # 2. Built, but tests not run or 0 tests
    if not tests_ran or tests_total in ("", 0, None):
        overall_status = "built_untested"
        return IntelligenceReport(lib, arch, overall_status, build_result, tests_passed, tests_total, diagnostics)

    # 3. Built and tested
    has_failing_tests = isinstance(tests_total, int) and isinstance(tests_passed, int) and (tests_passed < tests_total)

    if not has_failing_tests:
        # Clean pass: core files from passing tests do NOT create failing crash classifications
        overall_status = "passed"
        return IntelligenceReport(lib, arch, overall_status, build_result, tests_passed, tests_total, diagnostics)

    # Tests ran and had failures
    crashes = report.get("crashes", [])
    if crashes:
        overall_status = "crashed"
        for c in crashes:
            rec = classify_crash(c, lib)
            if rec:
                diagnostics.append(rec)
    else:
        overall_status = "failed_tests"

    if logs_dir:
        test_log = logs_dir / "tests.log"
        if test_log.is_file():
            text = test_log.read_text(encoding="utf-8", errors="replace")
            diagnostics.extend(classify_test_log(text, lib))

    return IntelligenceReport(lib, arch, overall_status, build_result, tests_passed, tests_total, diagnostics)


def summarize_campaign(ports_dir: Path, arch: str | None = None) -> dict[str, Any]:
    """Aggregates failure intelligence across all reports in ports_dir."""
    report_files = sorted(ports_dir.glob("*/report.json"), key=lambda p: p.parent.name)
    reports = [json.loads(p.read_text(encoding="utf-8")) for p in report_files if p.parent.name != "work"]
    reports = [r for r in reports if r.get("arch") != "host"]

    if arch is not None:
        reports = [r for r in reports if r.get("arch") == arch]
    elif reports:
        arch = reports[0].get("arch", "x86_64")
    else:
        arch = "unknown"

    total = len(reports)
    built_reports = [r for r in reports if r.get("build_result") == "built"]
    built = len(built_reports)
    failed_build = total - built

    untested = [r for r in built_reports if not r.get("tests_ran") or r.get("tests_total") in ("", 0, None)]
    tested = [r for r in built_reports if r.get("tests_ran") and r.get("tests_total") not in ("", 0, None)]

    clean_passed = [r for r in tested if r.get("tests_passed") == r.get("tests_total")]
    failed_tested = [r for r in tested if r.get("tests_passed") < r.get("tests_total")]
    crashed = [r for r in failed_tested if r.get("crashes")]
    failed_only = [r for r in failed_tested if not r.get("crashes")]

    signature_counts = Counter()
    signature_libs = defaultdict(list)
    signature_actionability = {}

    classified_reports = []
    for r in reports:
        logs_dir = ports_dir / r.get("library", "") / "logs"
        rep = analyze_report(r, logs_dir)
        classified_reports.append(rep)
        for d in rep.diagnostics:
            signature_counts[d.signature] += 1
            if r.get("library") not in signature_libs[d.signature]:
                signature_libs[d.signature].append(r.get("library"))
            signature_actionability[d.signature] = d.actionability.value if isinstance(d.actionability, Enum) else d.actionability

    recurring = []
    for sig, cnt in sorted(signature_counts.items(), key=lambda x: (-x[1], x[0])):
        recurring.append({
            "signature": sig,
            "count": cnt,
            "actionability": signature_actionability.get(sig, "unknown"),
            "libraries": sorted(signature_libs[sig]),
        })

    return {
        "arch": arch,
        "total_libraries": total,
        "built": built,
        "failed_build": failed_build,
        "built_untested": len(untested),
        "tested": len(tested),
        "passed_all_tests": len(clean_passed),
        "failed_tests": len(failed_only),
        "crashed": len(crashed),
        "built_rate_pct": round(built / total * 100, 1) if total else 0.0,
        "test_pass_rate_pct": round(len(clean_passed) / len(tested) * 100, 1) if tested else 0.0,
        "recurring_signatures": recurring,
        "ports": [rep.to_dict() for rep in classified_reports],
    }


def render_campaign_summary(summary: dict[str, Any]) -> str:
    """Renders a mathematically accurate, readable Markdown summary."""
    lines = [
        f"Campaign Failure Intelligence Summary (arch: {summary.get('arch', 'unknown')})",
        "=" * 56,
        f"Total Libraries: {summary['total_libraries']}",
        f"Built: {summary['built']} / {summary['total_libraries']} ({summary['built_rate_pct']}%)",
        f"Failed Build: {summary['failed_build']} / {summary['total_libraries']}",
        f"Built (untested): {summary['built_untested']} / {summary['built']}",
        f"Tested: {summary['tested']} / {summary['built']}",
        f"  - Passed all tests: {summary['passed_all_tests']} / {summary['tested']} ({summary['test_pass_rate_pct']}%)",
        f"  - Failed tests: {summary['failed_tests']} / {summary['tested']}",
        f"  - Crashed (failing tests): {summary['crashed']} / {summary['tested']}",
        "",
        "Recurring Failure Signatures",
        "-" * 28,
        "| Signature | Count | Actionability | Libraries |",
        "|---|---|---|---|",
    ]
    for r in summary.get("recurring_signatures", []):
        libs = ", ".join(r["libraries"][:4])
        if len(r["libraries"]) > 4:
            libs += f" (+{len(r['libraries']) - 4} more)"
        lines.append(f"| `{r['signature']}` | {r['count']} | `{r['actionability']}` | {libs} |")
    return "\n".join(lines)


def save_campaign_intelligence(ports_dir: Path, dest: Path, arch: str | None = None) -> dict[str, Any]:
    """Generates campaign intelligence summary on demand and writes to dest."""
    summary = summarize_campaign(ports_dir, arch)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary
