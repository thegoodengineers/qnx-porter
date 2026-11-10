"""Deterministic porting fixes. Each rule reads one diagnostic and returns a Fix with a plain reason, or None.

Rules come first; the language model only sees what no rule handles. A rule never guesses: it acts only
on what the compiler or linker said, plus facts about QNX 8.0's C library listed here.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from .errors import Diagnostic
from .qnx import Flags

# Where POSIX puts these. All of them exist in QNX 8.0's libc headers.
SYMBOL_HEADERS = {
    **dict.fromkeys(["strcasecmp", "strncasecmp", "bzero", "bcopy", "index", "rindex", "ffs"], "strings.h"),
    "alloca": "alloca.h",
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

# On Linux these are separate libraries; on QNX their functions are in libc, so -lX finds nothing.
IN_LIBC = {"pthread", "rt", "dl"}

# Linux-only headers. No rule can replace them honestly; they go to the model with this hint.
LINUX_ONLY = {
    "sys/epoll.h": "QNX has no epoll: use poll()/select(), or QNX's ionotify() for event notification",
    "sys/inotify.h": "QNX has no inotify: watch files with polling or the QNX inotify-compatible resource manager",
    "sys/eventfd.h": "QNX has no eventfd: use a pipe() pair or a pulse",
    "sys/prctl.h": "QNX has no prctl: thread names use pthread_setname_np()",
    "sys/sysinfo.h": "QNX has no sysinfo(): use sysconf(_SC_NPROCESSORS_ONLN), or the syspage for memory",
    "sys/sendfile.h": "QNX has no sendfile(): copy with read()/write()",
    "sys/signalfd.h": "QNX has no signalfd: use sigwaitinfo() in a thread",
    "sys/timerfd.h": "QNX has no timerfd: use timer_create() with a pulse or a signal",
    "byteswap.h": "QNX has no <byteswap.h>: use __builtin_bswap16/32/64",
    "execinfo.h": "QNX has no backtrace(): guard the code with !defined(__QNX__)",
    "features.h": "<features.h> is glibc-only: remove the include on QNX",
}

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

    def key(self):
        return (self.rule, tuple(sorted(self.edits)), tuple(self.cflags), tuple(self.libs), tuple(self.stubs),
                self.diag.symbol, self.diag.header)


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
    if d.kind in ("implicit_decl", "undeclared") and rel:
        header = d.header or SYMBOL_HEADERS.get(d.symbol)
        how = "the compiler's own note names it" if d.header else "POSIX declares it there"
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
    if d.kind == "werror" and d.flag and f"-Wno-error={d.flag}" not in flags.cflags:
        return Fix("no-werror", f"Warning -W{d.flag} is promoted to an error by the project's -Werror. Keep "
                   "it a warning (still printed in the build log) instead of editing the library's code; "
                   "QNX's headers and qcc raise warnings a glibc build does not.",
                   d, cflags=[f"-Wno-error={d.flag}"])
    if d.kind == "undefined_ref" and d.symbol in SOCKET_SYMBOLS and "-lsocket" not in flags.libs:
        return Fix("link-libsocket", f"`{d.symbol}` is in QNX's libsocket, not in libc as on Linux: link "
                   "with -lsocket.", d, libs=["-lsocket"])
    if d.kind == "missing_lib" and d.symbol in IN_LIBC:
        return Fix("stub-lib", f"-l{d.symbol} names a separate library on Linux; on QNX its functions are in "
                   f"libc. An empty lib{d.symbol}.a satisfies the link without editing the build files.",
                   d, stubs=[d.symbol])
    return None


def linux_only_hint(d: Diagnostic) -> str:
    if d.kind == "missing_header":
        if d.header.startswith("linux/"):
            return f"<{d.header}> is a Linux kernel header and does not exist on QNX"
        return LINUX_ONLY.get(d.header, "")
    return ""
