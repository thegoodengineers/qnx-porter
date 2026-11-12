import subprocess

from qnx_porter import fixes, llm, patches
from qnx_porter.errors import Diagnostic, parse
from qnx_porter.qnx import Flags
from qnx_porter.target import Target, parse_results, remote_command

C_FILE = "/* header */\n#include <stdio.h>\n#include \"x.h\"\n\nint f(void) { return strcasecmp(\"a\", \"A\"); }\n"


def repo(tmp_path, files):
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    patches.git(tmp_path, "add", "-A")
    patches.git(tmp_path, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "base")
    return tmp_path


def implicit(file="a.c", sym="strcasecmp", header=""):
    return Diagnostic("implicit_decl", f"implicit declaration of function '{sym}'", file=file, line=5,
                      symbol=sym, header=header)


def test_add_include_goes_after_the_last_include_above_the_error(tmp_path):
    (tmp_path / "a.c").write_text(C_FILE)
    [f] = fixes.plan([implicit()], tmp_path, Flags(), set())
    assert f.rule == "add-include"
    lines = f.edits["a.c"].splitlines()
    assert lines[3].startswith("#include <strings.h>") and lines[2] == '#include "x.h"'


def test_header_already_included_means_a_feature_macro_hid_it(tmp_path):
    (tmp_path / "a.c").write_text("#include <strings.h>\nint f(void){return strcasecmp(\"a\",\"b\");}\n")
    [f] = fixes.plan([implicit()], tmp_path, Flags(), set())
    assert f.rule == "qnx-source" and f.cflags == ["-D_QNX_SOURCE"]


def test_compiler_hint_beats_the_table(tmp_path):
    (tmp_path / "a.c").write_text(C_FILE)
    [f] = fixes.plan([implicit(sym="my_func", header="mylib.h")], tmp_path, Flags(), set())
    assert "#include <mylib.h>" in f.edits["a.c"]


def test_unknown_symbol_and_system_header_errors_get_no_rule(tmp_path):
    (tmp_path / "a.c").write_text(C_FILE)
    assert fixes.plan([implicit(sym="epoll_create1")], tmp_path, Flags(), set()) == []
    assert fixes.plan([implicit(file="/usr/include/x.h")], tmp_path, Flags(), set()) == []


def test_link_rules(tmp_path):
    socket = Diagnostic("undefined_ref", "undefined reference to `socket'", symbol="socket")
    rt = Diagnostic("missing_lib", "cannot find -lrt", symbol="rt")
    other = Diagnostic("undefined_ref", "undefined reference to `foo'", symbol="foo")
    planned = fixes.plan([socket, rt, other], tmp_path, Flags(), set())
    assert [(f.rule, f.libs, f.stubs) for f in planned] == [("link-libsocket", ["-lsocket"], []),
                                                            ("stub-lib", [], ["rt"])]


def test_werror_and_no_repeats(tmp_path):
    d = Diagnostic("werror", "x [-Werror=cast-align]", flag="cast-align")
    [f] = fixes.plan([d, d], tmp_path, Flags(), set())
    assert f.cflags == ["-Wno-error=cast-align"]
    assert fixes.plan([d], tmp_path, Flags(), {f.key()}) == []


def test_linux_only_headers_get_a_hint_not_a_guess():
    assert "poll" in fixes.hint(Diagnostic("missing_header", "", header="sys/epoll.h"))
    assert "kernel" in fixes.hint(Diagnostic("missing_header", "", header="linux/if.h"))


def test_source_patch_is_written_with_its_reason_and_committed(tmp_path):
    (tmp_path / "src").mkdir()
    src = repo(tmp_path / "src", {"a.c": C_FILE})
    out = tmp_path / "out"
    (out / "patches").mkdir(parents=True)
    [f] = fixes.plan([implicit()], src, Flags(), set())
    (src / "a.c").write_text(f.edits["a.c"])
    p = patches.commit_source(src, out, 1, f.rule, "rule", f.reason, "a.c:5: error", ["a.c"])
    text = (out / p.path).read_text()
    assert text.startswith("Subject: [qnx-porter 0001] add-include")
    assert "Reason: `strcasecmp` is declared in <strings.h>" in text and "+#include <strings.h>" in text
    assert patches.git(src, "status", "--porcelain") == ""


