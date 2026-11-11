"""The Linux-ism corpus (docs/LINUX_ISMS.md) as tests: real code shapes, real GCC 12 / GNU ld messages.

Each case: a source file as Linux-first projects write it, the error QNX's toolchain prints for it, and
the rule that must fire with what it must produce. Where the rule rewrites code, the result is also
compiled with the host compiler and -D__QNX__ (Linux CI) to prove it is still valid C.
"""
import os
import shutil
import subprocess

import pytest

from qnx_porter import fixes
from qnx_porter.errors import parse
from qnx_porter.qnx import Flags

CC = shutil.which("cc") if os.name != "nt" else None


def run(tmp_path, files: dict, log: str, flags=None):
    for name, text in files.items():
        (tmp_path / name).write_text(text)
    return fixes.plan(parse(log), tmp_path, flags or Flags(), set())


def compiles(tmp_path, text: str, *defs: str) -> bool:
    (tmp_path / "check.c").write_text(text)
    r = subprocess.run([CC, "-fsyntax-only", "-D_GNU_SOURCE", *defs, str(tmp_path / "check.c")],
                       capture_output=True, text=True)
    return r.returncode == 0 or print(r.stderr)


EPOLL_UNUSED = "#include <stdio.h>\n#include <sys/epoll.h>\nint f(void) { return 1; }\n"
EPOLL_USED = "#include <sys/epoll.h>\nint f(void) { return epoll_create1(0); }\n"


def test_unused_linux_only_header_is_guarded(tmp_path):
    [f] = run(tmp_path, {"a.c": EPOLL_UNUSED}, "a.c:2:10: fatal error: sys/epoll.h: No such file or directory\n")
    assert f.rule == "guard-linux-header" and not f.verify
    assert "#ifndef __QNX__" in f.edits["a.c"] and "#include <sys/epoll.h>\n#endif" in f.edits["a.c"]
    if CC:
        assert compiles(tmp_path, f.edits["a.c"], "-D__QNX__") and compiles(tmp_path, f.edits["a.c"])


def test_used_epoll_is_left_for_the_model_with_a_qnx_hint(tmp_path):
    log = "a.c:1:10: fatal error: sys/epoll.h: No such file or directory\n"
    assert run(tmp_path, {"a.c": EPOLL_USED}, log) == []
    assert "poll()" in fixes.hint(parse(log)[0]) and "ionotify" in fixes.hint(parse(log)[0])


@pytest.mark.parametrize("header", ["sys/sendfile.h", "sys/sysinfo.h", "sys/eventfd.h", "sys/timerfd.h",
                                    "sys/signalfd.h", "sys/random.h", "execinfo.h", "features.h", "mcheck.h"])
def test_every_listed_linux_header_is_guarded_when_unused(tmp_path, header):
    [f] = run(tmp_path, {"a.c": f"#include <{header}>\nint x;\n"},
              f"a.c:1:10: fatal error: {header}: No such file or directory\n")
    assert f.rule == "guard-linux-header"


def test_sendfile_use_gets_a_hint_not_a_rewrite(tmp_path):
    log = "s.c:1:10: fatal error: sys/sendfile.h: No such file or directory\n"
    src = "#include <sys/sendfile.h>\nlong f(int o, int i) { return sendfile(o, i, 0, 10); }\n"
    assert run(tmp_path, {"s.c": src}, log) == []
    assert "read()/write()" in fixes.hint(parse(log)[0])


def test_linux_kernel_headers_get_a_hint(tmp_path):
    d = parse("n.c:3:10: fatal error: linux/if_packet.h: No such file or directory\n")[0]
    assert run(tmp_path, {"n.c": "#include <stdio.h>\n\n#include <linux/if_packet.h>\n"}, d.raw + "\n") == []
    assert "Linux kernel header" in fixes.hint(d)


def test_byteswap_maps_to_gcc_builtins(tmp_path):
    src = "#include <stdint.h>\n#include <byteswap.h>\nuint32_t f(uint32_t x) { return bswap_32(x); }\n"
    [f] = run(tmp_path, {"b.c": src}, "b.c:2:10: fatal error: byteswap.h: No such file or directory\n")
    assert f.rule == "byteswap-builtins"
    assert "#define bswap_32(x) __builtin_bswap32(x)" in f.edits["b.c"]
    if CC:
        assert compiles(tmp_path, f.edits["b.c"], "-D__QNX__")


