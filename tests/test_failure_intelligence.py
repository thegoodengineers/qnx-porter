from __future__ import annotations

import json
from pathlib import Path
import pytest

from qnx_porter import errors, intelligence
from qnx_porter.cli import main as cli_main
from qnx_porter.intelligence import (
    Actionability,
    Confidence,
    DiagnosticRecord,
    FailureCategory,
    FailureStage,
    IntelligenceReport,
    analyze_report,
    classify_crash,
    classify_diagnostic,
    classify_test_log,
    render_campaign_summary,
    save_campaign_intelligence,
    summarize_campaign,
)


def test_built_untested_libraries_do_not_inflate_pass_counts(tmp_path):
    """24 untested libraries must have status built_untested and never inflate clean test pass counts."""
    campaign = tmp_path / "campaign"
    campaign.mkdir()

    # Lib 1: built and tested (passed)
    p1 = campaign / "lib1"
    p1.mkdir()
    (p1 / "report.json").write_text(json.dumps({
        "library": "lib1", "arch": "x86_64", "build_result": "built",
        "tests_ran": True, "tests_passed": 10, "tests_total": 10, "crashes": [],
    }))

    # Lib 2: built, but tests_total == 0 (untested)
    p2 = campaign / "lib2"
    p2.mkdir()
    (p2 / "report.json").write_text(json.dumps({
        "library": "lib2", "arch": "x86_64", "build_result": "built",
        "tests_ran": False, "tests_passed": "", "tests_total": "", "crashes": [],
    }))

    # Lib 3: built, but 0 of 0 tests
    p3 = campaign / "lib3"
    p3.mkdir()
    (p3 / "report.json").write_text(json.dumps({
        "library": "lib3", "arch": "x86_64", "build_result": "built",
        "tests_ran": True, "tests_passed": 0, "tests_total": 0, "crashes": [],
    }))

    # Lib 4: failed build
    p4 = campaign / "lib4"
    p4.mkdir()
    (p4 / "report.json").write_text(json.dumps({
        "library": "lib4", "arch": "x86_64", "build_result": "failed",
        "tests_ran": False, "tests_passed": 0, "tests_total": 0, "blocked_on": [], "crashes": [],
    }))

    summary = summarize_campaign(campaign)
    assert summary["total_libraries"] == 4
    assert summary["built"] == 3
    assert summary["failed_build"] == 1
    assert summary["built_untested"] == 2
    assert summary["tested"] == 1
    assert summary["passed_all_tests"] == 1
    assert summary["built_rate_pct"] == 75.0
    # Test pass rate must be 1 / 1 (100%), not 3 / 3 or 3 / 4!
    assert summary["test_pass_rate_pct"] == 100.0

    rendered = render_campaign_summary(summary)
    assert "Built (untested): 2 / 3" in rendered
    assert "Passed all tests: 1 / 1 (100.0%)" in rendered


def test_passing_tests_core_dump_is_not_classified_as_crash_failure():
    """A passing test suite with a core file must remain overall_status: passed."""
    rep = {
        "library": "cleanlib",
        "arch": "x86_64",
        "build_result": "built",
        "tests_ran": True,
        "tests_passed": 20,
        "tests_total": 20,
        "crashes": [{"binary": "test_cleanup", "backtrace": "Program terminated with signal SIGSEGV..."}],
    }
    result = analyze_report(rep)
    assert result.overall_status == "passed"
    assert len(result.diagnostics) == 0


def test_gdb_signal_extraction_from_header():
    """Signal must be extracted from 'Program terminated with signal ...' header, not by substring searching."""
    bt_sigabrt = (
        "Program terminated with signal SIGABRT, Aborted.\n"
        "#0  0x00000015502c127d in SignalKill () from /lib/libc.so.5\n"
        "#1  0x00000015502af18c in abort () from /lib/libc.so.5\n"
        "#2  0x0000000000401122 in my_func () at test.c:42\n"
    )
    rec_abrt = classify_crash({"binary": "test1", "backtrace": bt_sigabrt}, "otherlib")
    assert rec_abrt.signature == "crash:sigabrt"

    bt_sigsegv = (
        "Program terminated with signal SIGSEGV, Segmentation fault.\n"
        "#0  0x00000015502c127d in deref_null () at foo.c:10\n"
        "#1  0x0000000000401122 in abort_handler () at bar.c:42\n"  # contains word 'abort' in frame
    )
    rec_segv = classify_crash({"binary": "test2", "backtrace": bt_sigsegv}, "otherlib")
    assert rec_segv.signature == "crash:sigsegv"


