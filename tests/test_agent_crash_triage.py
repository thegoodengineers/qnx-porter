"""Test multi-crash triage and progressive crash repair in agent.py."""
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from qnx_porter import agent, build, qnx, target
from qnx_porter.target import Target

TEST_SRC = """#include <stdio.h>

void test_one(const char *name)
{
    printf("Item: %s\\n", name);
}

void test_two(const char *err)
{
    char buf[128];
    snprintf(buf, sizeof(buf), "Error: %s\\n", err);
}

int main(void)
{
    test_one(NULL);
    test_two(NULL);
    return 0;
}
"""

CMAKELISTS = """cmake_minimum_required(VERSION 3.16)
project(testcrash C)
add_executable(testcrash tests/suite.c)
enable_testing()
add_test(NAME testcrash COMMAND testcrash)
"""

BT1_TPL = """#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x00000018fee3408d in _Putfld () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#2  0x00000018fee33378 in _Printf () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xprintf.c:603
#3  0x00000018fee2e37d in printf () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/printf.c:37
#4  0x0000004959988eb1 in test_one (name=0x0) at {src}/tests/suite.c:5
"""

BT2_TPL = """#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x00000018fee3408d in _Putfld () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#2  0x00000018fee33378 in _Printf () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xprintf.c:603
#3  0x00000018fee2e37d in snprintf () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/snprintf.c:71
#4  0x0000004959988eb1 in test_two (err=0x0) at {src}/tests/suite.c:11
"""

BT2_REBUILT_TPL = """#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x00000018fee3408d in _Putfld () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#2  0x00000018fee33378 in _Printf () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xprintf.c:603
#3  0x00000018fee2e37d in snprintf () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/snprintf.c:71
#4  0x0000004959988eb1 in test_two (err=0x0) at {src}/tests/suite.c:14
"""


def setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "upstream_repo"
    repo.mkdir(parents=True)
    (repo / "CMakeLists.txt").write_text(CMAKELISTS)
    (repo / "tests").mkdir()
    (repo / "tests" / "suite.c").write_text(TEST_SRC)

    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "TestUser"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "Initial commit"], check=True)
    subprocess.run(["git", "-C", str(repo), "tag", "v1.0.0"], check=True)
    return repo


def make_mock_target() -> Target:
    mock_tgt = MagicMock(spec=Target)
    mock_tgt.host = "127.0.0.1"
    mock_tgt.port = 22
    mock_tgt.user = "root"
    mock_tgt.root = "/data"
    mock_tgt.uname.return_value = "QNX 8.0.0 x86_64"
    return mock_tgt