def test_prctl_set_name_becomes_pthread_setname_np(tmp_path):
    src = ('#include <sys/prctl.h>\nvoid name_me(const char *n) {\n'
           '    prctl(PR_SET_NAME, (unsigned long)n, 0, 0, 0);\n}\n')
    [f] = run(tmp_path, {"t.c": src}, "t.c:1:10: fatal error: sys/prctl.h: No such file or directory\n")
    assert f.rule == "prctl-set-name" and f.verify
    assert "pthread_setname_np(pthread_self(), n);" in f.edits["t.c"]
    assert "#else\n#include <pthread.h>\n#endif" in f.edits["t.c"]
    if CC:
        assert compiles(tmp_path, f.edits["t.c"], "-D__QNX__")


def test_prctl_with_other_options_is_not_rewritten(tmp_path):
    src = "#include <sys/prctl.h>\nvoid f(void) { prctl(PR_SET_NAME, \"x\"); prctl(PR_SET_DUMPABLE, 0); }\n"
    assert run(tmp_path, {"t.c": src}, "t.c:1:10: fatal error: sys/prctl.h: No such file or directory\n") == []


def test_freebsd_pthread_set_name_np_is_renamed(tmp_path):
    src = "#include <pthread.h>\nvoid f(void) { pthread_set_name_np(pthread_self(), \"io\"); }\n"
    log = "t.c:2:16: error: implicit declaration of function 'pthread_set_name_np' [-Wimplicit-function-declaration]\n"
    [f] = run(tmp_path, {"t.c": src}, log)
    assert f.rule == "pthread-setname" and "pthread_setname_np(pthread_self()" in f.edits["t.c"]


def test_macos_one_argument_setname_gets_the_thread(tmp_path):
    src = "#include <pthread.h>\nvoid f(void) { pthread_setname_np(\"w\"); }\n"
    log = "b.c:2:16: error: too few arguments to function 'pthread_setname_np'\n"  # real GCC wording
    [f] = run(tmp_path, {"b.c": src}, log)
    assert f.rule == "pthread-setname-args"
    assert 'pthread_setname_np(pthread_self(), "w")' in f.edits["b.c"]
    if CC:
        assert compiles(tmp_path, f.edits["b.c"])


PLATFORM = ('#include <stdio.h>\n#if defined(__linux__)\n#define POLLER "epoll"\n'
            '#elif defined(__FreeBSD__) || defined(__APPLE__)\n#define POLLER "kqueue"\n'
            '#else\n#error "Unsupported platform"\n#endif\n')


def test_unsupported_platform_error_lets_qnx_join_the_bsd_branch(tmp_path):
    [f] = run(tmp_path, {"p.c": PLATFORM}, 'p.c:7:2: error: #error "Unsupported platform"\n')
    assert f.rule == "qnx-platform-guard" and f.verify
    assert "#elif (defined(__FreeBSD__) || defined(__APPLE__)) || defined(__QNX__)" in f.edits["p.c"]
    assert "#if defined(__linux__)\n" in f.edits["p.c"]
    if CC:
        assert compiles(tmp_path, f.edits["p.c"], "-U__linux__", "-D__QNX__")


def test_ifdef_linux_only_chain(tmp_path):
    src = "#ifdef __linux__\nint ok;\n#else\n#error Linux only\n#endif\n"
    [f] = run(tmp_path, {"l.c": src}, "l.c:4:2: error: #error Linux only\n")
    assert f.edits["l.c"].startswith("#if defined(__linux__) || defined(__QNX__)\n")


def test_error_outside_an_os_chain_is_not_touched(tmp_path):
    src = "#if __STDC_VERSION__ < 199901L\n#error need C99\n#endif\n"
    assert run(tmp_path, {"c.c": src}, "c.c:2:2: error: #error need C99\n") == []
    src2 = "#if defined(__linux__) || defined(__QNX__)\nint a;\n#else\n#error no\n#endif\n"
    assert run(tmp_path, {"d.c": src2}, "d.c:4:2: error: #error no\n") == []


