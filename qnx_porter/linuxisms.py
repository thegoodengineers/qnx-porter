"""Rules for Linux-only code that breaks on QNX 8.0. The corpus behind them: docs/LINUX_ISMS.md.

Facts come from QNX's own documentation for SDP 8.0 (C Library Reference, the io-sock Networking
APIs page, and "Migrating to QNX OS 8.0"); each rule names its source in docs/LINUX_ISMS.md. A rule
edits code only when the edit is mechanical; anything that needs judgement gets a hint for the model.
"""
import re
from pathlib import Path

from .errors import Diagnostic

# Linux-only headers -> (pattern of identifiers that header provides, hint for when they are used).
LINUX_HEADERS = {
    "sys/epoll.h": (r"\bepoll_\w+|\bEPOLL\w+", "QNX has no epoll: use poll()/select(), or ionotify() for "
                    "event delivery"),
    "sys/eventfd.h": (r"\beventfd\w*|\bEFD_\w+", "QNX has no eventfd: use a pipe2() pair"),
    "sys/timerfd.h": (r"\btimerfd_\w+|\bTFD_\w+", "QNX has no timerfd: use timer_create() with a signal or pulse"),
    "sys/signalfd.h": (r"\bsignalfd\w*|\bSFD_\w+", "QNX has no signalfd: use sigwaitinfo() in a thread"),
    "sys/sendfile.h": (r"\bsendfile\w*", "QNX has no sendfile(): copy with a read()/write() loop"),
    "sys/sysinfo.h": (r"\bsysinfo\b|\bget_nprocs\w*", "QNX has no sysinfo(): use sysconf(_SC_NPROCESSORS_ONLN)"),
    "sys/prctl.h": (r"\bprctl\b|\bPR_\w+", "QNX has no prctl(): name threads with pthread_setname_np()"),
    "sys/random.h": (r"\bgetrandom\b|\bGRND_\w+", "QNX has no getrandom(): read /dev/urandom"),
    "byteswap.h": (r"\bbswap_(?:16|32|64)\b", "QNX has no <byteswap.h>: use __builtin_bswap16/32/64"),
    "execinfo.h": (r"\bbacktrace\w*", "QNX has no backtrace(): guard that code with !defined(__QNX__)"),
    "features.h": (r"(?!)", "<features.h> is glibc-only"),  # provides nothing a port needs
    "mcheck.h": (r"\bmcheck\w*|\bmtrace\b|\bmuntrace\b", "glibc-only heap checking: guard with !defined(__QNX__)"),
    "endian.h": (r"\b(?:htobe|htole|be|le)(?:16|32|64)(?:toh)?\b|\b__?BYTE_ORDER\b|\b__?(?:LITTLE|BIG)_ENDIAN\b",
                 "QNX 8.0 has no <endian.h>: use <gulliver.h> (ENDIAN_LE32 etc.) or GCC's __BYTE_ORDER__"),
}
# <sys/X.h> spellings glibc accepts and QNX 8.0 does not ship; the plain <X.h> exists (SDP 8.0 build 141).
HEADER_ALIASES = {f"sys/{h}.h": f"{h}.h" for h in
                  ("errno", "signal", "syslog", "unistd", "fcntl", "termios", "dirent")}
REMOVED = {  # removed from QNX 8.0's libc ("Migrating to QNX OS 8.0", C and C++ applications)
    **dict.fromkeys(["itoa", "ltoa", "lltoa", "ultoa", "ulltoa", "utoa"],
                    "QNX 8.0 removed itoa() and friends from <stdlib.h>: use snprintf()"),
}
OS_MACROS = ["__FreeBSD__", "__NetBSD__", "__OpenBSD__", "__unix__", "__unix", "__linux__", "__linux",
             "__APPLE__"]  # preference order: io-sock and much of QNX's libc are BSD-derived
IF_LINE = re.compile(r"^\s*#\s*(if|ifdef|ifndef)\b")
BRANCH = re.compile(r"^\s*#\s*(elif|else)\b")
ENDIF = re.compile(r"^\s*#\s*endif\b")


def _read(src: Path, rel: str) -> str:
    return (src / rel).read_text(encoding="utf-8", errors="surrogateescape")