def test_agent_multi_crash_same_file_progressive_success(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", lambda: {"QNX_HOST": "/mock/host", "QNX_TARGET": "/mock/target"})
    repo = setup_repo(tmp_path)
    mock_tgt = make_mock_target()

    # Mock build.run: initial build succeeds, rebuilds succeed
    monkeypatch.setattr(build, "run", lambda steps, work, env, log: (True, "build success"))

    call_count = 0

    def mock_run_tests(job, tgt, src, bdir, work, env, logs):
        nonlocal call_count
        call_count += 1
        src_path = str(src).replace("\\", "/")
        if call_count == 1:
            # First run: both calls crash
            crashes = [
                {"binary": "testcrash", "backtrace": BT1_TPL.format(src=src_path)},
                {"binary": "testcrash", "backtrace": BT2_TPL.format(src=src_path)},
            ]
            return 0, 2, crashes, []
        # Second run (after crash triage): tests pass!
        return 2, 2, [], []

    monkeypatch.setattr(agent, "_run_tests", mock_run_tests)

    rep = agent.port(str(repo), "v1.0.0", tmp_path / "ports", target=mock_tgt, arch="x86_64",
                     use_llm=False, name="testcrash", log=lambda *_: None)

    assert rep["build_result"] == "built"
    assert rep["tests_passed"] == 2
    assert rep["tests_total"] == 2
    assert rep["patches_kept"] == 1
    assert rep["patches"][0]["rule"] == "printf-null"
    # Verify that the kept patch fixed both calls in tests/suite.c
    patched_file = tmp_path / "ports" / "testcrash" / "work" / "src" / "tests" / "suite.c"
    patched_text = patched_file.read_text()
    assert "qnx_porter_str(name)" in patched_text
    assert "qnx_porter_str(err)" in patched_text
    assert patched_text.count("static const char *qnx_porter_str") == 1


def test_agent_progressive_crash_multi_round(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", lambda: {"QNX_HOST": "/mock/host", "QNX_TARGET": "/mock/target"})
    repo = setup_repo(tmp_path)
    mock_tgt = make_mock_target()

    monkeypatch.setattr(build, "run", lambda steps, work, env, log: (True, "build success"))

    call_count = 0

    def mock_run_tests(job, tgt, src, bdir, work, env, logs):
        nonlocal call_count
        call_count += 1
        src_path = str(src).replace("\\", "/")
        if call_count == 1:
            # Round 1: crash 1 observed
            return 0, 2, [{"binary": "testcrash", "backtrace": BT1_TPL.format(src=src_path)}], []
        if call_count == 2:
            # Round 2: crash 1 fixed, crash 2 uncovered in rebuilt binary!
            return 1, 2, [{"binary": "testcrash", "backtrace": BT2_REBUILT_TPL.format(src=src_path)}], []
        # Round 3: all tests pass!
        return 2, 2, [], []

    monkeypatch.setattr(agent, "_run_tests", mock_run_tests)

    rep = agent.port(str(repo), "v1.0.0", tmp_path / "ports", target=mock_tgt, arch="x86_64",
                     use_llm=False, name="testcrash", log=lambda *_: None)

    assert rep["build_result"] == "built"
    assert rep["tests_passed"] == 2
    assert rep["tests_total"] == 2
    assert rep["patches_kept"] == 2
    assert [p["rule"] for p in rep["patches"]] == ["printf-null", "printf-null"]


def test_agent_crash_fix_reverted_when_tests_do_not_improve(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", lambda: {"QNX_HOST": "/mock/host", "QNX_TARGET": "/mock/target"})
    repo = setup_repo(tmp_path)
    mock_tgt = make_mock_target()

    monkeypatch.setattr(build, "run", lambda steps, work, env, log: (True, "build success"))

    call_count = 0

    def mock_run_tests(job, tgt, src, bdir, work, env, logs):
        nonlocal call_count
        call_count += 1
        src_path = str(src).replace("\\", "/")
        # Tests never pass; same crash repeats
        return 0, 2, [{"binary": "testcrash", "backtrace": BT1_TPL.format(src=src_path)}], []

    monkeypatch.setattr(agent, "_run_tests", mock_run_tests)

    rep = agent.port(str(repo), "v1.0.0", tmp_path / "ports", target=mock_tgt, arch="x86_64",
                     use_llm=False, name="testcrash", log=lambda *_: None)

    assert rep["build_result"] == "built"
    assert rep["tests_passed"] == 0
    assert rep["patches_kept"] == 0
    # Source file must be clean / unpatched
    final_file = tmp_path / "ports" / "testcrash" / "work" / "src" / "tests" / "suite.c"
    assert "qnx_porter_str" not in final_file.read_text()


def test_agent_rebuild_failure_reverts_crash_fix(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", lambda: {"QNX_HOST": "/mock/host", "QNX_TARGET": "/mock/target"})
    repo = setup_repo(tmp_path)
    mock_tgt = make_mock_target()

    build_calls = 0

    def mock_build_run(steps, work, env, log):
        nonlocal build_calls
        build_calls += 1
        if build_calls == 1:
            return True, "initial build ok"
        # Rebuild fails!
        return False, "compiler error after crash fix"

    monkeypatch.setattr(build, "run", mock_build_run)

    def mock_run_tests(job, tgt, src, bdir, work, env, logs):
        src_path = str(src).replace("\\", "/")
        return 0, 2, [{"binary": "testcrash", "backtrace": BT1_TPL.format(src=src_path)}], []

    monkeypatch.setattr(agent, "_run_tests", mock_run_tests)

    rep = agent.port(str(repo), "v1.0.0", tmp_path / "ports", target=mock_tgt, arch="x86_64",
                     use_llm=False, name="testcrash", log=lambda *_: None)

    assert rep["patches_kept"] == 0
    final_file = tmp_path / "ports" / "testcrash" / "work" / "src" / "tests" / "suite.c"
    assert "qnx_porter_str" not in final_file.read_text()


def test_agent_crash_round2_reverted_round1_kept(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(qnx, "sdp_env", lambda: {"QNX_HOST": "/mock/host", "QNX_TARGET": "/mock/target"})
    repo = setup_repo(tmp_path)
    mock_tgt = make_mock_target()

    monkeypatch.setattr(build, "run", lambda steps, work, env, log: (True, "build success"))

    call_count = 0

    def mock_run_tests(job, tgt, src, bdir, work, env, logs):
        nonlocal call_count
        call_count += 1
        src_path = str(src).replace("\\", "/")
        if call_count == 1:
            (logs / "tests.log").write_text("Round 1 tests failed: 0/2")
            (logs / "crashes.log").write_text("crash 1 log")
            return 0, 2, [{"binary": "testcrash", "backtrace": BT1_TPL.format(src=src_path)}], []
        if call_count == 2:
            # Round 1 succeeded! Tests improved from 0 to 1.
            (logs / "tests.log").write_text("Round 1 re-test passed: 1/2")
            (logs / "crashes.log").write_text("crash 2 log")
            return 1, 2, [{"binary": "testcrash", "backtrace": BT2_REBUILT_TPL.format(src=src_path)}], []
        # Round 2: crash 2 fix was applied, but tests did not improve (still 1/2)
        (logs / "tests.log").write_text("Round 2 re-test did not improve: 1/2")
        (logs / "crashes.log").write_text("crash 2 still present log")
        return 1, 2, [{"binary": "testcrash", "backtrace": BT2_REBUILT_TPL.format(src=src_path)}], []

    monkeypatch.setattr(agent, "_run_tests", mock_run_tests)

    rep = agent.port(str(repo), "v1.0.0", tmp_path / "ports", target=mock_tgt, arch="x86_64",
                     use_llm=False, name="testcrash", log=lambda *_: None)

    assert rep["build_result"] == "built"
    assert rep["tests_passed"] == 1
    assert rep["tests_total"] == 2
    assert rep["patches_kept"] == 1
    assert len(rep["patches"]) == 2
    assert rep["patches"][0]["kept"] is True
    assert rep["patches"][1]["kept"] is False

    # Round 1 patch stays, Round 2 patch reverted
    final_file = tmp_path / "ports" / "testcrash" / "work" / "src" / "tests" / "suite.c"
    src_text = final_file.read_text()
    assert "qnx_porter_str(name)" in src_text
    assert "qnx_porter_str(err)" not in src_text

    # Disk logs restored to round 1's state
    tests_log = (tmp_path / "ports" / "testcrash" / "logs" / "tests.log").read_text()
    crashes_log = (tmp_path / "ports" / "testcrash" / "logs" / "crashes.log").read_text()
    assert tests_log == "Round 1 re-test passed: 1/2"
    assert crashes_log == "crash 2 log"