def test_existing_rules_recognized_as_existing():
    """Rules that already exist (printf-null, link-libsocket, endian-compat) must report existing_rule_could_not_apply."""
    # 1. printf-null in crash backtrace
    bt_printf = (
        "Program terminated with signal SIGSEGV, Segmentation fault.\n"
        "#0  0x000000155025a1e5 in strlen () from /lib/libc.so.5\n"
        "#1  0x0000001550201261 in _Putfld () from /lib/libc.so.5\n"
        "#2  0x00000015502023cb in _Printf () from /lib/libc.so.5\n"
        "#3  0x0000001550203f19 in vsnprintf () from /lib/libc.so.5\n"
        "#4  0x0000000000401234 in xmlWarnMsg () at SAX2.c:100\n"
    )
    rec_crash = classify_crash({"binary": "testapi", "backtrace": bt_printf}, "libxml2")
    assert rec_crash.signature == "crash:printf_null"
    assert rec_crash.category == FailureCategory.QNX_LIBC_DIFFERENCE
    assert rec_crash.actionability == Actionability.EXISTING_RULE_COULD_NOT_APPLY
    assert "printf-null" in rec_crash.summary

    # 2. Socket symbol (link-libsocket exists)
    diag_sock = errors.Diagnostic(kind="undefined_ref", message="undefined reference to `in6addr_any'", symbol="in6addr_any")
    rec_sock = classify_diagnostic(diag_sock)
    assert rec_sock.signature == "socket_symbol:in6addr_any"
    assert rec_sock.actionability == Actionability.EXISTING_RULE_COULD_NOT_APPLY
    assert "link-libsocket" in rec_sock.summary

    # 3. Endian header (endian-compat exists)
    diag_endian = errors.Diagnostic(kind="missing_header", message="endian.h: No such file or directory", header="endian.h")
    rec_endian = classify_diagnostic(diag_endian)
    assert rec_endian.signature == "missing_header:endian.h"
    assert rec_endian.actionability == Actionability.EXISTING_RULE_COULD_NOT_APPLY
    assert "endian-compat" in rec_endian.summary


def test_strtod_rounding_diagnosis_not_formatting():
    """Float test failures must be diagnosed as strtod parsing rounding, not formatting."""
    log_text = (
        "FAIL valid__real-exponent (exit 1)\n"
        "FAIL valid__real-subnormal-number (exit 1)\n"
    )
    records = classify_test_log(log_text, "jansson")
    assert len(records) == 1
    assert records[0].signature == "qnx_libc:strtod_rounding"
    assert records[0].category == FailureCategory.QNX_LIBC_DIFFERENCE
    assert records[0].actionability == Actionability.UPSTREAM_DEFECT_OR_TEST_CAVEAT
    assert "strtod" in records[0].summary
    assert "Formatting is not the problem" in records[0].hypothesis


def test_generic_assertion_not_classified_as_float():
    """Generic assertion text like 'does not evaluate to' without double/roundtrip context must not match float."""
    log_text = 'Test xpath failed: "foo" does not evaluate to "bar" in context c\n'
    records = classify_test_log(log_text, "randomlib")
    assert len(records) == 0


def test_missing_tool_word_boundary():
    """Missing tool pattern must use word boundaries and not match words containing 'ps'."""
    # Genuine ps failure
    log_ps = "/work/src/tests.sh[12]: ps: cannot execute - No such file or directory\n"
    recs_ps = classify_test_log(log_ps)
    assert len(recs_ps) == 1
    assert recs_ps[0].signature == "target:missing_tool:ps"

    # Word ending in ps (e.g. caps, eps, steps)
    log_caps = "/work/src/tests.sh[12]: caps: cannot execute - No such file or directory\n"
    recs_caps = classify_test_log(log_caps)
    assert len(recs_caps) == 0

    # killall failure
    log_killall = "/work/src/unit.sh: killall: cannot execute - No such file or directory\n"
    recs_kill = classify_test_log(log_killall)
    assert len(recs_kill) == 1
    assert recs_kill[0].signature == "target:missing_tool:killall"


def test_architecture_reporting_from_reports(tmp_path):
    """summarize_campaign must read arch from report.json, not from the directory path."""
    custom_dir = tmp_path / "custom-ports-dir"
    custom_dir.mkdir()
    (custom_dir / "liba").mkdir()
    (custom_dir / "liba" / "report.json").write_text(json.dumps({
        "library": "liba", "arch": "aarch64le", "build_result": "built",
        "tests_ran": True, "tests_passed": 5, "tests_total": 5, "crashes": [],
    }))

    summary = summarize_campaign(custom_dir)
    assert summary["arch"] == "aarch64le"