def _strip_comments(text: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", " ", text, flags=re.S)


def _include_re(header: str):
    return re.compile(rf"^([ \t]*#[ \t]*include[ \t]*<{re.escape(header)}>[^\n]*\n)", re.M)


def guard_include(text: str, header: str, extra_qnx: str = "") -> str:
    """Wrap `#include <header>` in #ifndef __QNX__, optionally with a QNX replacement in the #else."""
    alt = f"#else\n{extra_qnx}" if extra_qnx else ""
    return _include_re(header).sub(lambda m: f"#ifndef __QNX__  /* qnx-porter: <{header}> is Linux-only */\n"
                                             f"{m[1]}{alt}#endif\n", text, count=1)


def missing_header(d: Diagnostic, src: Path, rel: str):
    """(rule, reason, new_text) for a missing Linux-only header, or None with only a hint left."""
    if d.header not in LINUX_HEADERS:
        return None
    pattern, _hint = LINUX_HEADERS[d.header]
    text = _read(src, rel)
    if not _include_re(d.header).search(text):
        return None
    body = _include_re(d.header).sub("", _strip_comments(text))
    used = sorted(set(re.findall(pattern, body)))
    if not used:
        return ("guard-linux-header", f"<{d.header}> does not exist on QNX 8.0 and {rel} uses nothing from it, "
                "so the include is kept for Linux and skipped on QNX.", guard_include(text, d.header))
    if d.header == "byteswap.h":
        shim = "".join(f"#define bswap_{n}(x) __builtin_bswap{n}(x)\n" for n in (16, 32, 64))
        return ("byteswap-builtins", "<byteswap.h> is glibc-only. On QNX the same bswap_16/32/64 names map to "
                "GCC's __builtin_bswap16/32/64, which qcc (GCC 12) provides.", guard_include(text, d.header, shim))
    if d.header == "sys/prctl.h":
        new = prctl_to_setname(text)
        if new:
            return ("prctl-set-name", "QNX 8.0 has no prctl(). Every use here is prctl(PR_SET_NAME, name), "
                    "which on QNX is pthread_setname_np(pthread_self(), name) (libc, <pthread.h>). Note: it "
                    "returns an errno value instead of -1.", new)
    return None


def header_alias(d: Diagnostic, src: Path, rel: str):
    """`#include <sys/errno.h>` and friends: QNX ships only the POSIX spelling <errno.h>."""
    plain = HEADER_ALIASES.get(d.header)
    if not plain:
        return None
    text = _read(src, rel)
    new, n = re.subn(rf"(#[ \t]*include[ \t]*)<{re.escape(d.header)}>", rf"\1<{plain}>", text)
    if not n:
        return None
    return ("header-alias", f"<{d.header}> is a glibc alias QNX 8.0 does not ship; POSIX's <{plain}> declares "
            "the same things, and QNX has it.", new)


def bool_typedef(d: Diagnostic, src: Path, rel: str):
    """`typedef unsigned int bool;` after QNX's <sys/socket.h>, which pulls in <stdbool.h>.

    On QNX 8.0, <sys/socket.h> includes io-sock/types_fbsd.h, which includes <stdbool.h>, so `bool` is
    already the _Bool macro. Guard the typedef so the library uses stdbool's bool. Proved by rebuilding.
    """
    # GCC 12 (qcc in SDP 8.0) says "two or more data types"; GCC 13+ says "'bool' cannot be defined via 'typedef'"
    if not re.search(r"two or more data types in declaration specifiers|bool.{0,3} cannot be defined via", d.message):
        return None
    lines = _read(src, rel).splitlines(keepends=True)
    i = d.line - 1
    if not (0 <= i < len(lines)) or not re.match(r"\s*typedef\s+[\w\s]+\s+bool\s*;", lines[i]):
        return None
    lines[i] = (f"#ifndef __bool_true_false_are_defined  /* qnx-porter: QNX's <sys/socket.h> includes "
                f"<stdbool.h> */\n{lines[i]}#endif\n")
    return ("bool-typedef", f"{rel} defines its own `bool`, but on QNX 8.0 <sys/socket.h> already includes "
            "<stdbool.h> (via io-sock/types_fbsd.h), so `bool` is taken. The typedef is skipped when "
            "stdbool's bool is visible. Note: bool is then _Bool, not unsigned int, in those files.",
            "".join(lines))


def prctl_to_setname(text: str) -> str | None:
    """Rewrite prctl(PR_SET_NAME, x) calls, only if those are the file's only prctl uses."""
    calls = list(re.finditer(r"\bprctl\s*\(\s*PR_SET_NAME\s*,", text))
    if not calls or len(re.findall(r"\bprctl\s*\(", _strip_comments(text))) != len(calls):
        return None
    out, last = [], 0
    for m in calls:
        start = m.end()
        depth, i = 1, start
        while i < len(text) and depth:
            depth += {"(": 1, ")": -1}.get(text[i], 0)
            i += 1
        if depth:
            return None
        arg = text[start:i - 1].strip()
        arg = re.sub(r"\s*,\s*0\s*,\s*0\s*,\s*0\s*$", "", arg)  # prctl's unused trailing arguments
        arg = re.sub(r"^\(\s*(?:unsigned\s+)?long\s*\)\s*", "", arg)  # prctl's (unsigned long) cast
        if "," in re.sub(r"\([^()]*\)", "", arg):
            return None
        out.append(text[last:m.start()] + f"pthread_setname_np(pthread_self(), {arg})")
        last = i
    new = guard_include("".join(out) + text[last:], "sys/prctl.h", "#include <pthread.h>\n")
    return new


def renamed_call(d: Diagnostic, src: Path, rel: str):
    """FreeBSD's pthread_set_name_np(tid, name) is QNX's pthread_setname_np(tid, name)."""
    if d.symbol != "pthread_set_name_np":
        return None
    text = _read(src, rel)
    new = re.sub(r"\bpthread_set_name_np\s*\(", "pthread_setname_np(", text)
    return ("pthread-setname", "pthread_set_name_np() is FreeBSD's spelling; QNX 8.0 has "
            "pthread_setname_np(pthread_t, const char *) in <pthread.h>, same argument order.", new)


def one_arg_setname(d: Diagnostic, src: Path, rel: str):
    """macOS's pthread_setname_np(name) takes one argument; QNX's (like Linux's) takes the thread first."""
    if not re.search(r"too few arguments to function .pthread_setname_np", d.message):
        return None
    lines = _read(src, rel).splitlines(keepends=True)
    i = d.line - 1
    if not 0 <= i < len(lines):
        return None
    new_line, n = re.subn(r"\bpthread_setname_np\s*\(\s*(?!pthread_self\b)", "pthread_setname_np(pthread_self(), ",
                          lines[i], count=1)
    if not n:
        return None
    lines[i] = new_line
    return ("pthread-setname-args", "This call uses the one-argument macOS form pthread_setname_np(name). QNX "
            "8.0's is pthread_setname_np(pthread_t tid, const char *name), so the calling thread is passed "
            "explicitly.", "".join(lines))


def platform_guard(d: Diagnostic, src: Path, rel: str):
    """`#error unsupported platform` at the end of an OS #if chain: let QNX take the BSD/Unix/Linux branch.

    This needs a rebuild to prove it, so the agent applies it alone and reverts it if the error remains or
    new errors appear.
    """
    if not d.message.lstrip().startswith("#error"):
        return None
    lines = _read(src, rel).splitlines(keepends=True)
    depth, branches, start = 0, [], None
    for j in range(min(d.line, len(lines)) - 2, -1, -1):
        ln = lines[j]
        if ENDIF.match(ln):
            depth += 1
        elif IF_LINE.match(ln):
            if depth == 0:
                start = j
                break
            depth -= 1
        elif BRANCH.match(ln) and depth == 0:
            branches.append(j)
    if start is None or not branches:
        return None  # the #error is not in an #else/#elif of a chain
    conds = [start] + sorted(b for b in branches if re.match(r"^\s*#\s*elif\b", lines[b]))
    chain_text = "".join(lines[c] for c in conds)
    if "__QNX__" in chain_text or "__QNXNTO__" in chain_text:
        return None
    for macro in OS_MACROS:
        for c in conds:
            if re.search(rf"\b{macro}\b", lines[c]) and not lines[c].rstrip().endswith("\\"):
                lines[c] = _add_qnx(lines[c])
                return ("qnx-platform-guard", f"{rel} stops with #error because no branch of its OS check "
                        f"matches QNX. QNX 8.0 is POSIX with a FreeBSD-derived network stack, so it joins the "
                        f"{macro} branch. Checked by rebuilding; reverted if it does not help.", "".join(lines))
    return None


def _add_qnx(line: str) -> str:
    body = line.rstrip("\n")
    comment = ""
    if (k := body.find("/*")) >= 0 or (k := body.find("//")) >= 0:
        body, comment = body[:k].rstrip(), " " + body[k:]
    if (m := re.match(r"^(\s*#\s*)ifdef\s+(\w+)\s*$", body)):
        body = f"{m[1]}if defined({m[2]}) || defined(__QNX__)"
    else:
        body = re.sub(r"^(\s*#\s*(?:el)?if)\s+(.*)$", r"\1 (\2) || defined(__QNX__)", body)
    return body + comment + "\n"


def tree_ignores_sigpipe(src: Path) -> bool:
    """True if the library already sets SIGPIPE to SIG_IGN somewhere (then MSG_NOSIGNAL=0 is safe)."""
    for p in src.rglob("*"):
        if p.suffix in (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp") and p.is_file() and ".git" not in p.parts:
            t = p.read_text(encoding="utf-8", errors="ignore")
            if re.search(r"SIGPIPE\s*,\s*SIG_IGN|SIG_IGN.{0,80}SIGPIPE", t, re.S):
                return True
    return False


def hint(d: Diagnostic) -> str:
    """A QNX-specific hint for the model (or the person) when no rule applies."""
    if d.kind == "missing_header":
        if d.header.startswith("linux/"):
            return f"<{d.header}> is a Linux kernel header and does not exist on QNX"
        return LINUX_HEADERS.get(d.header, (None, ""))[1]
    if d.symbol in REMOVED:
        return REMOVED[d.symbol]
    if d.symbol == "MSG_NOSIGNAL":
        return ("io-sock is ported from FreeBSD 14.3: if MSG_NOSIGNAL is not visible, set SO_NOSIGPIPE on the "
                "socket with setsockopt(), or ignore SIGPIPE")
    if d.symbol in ("SOCK_CLOEXEC", "SOCK_NONBLOCK"):
        return "set O_CLOEXEC / O_NONBLOCK with fcntl() after socket() if the flag is not visible"
    return ""
