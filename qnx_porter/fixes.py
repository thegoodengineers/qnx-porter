"""Deterministic porting fixes. Each rule reads one diagnostic and returns a Fix with a plain reason, or None.

Rules come first; the language model only sees what no rule handles. A rule never guesses: it acts only
on what the compiler or linker said, plus facts about QNX 8.0's C library listed here.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import linuxisms
from .errors import Diagnostic
from .qnx import Flags

# Where POSIX puts these. All of them exist in QNX 8.0's libc headers.
SYMBOL_HEADERS = {
    **dict.fromkeys(["strcasecmp", "strncasecmp", "bzero", "bcopy", "index", "rindex", "ffs"], "strings.h"),
    "alloca": "alloca.h",
    # QNX 8.0 C Library Reference: where QNX declares these (differs from glibc for gettid, dl_iterate_phdr)
    "gettid": "process.h",
    "dl_iterate_phdr": "sys/link.h",
    **dict.fromkeys(["getopt_long", "getopt_long_only"], "getopt.h"),
    **dict.fromkeys(["memalign", "malloc_usable_size", "mallinfo"], "malloc.h"),
    **dict.fromkeys(["strsep", "strcasestr", "memmem", "strerror_r"], "string.h"),
    **dict.fromkeys(["asprintf", "vasprintf"], "stdio.h"),
    "pipe2": "unistd.h",
    "posix_memalign": "stdlib.h",
    **dict.fromkeys(["select", "fd_set", "FD_SET", "FD_ZERO", "FD_ISSET", "FD_CLR"], "sys/select.h"),
    **dict.fromkeys(["gettimeofday", "timeval", "settimeofday"], "sys/time.h"),
    **dict.fromkeys(["inet_pton", "inet_ntop", "inet_addr", "inet_ntoa", "htons", "htonl", "ntohs", "ntohl"],
                    "arpa/inet.h"),
    **dict.fromkeys(["getaddrinfo", "freeaddrinfo", "gai_strerror", "gethostbyname", "addrinfo"], "netdb.h"),
    **dict.fromkeys(["socket", "bind", "connect", "listen", "accept", "setsockopt", "getsockopt", "send",
                     "recv", "sendto", "recvfrom", "socklen_t", "sockaddr", "shutdown"], "sys/socket.h"),
    **dict.fromkeys(["sockaddr_in", "sockaddr_in6", "IPPROTO_TCP", "INADDR_ANY"], "netinet/in.h"),
    "TCP_NODELAY": "netinet/tcp.h",
    **dict.fromkeys(["ioctl", "FIONBIO", "FIONREAD"], "sys/ioctl.h"),
    **dict.fromkeys(["mmap", "munmap", "mprotect", "MAP_FAILED", "PROT_READ", "PROT_WRITE"], "sys/mman.h"),
    **dict.fromkeys(["usleep", "sleep", "close", "read", "write", "unlink", "getpid", "sysconf", "access",
                     "isatty", "getcwd", "lseek", "pipe", "fork", "dup2"], "unistd.h"),
    **dict.fromkeys(["clock_gettime", "nanosleep", "CLOCK_MONOTONIC", "CLOCK_REALTIME"], "time.h"),
    **dict.fromkeys(["PATH_MAX", "INT_MAX", "LONG_MAX", "CHAR_BIT"], "limits.h"),
    **dict.fromkeys(["uint8_t", "uint16_t", "uint32_t", "uint64_t", "int8_t", "int16_t", "int32_t",
                     "int64_t", "uintptr_t", "intptr_t", "SIZE_MAX", "UINT32_MAX", "UINT64_MAX"], "stdint.h"),
    **dict.fromkeys(["ssize_t", "off_t", "pid_t", "mode_t"], "sys/types.h"),
    **dict.fromkeys(["open", "fcntl", "O_RDONLY", "O_NONBLOCK", "O_CLOEXEC"], "fcntl.h"),
    **dict.fromkeys(["strdup", "strndup", "memset", "memcpy", "strlen", "strerror"], "string.h"),
    **dict.fromkeys(["stat", "fstat", "mkdir", "S_ISDIR"], "sys/stat.h"),
    **dict.fromkeys(["pthread_create", "pthread_mutex_t", "pthread_t"], "pthread.h"),
}

# Network functions live in libsocket on QNX, not in libc as on Linux.
SOCKET_SYMBOLS = {"socket", "bind", "connect", "listen", "accept", "accept4", "setsockopt", "getsockopt",
                  "send", "recv", "sendto", "recvfrom", "sendmsg", "recvmsg", "shutdown", "getaddrinfo",
                  "freeaddrinfo", "gai_strerror", "getnameinfo", "gethostbyname", "gethostbyaddr",
                  "getpeername", "getsockname", "inet_pton", "inet_ntop", "inet_addr", "inet_ntoa",
                  "if_nametoindex", "if_indextoname", "getifaddrs", "freeifaddrs", "socketpair"}

# On Linux these are separate libraries; on QNX 8.0 their functions are in libc (the C Library Reference
# lists "Library: libc" for pthread_*, clock_gettime, timer_create, shm_open, mq_open and dlopen).
IN_LIBC = {"pthread", "rt", "dl"}

# a library typedef of (u)intptr_t that disagrees with QNX's <stdint.h> (cmocka on aarch64le)
# a negative constant put in a plain char: an error only where char is unsigned (yaml-cpp's tests on aarch64le)
UNSIGNED_CHAR = re.compile(r"narrowing conversion of ['‘’`]-\d+['‘’`] from ['‘’`]int['‘’`] to ['‘’`]char['‘’`]")
WORDSIZE_GUESS = re.compile(r"conflicting types for ['‘’`]u?intptr_t['‘’`]; have ['‘’`](?:unsigned )?int['‘’`]")

# QNX 8.0 moved inotify_* out of libc into libfsnotify ("Migrating to QNX OS 8.0", C and C++ applications).
WCSWIDTH_HEADER = """/* qnx-porter: POSIX wcswidth() on top of QNX 8.0's wcwidth() */
#include <stddef.h>
#include <wchar.h>
static inline int qnx_porter_wcswidth(const wchar_t *s, size_t n)
{
    int width = 0;
    for (; n > 0 && *s != L'\\0'; n--, s++) {
        int w = wcwidth(*s);
        if (w < 0)
            return -1;
        width += w;
    }
    return width;
}
#define wcswidth qnx_porter_wcswidth
"""

# POSIX regex functions: exported by libregex.so on QNX 8.0, not by libc.so (nm on SDP 8.0 build 141).
REGEX_SYMBOLS = {"regcomp", "regexec", "regfree", "regerror"}
FSNOTIFY_SYMBOLS = {"inotify_init", "inotify_init1", "inotify_add_watch", "inotify_rm_watch"}

# QNX's <math.h> turns isinf()/isfinite()/isnan()/fpclassify() into calls to __isinf etc., and those, like
# sqrt and floor, are exported by libm.so and not by libc.so (checked with nm on SDP 8.0 build 141). glibc
# resolves the classification macros inline or in libc, so Linux projects often never link -lm.
_MATH = ["sqrt", "cbrt", "pow", "exp", "exp2", "expm1", "log", "log2", "log10", "log1p", "floor", "ceil",
         "round", "lround", "llround", "trunc", "rint", "lrint", "llrint", "nearbyint", "fmod", "remainder",
         "sin", "cos", "tan", "asin", "acos", "atan", "atan2", "sinh", "cosh", "tanh", "asinh", "acosh",
         "atanh", "hypot", "ldexp", "frexp", "modf", "scalbn", "copysign", "nextafter", "fmax", "fmin", "fdim",
         "fma", "erf", "erfc", "tgamma", "lgamma", "nan"]
_CLASSIFY = ["__isinf", "__isnan", "__isfinite", "__isnormal", "__fpclassify", "__signbit"]
ENDIAN_MACROS = {f"{a}{n}{b}" for n in (16, 32, 64) for a, b in
                 (("htobe", ""), ("htole", ""), ("be", "toh"), ("le", "toh"))}
BSD_ENDIAN_MACROS = {f"{a}{n}" for n in (16, 32, 64) for a in ("betoh", "letoh")}
ALL_ENDIAN_MACROS = ENDIAN_MACROS | BSD_ENDIAN_MACROS

# QNX 8.0 has these as BSD macros in <net/netbyte.h>, visible only with __EXT_BSD (off under strict POSIX
# macros). The compat header includes it and fills any missing name from QNX's own __NET_BE*/__NET_LE*
# helpers. It is -included into every compile: function-like -D flags would break the make shell.
ENDIAN_HEADER = ("/* qnx-porter: glibc <endian.h> names, from QNX's <net/netbyte.h> */\n#include <net/netbyte.h>\n"
                 + "".join(f"#ifndef {m}\n#define {m}(x) __NET_{'BE' if m.startswith(('htobe', 'be', 'betoh')) else 'LE'}"
                           f"{''.join(c for c in m if c.isdigit())}((x))\n#endif\n" for m in sorted(ALL_ENDIAN_MACROS)))

# Standalone compatibility header for projects that explicitly do `#include <endian.h>`.
# QNX 8.0 does not ship <endian.h>. This header includes <net/netbyte.h> when available,
# defines standard byte-order constants (__LITTLE_ENDIAN, __BIG_ENDIAN, __PDP_ENDIAN, __BYTE_ORDER,
# and their unqualified aliases), and defines all 16/32/64-bit conversion macros.
ENDIAN_COMPAT_H = ("#ifndef _QNX_PORTER_ENDIAN_H\n#define _QNX_PORTER_ENDIAN_H\n\n"
                   "#if defined(__has_include)\n"
                   "#  if __has_include(<net/netbyte.h>)\n"
                   "#    include <net/netbyte.h>\n"
                   "#  endif\n"
                   "#else\n"
                   "#  include <net/netbyte.h>\n"
                   "#endif\n\n"
                   "/* Byte order constants */\n"
                   "#ifndef __LITTLE_ENDIAN\n#  define __LITTLE_ENDIAN 1234\n#endif\n"
                   "#ifndef __BIG_ENDIAN\n#  define __BIG_ENDIAN 4321\n#endif\n"
                   "#ifndef __PDP_ENDIAN\n#  define __PDP_ENDIAN 3412\n#endif\n"
                   "#ifndef __BYTE_ORDER\n"
                   "#  if defined(__BYTE_ORDER__)\n"
                   "#    define __BYTE_ORDER __BYTE_ORDER__\n"
                   "#  elif defined(__ORDER_LITTLE_ENDIAN__) && defined(__ORDER_BIG_ENDIAN__)\n"
                   "#    if defined(__BIG_ENDIAN__)\n"
                   "#      define __BYTE_ORDER __BIG_ENDIAN\n"
                   "#    else\n"
                   "#      define __BYTE_ORDER __LITTLE_ENDIAN\n"
                   "#    endif\n"
                   "#  else\n"
                   "#    define __BYTE_ORDER __LITTLE_ENDIAN\n"
                   "#  endif\n"
                   "#endif\n\n"
                   "#ifndef LITTLE_ENDIAN\n#  define LITTLE_ENDIAN __LITTLE_ENDIAN\n#endif\n"
                   "#ifndef BIG_ENDIAN\n#  define BIG_ENDIAN __BIG_ENDIAN\n#endif\n"
                   "#ifndef PDP_ENDIAN\n#  define PDP_ENDIAN __PDP_ENDIAN\n#endif\n"
                   "#ifndef BYTE_ORDER\n#  define BYTE_ORDER __BYTE_ORDER\n#endif\n\n"
                   "/* Endian conversion macros */\n"
                   + "".join(f"#ifndef {m}\n#  define {m}(x) __NET_{'BE' if m.startswith(('htobe', 'be', 'betoh')) else 'LE'}"
                             f"{''.join(c for c in m if c.isdigit())}((x))\n#endif\n" for m in sorted(ALL_ENDIAN_MACROS))
                   + "\n#endif /* _QNX_PORTER_ENDIAN_H */\n")

LIBM_SYMBOLS = {f"{n}{s}" for n in _MATH + _CLASSIFY for s in ("", "f", "l")}

INCLUDE = re.compile(r"^\s*#\s*include\b")


@dataclass
class Fix:
    rule: str
    reason: str
    diag: Diagnostic
    edits: dict[str, str] = field(default_factory=dict)  # path relative to src -> new text
    cflags: list[str] = field(default_factory=list)
    ldflags: list[str] = field(default_factory=list)
    libs: list[str] = field(default_factory=list)
    stubs: list[str] = field(default_factory=list)
    late: list[str] = field(default_factory=list)  # flags that must come after the project's own
    settings: dict = field(default_factory=dict)  # toolchain switches, set on Flags
    verify: bool = False  # needs a rebuild to prove it: applied alone, reverted if the error stays
    compat: dict[str, str] = field(default_factory=dict)  # header name -> text, -included in every compile

    def key(self):
        flags = (self.rule, tuple(self.cflags), tuple(self.ldflags), tuple(self.libs), tuple(self.stubs),
                 tuple(self.late), tuple(sorted(self.settings.items())))
        if not self.edits:
            return flags  # one flag change answers every error that asks for it
        return flags + (tuple(sorted(self.edits)), self.diag.symbol, self.diag.header)


def add_include(src: Path, rel: str, header: str, before_line: int) -> str | None:
    """Text of `rel` with `#include <header>` after the last include above the error line. None if present."""
    path = src / rel
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    lines = text.splitlines(keepends=True)
    if any(re.match(rf"\s*#\s*include\s*[<\"]{re.escape(header)}[>\"]", ln) for ln in lines):
        return None
    incs = [i for i, ln in enumerate(lines) if INCLUDE.match(ln) and i < max(before_line - 1, 1)]
    at = incs[-1] + 1 if incs else _after_header_comment(lines)
    lines.insert(at, f"#include <{header}>  /* qnx-porter: needed on QNX */\n")
    return "".join(lines)


def _after_header_comment(lines: list[str]) -> int:
    i = 0
    if lines and lines[0].lstrip().startswith("/*"):
        while i < len(lines) and "*/" not in lines[i]:
            i += 1
        return i + 1
    while i < len(lines) and lines[i].lstrip().startswith("//"):
        i += 1
    return i


def in_tree(src: Path, file: str) -> str | None:
    """The diagnostic's file relative to src, or None if it is outside the library (a system header)."""
    try:
        p = Path(file)
        p = p if p.is_absolute() else (src / p)
        rel = p.resolve().relative_to(src.resolve())
        return rel.as_posix() if (src / rel).is_file() else None
    except (ValueError, OSError):
        return None