def test_cli_diagnose_errors_on_invalid_input(capsys):
    """CLI diagnose must return exit code 1 with clear stderr on missing or empty paths."""
    res_missing = cli_main(["diagnose", "definitely_nonexistent_path"])
    assert res_missing == 1
    err = capsys.readouterr().err
    assert "does not exist" in err

    res_empty = cli_main(["diagnose", "pyproject.toml"])  # not a json report
    assert res_empty == 1


def test_cli_diagnose_unified_single_report(tmp_path, capsys):
    """CLI diagnose must use single unified code path for file and directory report."""
    port_dir = tmp_path / "myport"
    port_dir.mkdir()
    report_path = port_dir / "report.json"
    report_path.write_text(json.dumps({
        "library": "myport", "arch": "x86_64", "build_result": "built",
        "tests_ran": True, "tests_passed": 10, "tests_total": 10, "crashes": [],
    }))

    # 1. Run pointing to directory
    rc1 = cli_main(["diagnose", str(port_dir)])
    assert rc1 == 0
    out1 = capsys.readouterr().out
    assert "Library: myport (x86_64)" in out1
    assert "Overall Status: passed" in out1

    # 2. Run pointing to file
    rc2 = cli_main(["diagnose", str(report_path)])
    assert rc2 == 0
    out2 = capsys.readouterr().out
    assert "Library: myport (x86_64)" in out2
    assert "Overall Status: passed" in out2


def test_agent_rendering_no_extra_blank_lines():
    """Agent render() must not output extra blank lines when fi_block is empty."""
    from unittest.mock import MagicMock
    from qnx_porter.agent import render

    job = MagicMock()
    job.toolchain_path.return_value = Path("qnx-toolchain.cmake")

    # Clean passing report
    r_passed = {
        "library": "foo", "version": "1.0", "url": "https://example.com/foo.git",
        "commit": "1234567890ab", "build_system": "cmake", "sdp": "QNX SDP 8.0",
        "arch": "x86_64", "target": "172.31.1.11", "build_result": "built", "rounds": 1,
        "tests_ran": True, "tests_passed": 5, "tests_total": 5, "patches_kept": 0,
        "patches_by_rule": 0, "patches_by_model": 0, "patches": [], "minutes": 1.0,
        "blocked_on": [], "crashes": [], "failure_intelligence": {"overall_status": "passed"},
    }
    rendered = render(r_passed, job)
    assert "\n## Still failing\n- nothing" in rendered
    assert "\n## Still failing\n- nothing\n\n" not in rendered
    assert "## Failure Intelligence" not in rendered


def test_deterministic_campaign_summary():
    """Campaign summary must be strictly deterministic across repeated runs."""
    ports_dir = Path("ports")
    if not ports_dir.is_dir():
        pytest.skip("ports/ directory not available")

    s1 = summarize_campaign(ports_dir)
    s2 = summarize_campaign(ports_dir)
    assert json.dumps(s1, sort_keys=True) == json.dumps(s2, sort_keys=True)


