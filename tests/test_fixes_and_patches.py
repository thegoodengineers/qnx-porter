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


def test_link_libsocket_symbols_from_batch_logs(tmp_path):
    # Real ld output from ports-2024/libcoap/logs/round-01.log (data symbol in6addr_any)
    log_coap = ("/home/chirag/qnx-porter/ports/libcoap/work/src/src/coap_address.c:839:(.text+0x12df): "
                "undefined reference to `in6addr_any'\n")
    [f1] = fixes.plan(parse(log_coap), tmp_path, Flags(), set())
    assert f1.rule == "link-libsocket" and f1.libs == ["-lsocket"]

    # Real ld output from ports-2024/libsrtp/logs/round-01.log (renamed symbol __inet_addr)
    log_srtp = ("/home/chirag/qnx-porter/ports/libsrtp/work/src/test/rtpw.c:309:(.text.startup+0x2cb): "
                "undefined reference to `__inet_addr'\n")
    [f2] = fixes.plan(parse(log_srtp), tmp_path, Flags(), set())
    assert f2.rule == "link-libsocket" and f2.libs == ["-lsocket"]

    # Real ld output from ports-2024/libevent/logs/round-02.log (renamed symbol __inet_ntoa)
    log_event = ("/home/chirag/qnx800/host/linux/x86_64/usr/bin/x86_64-pc-nto-qnx8.0.0-ld: "
                 "lib/libevent_extra-2.1.so.7.0.1: undefined reference to `__inet_ntoa'\n")
    [f3] = fixes.plan(parse(log_event), tmp_path, Flags(), set())
    assert f3.rule == "link-libsocket" and f3.libs == ["-lsocket"]


def test_werror_and_no_repeats(tmp_path):
    d = Diagnostic("werror", "x [-Werror=cast-align]", flag="cast-align")
    [f] = fixes.plan([d, d], tmp_path, Flags(), set())
    assert f.late == ["-Wno-error=cast-align"]
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


def test_an_edit_of_a_crlf_file_changes_only_the_edited_lines(tmp_path):
    (tmp_path / "t.cpp").write_bytes(b"int a;\r\nint b;\r\n")
    repo(tmp_path, {})
    text = (tmp_path / "t.cpp").read_text()  # universal newlines, as the rules read
    patches.write_source(tmp_path / "t.cpp", text.replace("int b;", "int b, c;"))
    assert (tmp_path / "t.cpp").read_bytes() == b"int a;\r\nint b, c;\r\n"
    diff = patches.git(tmp_path, "diff")
    assert "-int a;" not in diff and "+int b, c;" in diff


def test_can_utils_endian_missing_header_fires_endian_compat_rule(tmp_path):
    # Real error from ports-2024/can-utils/report.json
    log = ("/home/chirag/qnx-porter/ports/can-utils/work/src/mcp251xfd/mcp251xfd-dev-coredump.c:9:10: "
           "fatal error: endian.h: No such file or directory\n")
    src = "#include <endian.h>\nuint32_t to_be(uint32_t val) { return htobe32(val); }\n"
    core_dump_path = tmp_path / "mcp251xfd"
    core_dump_path.mkdir(parents=True)
    (core_dump_path / "mcp251xfd-dev-coredump.c").write_text(src)
    diags = parse(log)
    planned = fixes.plan(diags, tmp_path, Flags(), set())
    assert len(planned) == 1
    f = planned[0]
    assert f.rule == "endian-compat"
    assert f.cflags == ["-D_QNX_PORTER_ENDIAN"]
    assert "endian.h" in f.compat
    assert "htobe32" in f.compat["endian.h"]
    assert "be64toh" in f.compat["endian.h"]


def test_agent_apply_adds_include_directory_for_compat_headers(tmp_path):
    from unittest.mock import MagicMock
    from qnx_porter import agent

    diag = Diagnostic("missing_header", "fatal error: endian.h: No such file or directory", header="endian.h")
    fix = fixes.Fix("endian-compat", "test reason", diag, cflags=["-D_QNX_PORTER_ENDIAN"],
                    compat={"endian.h": fixes.ENDIAN_COMPAT_H})
    mock_job = MagicMock()
    mock_job.flags = Flags()
    mock_job.toolchain_text.return_value = "BEFORE"
    mock_job.toolchain_path.return_value = tmp_path / "toolchain.cmake"

    src = tmp_path / "src"
    src.mkdir()
    out = tmp_path / "out"
    out.mkdir()
    (out / "patches").mkdir()
    work = tmp_path / "work"
    work.mkdir()

    patch = agent._apply(fix, 1, src, out, mock_job, work)
    compat_dir = work / "qnx-compat"
    assert (compat_dir / "endian.h").is_file()
    assert (compat_dir / "endian.h").read_text(encoding="utf-8") == fixes.ENDIAN_COMPAT_H
    assert f"-I{compat_dir}" in mock_job.flags.cflags
    assert ["-include", str(compat_dir / "endian.h")][0] in mock_job.flags.cflags
    assert "-D_QNX_PORTER_ENDIAN" in mock_job.flags.cflags
    assert patch.rule == "endian-compat"