def plan(diags: list[Diagnostic], src: Path, flags: Flags, tried: set) -> list[Fix]:
    """Deterministic fixes for this round, at most one per file and one per flag, never one tried before."""
    fixes, files, seen = [], set(), set()
    for d in diags:
        f = _rule(d, src, flags)
        if not f or f.key() in tried or f.key() in seen or (f.edits and files & set(f.edits)):
            continue
        seen.add(f.key())
        files |= set(f.edits)
        fixes.append(f)
    return fixes


def _rule(d: Diagnostic, src: Path, flags: Flags) -> Fix | None:
    rel = in_tree(src, d.file) if d.file else None
    if rel and (f := _source_rule(d, src, rel)):
        return f
    if d.kind in ("implicit_decl", "undeclared") and rel:
        header = d.header or SYMBOL_HEADERS.get(d.symbol)
        how = "the compiler's own note names it" if d.header else "that is where QNX declares it"
        if header:
            new = add_include(src, rel, header, d.line)
            if new is not None:
                return Fix("add-include", f"`{d.symbol}` is declared in <{header}> ({how}); {rel} did not "
                           f"include it. glibc pulls it in through other headers, QNX's libc does not.",
                           d, edits={rel: new})
            if d.kind == "implicit_decl" and "-D_QNX_SOURCE" not in flags.cflags:
                return Fix("qnx-source", f"`{d.symbol}` is in <{header}>, which {rel} already includes, so a "
                           "strict feature-test macro hid it. -D_QNX_SOURCE exposes POSIX and QNX extensions "
                           "in QNX's headers, as _GNU_SOURCE does on glibc.", d, cflags=["-D_QNX_SOURCE"])
    if d.kind == "error" and "-D_QNX_SOURCE" not in flags.cflags and \
            (m := re.search(r"no matching function for call to .(\w+)::\1\(", d.message)) and m[1] in SYMBOL_HEADERS:
        return Fix("qnx-source", f"C++ sees only `struct {m[1]}`, not the POSIX function `{m[1]}()`: in strict "
                   "-std=c++NN mode QNX's headers hide POSIX extensions (here sys/stat.h declares stat() only under "
                   "__EXT_POSIX1_198808). -D_QNX_SOURCE exposes them, as _GNU_SOURCE does on glibc.",
                   d, cflags=["-D_QNX_SOURCE"])
    if d.kind == "undeclared" and d.symbol == "SA_RESTART" and not _defined(flags, "SA_RESTART"):
        return Fix("sa-restart", "QNX 8.0's <signal.h> lists SA_RESTART as not supported yet. Defining it as 0 "
                   "lets the code build; system calls interrupted by a signal then return EINTR instead of "
                   "restarting, which the library's tests on QNX show it handles or not.", d,
                   cflags=["-DSA_RESTART=0"])
    if d.kind == "undeclared" and d.symbol == "MAP_ANONYMOUS" and not _defined(flags, "MAP_ANONYMOUS"):
        return Fix("map-anon", "QNX 8.0's mmap() documents MAP_ANON for anonymous memory; Linux code spells it "
                   "MAP_ANONYMOUS. Same flag, so define one as the other.", d, cflags=["-DMAP_ANONYMOUS=MAP_ANON"])
    if d.kind == "undeclared" and d.symbol == "MSG_NOSIGNAL" and not _defined(flags, "MSG_NOSIGNAL") \
            and linuxisms.tree_ignores_sigpipe(src):
        return Fix("msg-nosignal", "MSG_NOSIGNAL is not visible here, and this library already ignores "
                   "SIGPIPE (signal(SIGPIPE, SIG_IGN)), so the flag has nothing left to do: define it as 0.",
                   d, cflags=["-DMSG_NOSIGNAL=0"])
    if d.kind == "werror" and not d.flag and "-Wno-error" not in flags.cflags + flags.late:
        return Fix("no-werror", "A warning that has no -W switch of its own (here: " + d.message[:80] + ") is made an "
                   "error by the project's -Werror. The only way to keep it a warning is -Wno-error; the warning "
                   "is still printed in the build log.", d, late=["-Wno-error"])
    if d.kind == "werror" and d.flag and f"-Wno-error={d.flag}" not in flags.cflags + flags.late:
        return Fix("no-werror", f"Warning -W{d.flag} is promoted to an error by the project's -Werror. Keep "
                   "it a warning (still printed in the build log) instead of editing the library's code; "
                   "QNX's headers and qcc raise warnings a glibc build does not.",
                   d, late=[f"-Wno-error={d.flag}"])
    # QNX's <arpa/inet.h> maps inet_pton to __inet_pton and so on, all exported by libsocket.
    if d.kind == "undefined_ref" and d.symbol.lstrip("_") in SOCKET_SYMBOLS and "-lsocket" not in flags.libs:
        return Fix("link-libsocket", f"`{d.symbol}` is in QNX's libsocket, not in libc as on Linux: link "
                   "with -lsocket.", d, libs=["-lsocket"])
    if d.kind in ("undefined_ref", "implicit_decl") and d.symbol == "wcswidth" and "-D_QNX_PORTER_WCSWIDTH" not in flags.cflags:
        return Fix("wcswidth-compat", "QNX 8.0's libc has wcwidth() but no wcswidth(). POSIX defines wcswidth(s, n) "
                   "as the sum of wcwidth() over the first n characters of s, or -1 if any is not printable; a "
                   "small header (-included in every compile) implements exactly that on top of QNX's wcwidth().",
                   d, cflags=["-D_QNX_PORTER_WCSWIDTH"], compat={"qnx-wcswidth.h": WCSWIDTH_HEADER})
    if WORDSIZE_GUESS.search(d.message) and not _defined(flags, "__WORDSIZE"):
        return Fix("wordsize-64", "The library guesses the word size from glibc's __WORDSIZE, else from __x86_64__, "
                   "else assumes 32 bits (cmocka.h), and so redefines (u)intptr_t as a 32-bit type on aarch64. "
                   "QNX 8.0's x86_64 and aarch64le targets are both LP64 and QNX's headers never define "
                   "__WORDSIZE, so define it as 64.", d, cflags=["-D__WORDSIZE=64"])
    if UNSIGNED_CHAR.search(d.message) and "-fsigned-char" not in flags.cflags:
        return Fix("signed-char", "Plain char is unsigned on aarch64 (the Arm ABI) and signed on x86_64; the code "
                   "puts a negative constant in a char, which is fine on x86_64 and a narrowing error on aarch64. "
                   "-fsigned-char keeps the x86_64 meaning the code was written for, without editing it.",
                   d, cflags=["-fsigned-char"])
    if d.kind == "qcc_option" and d.symbol.startswith("--sysroot") and not flags.omit_sysroot:
        return Fix("qcc-sysroot", "The project's own build script passes --sysroot to the compiler, which qcc does "
                   "not accept. qcc already finds the SDP sysroot through QNX_TARGET, so the toolchain stops "
                   "setting CMAKE_SYSROOT (libraries are still found through CMAKE_FIND_ROOT_PATH).",
                   d, settings={"omit_sysroot": True})
    if d.kind == "undefined_ref" and d.symbol in REGEX_SYMBOLS and "-lregex" not in flags.libs:
        return Fix("link-libregex", f"`{d.symbol}` (POSIX <regex.h>) is in QNX's libregex, not in libc as on "
                   "Linux: link with -lregex.", d, libs=["-lregex"])
    if d.kind == "undefined_ref" and d.symbol in FSNOTIFY_SYMBOLS and "-lfsnotify" not in flags.libs:
        return Fix("link-libfsnotify", f"QNX 8.0 has inotify, but `{d.symbol}` moved from libc to libfsnotify: "
                   "link with -lfsnotify.", d, libs=["-lfsnotify"])
    if d.kind == "missing_header" and d.header == "endian.h" and "-D_QNX_PORTER_ENDIAN" not in flags.cflags:
        return Fix("endian-compat", "<endian.h> does not exist on QNX 8.0. QNX provides BSD byte-order "
                   "conversion macros in <net/netbyte.h> (__NET_BE*/__NET_LE*); a generated compatibility "
                   "<endian.h> header in the include search path maps glibc names and byte-order "
                   "constants to QNX's definitions.", d,
                   cflags=["-D_QNX_PORTER_ENDIAN"], compat={"endian.h": ENDIAN_COMPAT_H})
    if d.kind in ("undefined_ref", "implicit_decl") and d.symbol in ALL_ENDIAN_MACROS \
            and "-D_QNX_PORTER_ENDIAN" not in flags.cflags:
        return Fix("endian-netbyte", f"`{d.symbol}` comes from glibc's <endian.h>, which QNX 8.0 does not have. "
                   "QNX has the same names as BSD macros in <net/netbyte.h>; a small header (-included in "
                   "every compile) includes it and defines any name strict POSIX flags hid, from QNX's "
                   "__NET_BE*/__NET_LE* helpers.", d,
                   cflags=["-D_QNX_PORTER_ENDIAN"], compat={"qnx-endian.h": ENDIAN_HEADER})
    if d.kind == "undefined_ref" and d.symbol in LIBM_SYMBOLS and "-lm" not in flags.libs:
        return Fix("link-libm", f"`{d.symbol}` is in QNX's libm, not in libc: QNX's <math.h> implements "
                   "isinf/isfinite/isnan as calls to __isinf etc. in libm, where glibc needs no library. "
                   "Link with -lm.", d, libs=["-lm"])
    if d.kind == "multiple_def" and "-fcommon" not in flags.cflags:
        return Fix("fcommon", f"`{d.symbol}` is a tentative definition in a header, shared by several files. "
                   "GCC 10 and later (SDP 8.0 ships GCC 12) default to -fno-common, which makes that a link "
                   "error; -fcommon restores the old behaviour without editing the library.",
                   d, cflags=["-fcommon"])
    if d.kind == "missing_lib" and d.symbol in IN_LIBC:
        return Fix("stub-lib", f"-l{d.symbol} names a separate library on Linux; on QNX its functions are in "
                   f"libc. An empty lib{d.symbol}.a satisfies the link without editing the build files.",
                   d, stubs=[d.symbol])
    return None


def _defined(flags: Flags, name: str) -> bool:
    return any(c.startswith(f"-D{name}=") for c in flags.cflags)


def _source_rule(d: Diagnostic, src: Path, rel: str) -> Fix | None:
    """Rules that rewrite a few lines of source (linuxisms.py)."""
    risky = {"prctl-set-name", "qnx-platform-guard", "bool-typedef"}
    for rule_fn, kinds in ((linuxisms.header_alias, ("missing_header",)),
                           (linuxisms.missing_header, ("missing_header",)),
                           (linuxisms.bool_typedef, ("error",)),
                           (linuxisms.renamed_call, ("implicit_decl",)),
                           (linuxisms.one_arg_setname, ("error",)),
                           (linuxisms.platform_guard, ("hash_error",))):
        if d.kind in kinds and (r := rule_fn(d, src, rel)):
            rule, reason, text = r
            return Fix(rule, reason, d, edits={rel: text}, verify=rule in risky)
    return None


def hint(d: Diagnostic) -> str:
    return linuxisms.hint(d)
