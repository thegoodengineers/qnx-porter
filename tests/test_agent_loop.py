"""End-to-end runs of the porting loop with the host compiler, so CI exercises it without QNX.

The fixture is a small CMake library written the way Linux code often is: it calls strcasecmp without
<strings.h> and builds with -Werror. The QNX runs (same loop, qcc, QEMU) are in results/ports.csv.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from qnx_porter import agent, llm

FIXTURE = Path(agent.__file__).parent / "brokenlib"
needs_tools = pytest.mark.skipif(
    os.name == "nt" or not (shutil.which("cmake") and shutil.which("cc")),
    reason="the agent runs on a Linux host (WSL on Windows) with cmake and a C compiler")


def upstream(tmp_path, extra=None):
    src = tmp_path / "upstream"
    shutil.copytree(FIXTURE, src)
    for name, text in (extra or {}).items():
        (src / name).write_text(text)
    subprocess.run(["git", "init", "-q", str(src)], check=True)
    for cmd in (["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "v1"],
                ["tag", "v1"]):
        subprocess.run(["git", "-C", str(src), *cmd], check=True)
    return src


@needs_tools
def test_rules_alone_port_the_fixture(tmp_path):
    r = agent.port(str(upstream(tmp_path)), "v1", tmp_path / "ports", arch=None, use_llm=False,
                   name="brokenlib", log=lambda *_: None)
    assert r["build_result"] == "built"
    assert [p["rule"] for p in r["patches"]] == ["add-include", "no-werror"]
    out = tmp_path / "ports" / "brokenlib"
    assert "+#include <strings.h>" in (out / "qnx.patch").read_text()
    assert json.loads((out / "report.json").read_text())["patches_by_rule"] == 2
    assert "Every change, with its reason" in (out / "REPORT.md").read_text()
    assert len(list((out / "patches").glob("*.patch"))) == 2


@needs_tools
def test_long_tail_goes_to_the_model_and_a_useless_patch_is_reverted(tmp_path, monkeypatch):
    lib = upstream(tmp_path, {"extra.c": "int g(void) { return PORTED_VALUE; }\n",
                              "CMakeLists.txt": FIXTURE.joinpath("CMakeLists.txt").read_text().replace(
                                  "textutil.c)", "textutil.c extra.c)")})
    replies = iter([
        {"reason": "adds an unrelated comment", "diff":
            "--- a/extra.c\n+++ b/extra.c\n@@ -1 +1,2 @@\n+/* nothing */\n int g(void) { return PORTED_VALUE; }\n"},
        {"reason": "define PORTED_VALUE for QNX", "diff":
            "--- a/extra.c\n+++ b/extra.c\n@@ -1 +1,2 @@\n+#define PORTED_VALUE 1\n int g(void) { return PORTED_VALUE; }\n"},
    ])
    asked = []
    monkeypatch.setattr(llm, "configured", lambda: True)
    monkeypatch.setattr(llm, "ask", lambda prompt: asked.append(prompt) or next(replies))
    r = agent.port(str(lib), "v1", tmp_path / "ports", arch=None, name="brokenlib", log=lambda *_: None)
    assert r["build_result"] == "built", r["blocked_on"]
    model = [p for p in r["patches"] if p["source"] == "model"]
    assert [(p["reason"], p["kept"]) for p in model] == [("adds an unrelated comment", False),
                                                        ("define PORTED_VALUE for QNX", True)]
    assert "PORTED_VALUE" in asked[0] and "extra.c" in asked[0]
    assert "#define PORTED_VALUE 1" in (tmp_path / "ports" / "brokenlib" / "qnx.patch").read_text()


@needs_tools
def test_without_a_model_it_stops_and_says_what_is_left(tmp_path, monkeypatch):
    lib = upstream(tmp_path, {"textutil.c": "#include <sys/not_on_qnx.h>\nint same_word(const char*a,"
                                            "const char*b){return a==b;}\n"})
    monkeypatch.setattr(llm, "configured", lambda: False)
    r = agent.port(str(lib), "v1", tmp_path / "ports", arch=None, name="brokenlib", log=lambda *_: None)
    assert r["build_result"] == "failed"
    assert "sys/not_on_qnx.h" in r["blocked_on"][0]["error"]


@needs_tools
def test_gcc10_common_symbols_are_fixed_with_real_linker_output(tmp_path):
    lib = upstream(tmp_path, {"counter.h": "int shared_counter;\n",
                              "textutil.h": "#include \"counter.h\"\nint same_word(const char *a, const char *b);\n",
                              "test_textutil.c": "#include \"textutil.h\"\nint main(void) { return shared_counter + !same_word(\"a\", \"A\"); }\n"})
    r = agent.port(str(lib), "v1", tmp_path / "ports", arch=None, use_llm=False, name="brokenlib",
                   log=lambda *_: None)
    assert r["build_result"] == "built", r["blocked_on"]
    assert "fcommon" in [p["rule"] for p in r["patches"]]


@needs_tools
def test_a_rule_that_needs_proof_is_reverted_when_the_rebuild_disagrees(tmp_path):
    # On the Linux host __QNX__ is not defined, so letting QNX join the FreeBSD branch cannot help here:
    # the agent must notice and revert its own rule, as it does for the model.
    guard = "#if defined(__FreeBSD__)\nint platform = 1;\n#else\n#error \"Unsupported platform\"\n#endif\n"
    lib = upstream(tmp_path, {"textutil.h": guard + "int same_word(const char *a, const char *b);\n"})
    r = agent.port(str(lib), "v1", tmp_path / "ports", arch=None, use_llm=False, name="brokenlib",
                   log=lambda *_: None)
    [p] = [p for p in r["patches"] if p["rule"] == "qnx-platform-guard"]
    assert p["kept"] is False and r["build_result"] == "failed"
    assert "#error" in r["blocked_on"][0]["error"]


@needs_tools
def test_a_proved_fix_that_lets_the_build_reach_the_linker_is_kept(tmp_path):
    # paho.mqtt.c on QNX: fixing its own `bool` typedef let compilation finish, and link errors (a different
    # file) appeared. That is progress, not a reason to revert.
    header = ("#include <stdbool.h>\ntypedef unsigned int bool;\n"
              "int same_word(const char *a, const char *b);\nint not_defined_anywhere(void);\n")
    test = '#include "textutil.h"\nint main(void) { return not_defined_anywhere(); }\n'
    lib = upstream(tmp_path, {"textutil.h": header, "test_textutil.c": test})
    r = agent.port(str(lib), "v1", tmp_path / "ports", arch=None, use_llm=False, name="brokenlib",
                   log=lambda *_: None)
    kept = [p for p in r["patches"] if p["rule"] == "bool-typedef"]
    assert kept and kept[0]["kept"] is True, (r["patches"], r["blocked_on"])
    assert "not_defined_anywhere" in r["blocked_on"][0]["error"]


@needs_tools
def test_a_local_checkout_without_a_tag(tmp_path):
    # What the GitHub Action does: port the repository that is checked out, at whatever is checked out.
    lib = upstream(tmp_path)
    r = agent.port(str(lib), "", tmp_path / "ports", arch=None, use_llm=False, name="here", log=lambda *_: None)
    assert r["build_result"] == "built" and len(r["version"]) == 12  # the commit, since there is no tag