def test_real_ports_fixtures_match_verified_causes():
    """Verify classifications on real campaign artifacts from ports/."""
    ports_dir = Path("ports")
    if not ports_dir.is_dir():
        pytest.skip("ports/ directory not available")

    # 1. libxml2: crash:printf_null (existing rule could not apply)
    r_xml = json.loads((ports_dir / "libxml2" / "report.json").read_text(encoding="utf-8"))
    res_xml = analyze_report(r_xml, ports_dir / "libxml2" / "logs")
    assert res_xml.overall_status == "crashed"
    assert res_xml.diagnostics[0].signature == "crash:printf_null"
    assert res_xml.diagnostics[0].actionability == Actionability.EXISTING_RULE_COULD_NOT_APPLY

    # 2. pugixml: qnx_libc:strtod_rounding
    r_pugi = json.loads((ports_dir / "pugixml" / "report.json").read_text(encoding="utf-8"))
    res_pugi = analyze_report(r_pugi, ports_dir / "pugixml" / "logs")
    assert res_pugi.overall_status == "failed_tests"
    assert any(d.signature == "qnx_libc:strtod_rounding" for d in res_pugi.diagnostics)

    # 3. googletest: qnx_libc:fchdir_needs_o_directory
    r_gtest = json.loads((ports_dir / "googletest" / "report.json").read_text(encoding="utf-8"))
    res_gtest = analyze_report(r_gtest, ports_dir / "googletest" / "logs")
    assert res_gtest.overall_status == "crashed"
    assert any(d.signature == "qnx_libc:fchdir_needs_o_directory" for d in res_gtest.diagnostics)

    # 4. can-utils: unportable kernel header
    r_can = json.loads((ports_dir / "can-utils" / "report.json").read_text(encoding="utf-8"))
    res_can = analyze_report(r_can, ports_dir / "can-utils" / "logs")
    assert res_can.overall_status == "failed_build"
    assert any(d.actionability == Actionability.UNPORTABLE_KERNEL for d in res_can.diagnostics)

    # 5. libsrtp: random qsort comparator is upstream test caveat
    r_srtp = json.loads((ports_dir / "libsrtp" / "report.json").read_text(encoding="utf-8"))
    res_srtp = analyze_report(r_srtp, ports_dir / "libsrtp" / "logs")
    assert res_srtp.overall_status == "crashed"
    assert any(d.signature == "upstream_test:qsort_random_comparator" for d in res_srtp.diagnostics)
    assert any(d.actionability == Actionability.UPSTREAM_DEFECT_OR_TEST_CAVEAT for d in res_srtp.diagnostics)

    # 6. libuv: qnx_api_member mismatch
    r_uv = json.loads((ports_dir / "libuv" / "report.json").read_text(encoding="utf-8"))
    res_uv = analyze_report(r_uv, ports_dir / "libuv" / "logs")
    assert res_uv.overall_status == "failed_build"
    assert any(d.category == FailureCategory.QNX_API_MISMATCH for d in res_uv.diagnostics)

    # 7. libwebsockets: undeclared TCPCTL_KEEPCNT
    r_ws = json.loads((ports_dir / "libwebsockets" / "report.json").read_text(encoding="utf-8"))
    res_ws = analyze_report(r_ws, ports_dir / "libwebsockets" / "logs")
    assert res_ws.overall_status == "failed_build"
    assert any(d.signature == "undeclared:TCPCTL_KEEPCNT" for d in res_ws.diagnostics)

    # 8. flac: root permission
    r_flac = json.loads((ports_dir / "flac" / "report.json").read_text(encoding="utf-8"))
    res_flac = analyze_report(r_flac, ports_dir / "flac" / "logs")
    assert any(d.signature == "test:root_permission_mismatch" for d in res_flac.diagnostics)

    # 9. zstd: out of memory
    r_zstd = json.loads((ports_dir / "zstd" / "report.json").read_text(encoding="utf-8"))
    res_zstd = analyze_report(r_zstd, ports_dir / "zstd" / "logs")
    assert any(d.signature == "target:out_of_memory" for d in res_zstd.diagnostics)

    # 10. libmodbus: missing tool killall
    r_mb = json.loads((ports_dir / "libmodbus" / "report.json").read_text(encoding="utf-8"))
    res_mb = analyze_report(r_mb, ports_dir / "libmodbus" / "logs")
    assert any(d.signature == "target:missing_tool:killall" for d in res_mb.diagnostics)


def test_scoped_cpp_symbol_not_classified_as_socket():
    """Scoped C++ symbols (e.g. std::bind, Foo::socket) must not be classified as BSD socket library."""
    diag_cpp = errors.Diagnostic(kind="undefined_ref", message="undefined reference to `std::bind'", symbol="std::bind")
    rec = classify_diagnostic(diag_cpp)
    assert rec.category == FailureCategory.UNDEFINED_SYMBOL
    assert rec.actionability == Actionability.MODEL_PATCH_CANDIDATE
    assert rec.signature == "undefined_symbol:std::bind"


def test_qcc_option_and_werror_diagnostics():
    """Compiler flag issues parsed by errors.py must be cleanly classified."""
    diag_opt = errors.Diagnostic(kind="qcc_option", message="cc: unknown option: '-fstack-clash-protection'", symbol="-fstack-clash-protection")
    rec_opt = classify_diagnostic(diag_opt)
    assert rec_opt.signature == "toolchain_option:-fstack-clash-protection"
    assert rec_opt.category == FailureCategory.TOOLCHAIN_FLAG

    diag_werr = errors.Diagnostic(kind="werror", message="error: [-Werror=unused-function]", flag="unused-function")
    rec_werr = classify_diagnostic(diag_werr)
    assert rec_werr.signature == "compiler:werror"
    assert rec_werr.category == FailureCategory.TOOLCHAIN_FLAG


def test_cli_diagnose_json_output(capsys):
    """CLI diagnose --json must emit valid JSON."""
    ports_dir = Path("ports")
    if not ports_dir.is_dir():
        pytest.skip("ports/ directory not available")

    rc = cli_main(["diagnose", str(ports_dir / "libxml2"), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["library"] == "libxml2"
    assert data["overall_status"] == "crashed"
    assert data["primary_signature"] == "crash:printf_null"