def test_model_diff_must_apply_cleanly(tmp_path):
    src = repo(tmp_path, {"a.c": "int x;\n"})
    good = "--- a/a.c\n+++ b/a.c\n@@ -1 +1,2 @@\n int x;\n+int y;\n"
    bad = "--- a/a.c\n+++ b/a.c\n@@ -1 +1,2 @@\n int nope;\n+int y;\n"
    assert patches.apply_diff(src, bad)[0] is False
    assert patches.apply_diff(src, good) == (True, "")
    assert (src / "a.c").read_text() == "int x;\nint y;\n"
    assert patches.changed_files(good) == ["a.c"]


def test_model_reply_parsing():
    assert llm.parse_reply('```json\n{"reason": "r", "diff": "d"}\n```') == {"reason": "r", "diff": "d"}
    assert llm.parse_reply("sorry")["diff"] == ""


def test_model_needs_key_model_and_endpoint(monkeypatch):
    monkeypatch.delenv("QNX_PORTER_API_KEY", raising=False)
    monkeypatch.setenv("QNX_PORTER_MODEL", "m")
    monkeypatch.setenv("QNX_PORTER_BASE_URL", "https://example.invalid/v1")
    assert not llm.configured()
    monkeypatch.setenv("QNX_PORTER_API_KEY", "k")
    assert llm.configured()
    monkeypatch.delenv("QNX_PORTER_BASE_URL")
    assert not llm.configured()  # no built-in default endpoint


def test_temperature_is_sent_only_when_set():
    env = {"QNX_PORTER_MODEL": "m"}
    body = llm.request_body("p", env)
    assert "temperature" not in body and "max_tokens" not in body  # some models reject sampling parameters
    assert body["model"] == "m" and body["messages"][1]["content"] == "p"
    body = llm.request_body("p", {**env, "QNX_PORTER_TEMPERATURE": "0", "QNX_PORTER_MAX_TOKENS": "4096"})
    assert body["temperature"] == 0.0 and body["max_tokens"] == 4096


def test_test_summaries_from_each_runner():
    assert parse_results("cmake", "90% tests passed, 1 tests failed out of 10\n") == (9, 10)
    assert parse_results("cmake", "100% tests passed, 0 tests failed out of 3\n  2 - x ***Skipped 0.0 sec\n") \
        == (2, 2)
    meson = "Ok:                 7\nExpected Fail:      0\nFail:               1\nSkipped:            2\nTimeout:            0\n"
    assert parse_results("meson", meson) == (7, 8)
    auto = "# TOTAL: 5\n# PASS:  4\n# SKIP:  1\n# FAIL:  0\n# TOTAL: 2\n# PASS:  1\n# FAIL:  1\n"
    assert parse_results("autotools", auto) == (5, 6)


def test_remote_command_moves_host_paths_under_the_target_root():
    t = Target.parse("root@10.0.0.2:2222")
    assert t.port == 2222 and t.root == "/data/qnx-porter"
    cmd = remote_command(t, "/home/me/w", "/home/me/w/build", ["/home/me/w/build/t1", "--data", "/home/me/w/src/d"])
    assert cmd == ("cd /data/qnx-porter/home/me/w/build && exec /data/qnx-porter/home/me/w/build/t1 --data "
                   "/data/qnx-porter/home/me/w/src/d")


def test_parse_then_plan_on_a_real_gcc_log(tmp_path):
    (tmp_path / "a.c").write_text(C_FILE)
    log = ("a.c:5:22: error: implicit declaration of function 'strcasecmp' "
           "[-Werror=implicit-function-declaration]\n")
    [f] = fixes.plan(parse(log), tmp_path, Flags(), set())
    assert f.rule == "add-include"