def test_map_anonymous_becomes_map_anon(tmp_path):
    src = "#include <sys/mman.h>\nvoid *f(void) { return mmap(0, 4096, 3, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0); }\n"
    [f] = run(tmp_path, {"m.c": src}, "m.c:2:52: error: 'MAP_ANONYMOUS' undeclared (first use in this function)\n")
    assert f.rule == "map-anon" and f.cflags == ["-DMAP_ANONYMOUS=MAP_ANON"]


def test_msg_nosignal_only_when_the_library_already_ignores_sigpipe(tmp_path):
    log = "n.c:3:30: error: 'MSG_NOSIGNAL' undeclared (first use in this function)\n"
    src = "#include <sys/socket.h>\nlong f(int s, const void *b) {\n  return send(s, b, 1, MSG_NOSIGNAL); }\n"
    assert run(tmp_path, {"n.c": src}, log) == []
    assert "SO_NOSIGPIPE" in fixes.hint(parse(log)[0])
    (tmp_path / "init.c").write_text("#include <signal.h>\nvoid init(void) { signal(SIGPIPE, SIG_IGN); }\n")
    [f] = run(tmp_path, {}, log)
    assert f.rule == "msg-nosignal" and f.cflags == ["-DMSG_NOSIGNAL=0"]


def test_inotify_links_libfsnotify(tmp_path):
    [f] = run(tmp_path, {}, "w.c:(.text+0x12): undefined reference to `inotify_add_watch'\n")
    assert f.rule == "link-libfsnotify" and f.libs == ["-lfsnotify"]


def test_gcc10_no_common_link_error_gets_fcommon(tmp_path):
    log = ("/usr/bin/ld: /tmp/ccd0z8tK.o:(.bss+0x0): multiple definition of `counter'; "
           "/tmp/cco9f0jk.o:(.bss+0x0): first defined here\ncollect2: error: ld returned 1 exit status\n")
    [f] = run(tmp_path, {}, log)
    assert f.rule == "fcommon" and f.cflags == ["-fcommon"]


@pytest.mark.parametrize("lib", ["dl", "rt", "pthread"])
def test_libraries_that_are_libc_on_qnx(tmp_path, lib):
    [f] = run(tmp_path, {}, f"ld: cannot find -l{lib}: No such file or directory\n")
    assert f.rule == "stub-lib" and f.stubs == [lib]


@pytest.mark.parametrize("sym,header", [("gettid", "process.h"), ("dl_iterate_phdr", "sys/link.h"),
                                        ("getopt_long", "getopt.h"), ("memalign", "malloc.h"),
                                        ("strsep", "string.h"), ("pipe2", "unistd.h")])
def test_qnx_header_locations(tmp_path, sym, header):
    log = f"a.c:2:12: error: implicit declaration of function '{sym}' [-Wimplicit-function-declaration]\n"
    [f] = run(tmp_path, {"a.c": "#include <stdio.h>\nint f(void) { return 0; }\n"}, log)
    assert f"#include <{header}>" in f.edits["a.c"]


def test_removed_itoa_gets_the_snprintf_hint():
    d = parse("a.c:1:1: error: implicit declaration of function 'itoa' [-Wimplicit-function-declaration]\n")[0]
    assert "snprintf" in fixes.hint(d)


def test_math_classification_macros_need_libm_on_qnx(tmp_path):
    # Real ld output from porting yyjson 0.10.0 with qcc (SDP 8.0 build 141).
    log = ("/home/u/qnx800/host/linux/x86_64/usr/bin/x86_64-pc-nto-qnx8.0.0-ld: "
           "test_number.c:(.text+0x33ca): undefined reference to `__isfinite'\n"
           "test_json_writer.c:(.text+0xd5): undefined reference to `__isinf'\n")
    [f] = run(tmp_path, {}, log)
    assert f.rule == "link-libm" and f.libs == ["-lm"]
    assert run(tmp_path, {}, log, Flags(libs=["-lm"])) == []