def test_byte_order_macro_at_link_time_gets_its_header(tmp_path):
    # mosquitto 2.1.2 db_dump.c: ntohl without <arpa/inet.h> is only a warning, then a link error with file:line
    from qnx_porter import errors
    (tmp_path / "a.c").write_text(C_FILE)
    [d] = errors.parse(f"{tmp_path}/a.c:3:(.text.startup+0x504): undefined reference to `ntohl'")
    [f] = fixes.plan([d], tmp_path, Flags(), set())
    assert f.rule == "add-include" and "#include <arpa/inet.h>" in f.edits["a.c"] and not f.libs
    [d] = errors.parse(f"{tmp_path}/a.c:3:(.text+0x1): undefined reference to `socket'")
    assert [x.rule for x in fixes.plan([d], tmp_path, Flags(), set())] == ["link-libsocket"]


def test_include_is_not_added_inside_a_conditional_block(tmp_path):
    (tmp_path / "a.c").write_text("#include <stdio.h>\n#include <string.h>\n#ifdef __ANDROID__\n"
                                  "#include <sys/endian.h>\n#endif\n\nint f(void) { return ntohl(1); }\n")
    text = fixes.add_include(tmp_path, "a.c", "arpa/inet.h", 7)
    assert text.splitlines()[2] == "#include <arpa/inet.h>  /* qnx-porter: needed on QNX */"
    (tmp_path / "g.h").write_text("#ifndef G_H\n#define G_H\n#include <stdio.h>\nint g(void);\n#endif\n")
    assert fixes.add_include(tmp_path, "g.h", "x.h", 4).splitlines()[3].startswith("#include <x.h>")


def test_dso_missing_form_of_undefined_reference_links_libsocket(tmp_path):
    from qnx_porter import errors
    log = ("ld: CMakeFiles/mosquitto.dir/bridge.c.o: undefined reference to symbol 'getsockopt@@libsocket.so.4'\n"
           "ld: /q/x86_64/lib/libsocket.so.4: error adding symbols: DSO missing from command line\n")
    [d] = [x for x in errors.parse(log) if x.kind == "undefined_ref"]
    assert d.symbol == "getsockopt"
    assert [f.rule for f in fixes.plan([d], tmp_path, Flags(), set())] == ["link-libsocket"]


def test_bsd_list_macro_gets_sys_queue_h(tmp_path):
    # open62541 v1.5.10 eventloop_posix.h: its own queue.h is skipped on __QNX__
    from qnx_porter import errors
    (tmp_path / "e.h").write_text("#include <errno.h>\n\nstruct s {\n    LIST_ENTRY(s) next;\n};\n")
    [d] = errors.parse(f"{tmp_path}/e.h:4:5: error: expected specifier-qualifier-list before 'LIST_ENTRY'")
    [f] = fixes.plan([d], tmp_path, Flags(), set())
    assert f.rule == "add-include" and "#include <sys/queue.h>" in f.edits["e.h"]


def test_deep_recursion_backtrace_names_the_function():
    # cJSON v1.7.19 misc_tests on x86_64 QNX: SIGSEGV in malloc at recursion depth 6540
    from qnx_porter import crash
    bt = ("#0  0x18a08fb92f in mspace_malloc (msp=0x1, bytes=64) at /b/malloc.c:1673\n"
          "#1  0x18a08fd150 in malloc (bytes=64) at /b/ptmalloc3.c:139\n"
          "#2  0x5e8d04d5de in cJSON_New_Item (hooks=0x5) at /s/cJSON.c:243\n"
          + "".join(f"#{i}  0x5e8d04d6c7 in cJSON_Duplicate_rec (item=<optimized out>, depth={6540 - i}, "
                    "recurse=1) at /s/cJSON.c:2824\n" for i in range(3, 12)))
    assert crash.deep_recursion(bt) == "cJSON_Duplicate_rec"
    assert crash.deep_recursion("#0  0x1 in strlen (s=0x0) at a.c:1\n#1  0x2 in printf (f=0x1) at b.c:2\n") is None
