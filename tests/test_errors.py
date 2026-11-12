from qnx_porter.errors import parse

LD = "/home/u/qnx800/host/linux/x86_64/usr/bin/x86_64-pc-nto-qnx8.0.0-ld"


def kinds(log):
    return [(d.kind, d.symbol or d.header or d.flag) for d in parse(log)]


def test_missing_header():
    d = parse("src/poller.c:12:10: fatal error: sys/epoll.h: No such file or directory\n")[0]
    assert (d.kind, d.header, d.file, d.line) == ("missing_header", "sys/epoll.h", "src/poller.c", 12)


def test_implicit_declaration_takes_the_compilers_include_hint():
    log = ("a.c: In function 'f':\n"
           "a.c:8:12: error: implicit declaration of function 'strcasecmp' [-Werror=implicit-function-declaration]\n"
           "a.c:3:1: note: include '<strings.h>' or provide a declaration of 'strcasecmp'\n")
    d = parse(log)[0]
    assert (d.kind, d.symbol, d.header, d.flag) == ("implicit_decl", "strcasecmp", "strings.h",
                                                     "implicit-function-declaration")


def test_cxx_undeclared_with_defined_in_note_and_utf8_quotes():
    log = ("x.cpp:5:3: error: ‘uint8_t’ was not declared in this scope\n"
           "x.cpp:1:1: note: ‘uint8_t’ is defined in header ‘<cstdint>’; "
           "did you forget to ‘#include <cstdint>’?\n")
    d = parse(log)[0]
    assert (d.kind, d.symbol, d.header) == ("undeclared", "uint8_t", "cstdint")


def test_plain_warnings_are_ignored_but_werror_is_kept():
    log = ("a.c:1:1: warning: unused parameter 'x' [-Wunused-parameter]\n"
           "a.c:2:7: error: unused variable 'y' [-Werror=unused-variable]\n")
    assert kinds(log) == [("werror", "unused-variable")]


def test_linker_errors():
    log = (f"{LD}: CMakeFiles/net.dir/net.c.o: in function `open_conn':\n"
           "net.c:(.text+0x2a): undefined reference to `socket'\n"
           "net.c:(.text+0x5b): undefined reference to `getaddrinfo'\n"
           f"{LD}: cannot find -lrt: No such file or directory\n"
           "collect2: error: ld returned 1 exit status\n")
    assert kinds(log)[:3] == [("undefined_ref", "socket"), ("undefined_ref", "getaddrinfo"), ("missing_lib", "rt")]


def test_configure_and_cmake_errors():
    log = ("checking for epoll_ctl... no\nconfigure: error: epoll is required\n"
           "CMake Error at CMakeLists.txt:42 (message):\n  Unsupported platform: QNX\n")
    d = parse(log)
    assert d[0].kind == "configure_error" and d[0].message == "epoll is required"
    assert d[1].kind == "cmake_error" and d[1].line == 42 and "Unsupported platform" in d[1].message


def test_duplicates_are_dropped():
    line = "a.c:3:5: error: 'MSG_NOSIGNAL' undeclared (first use in this function)\n"
    assert len(parse(line * 3)) == 1
