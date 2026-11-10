"""Turn compiler, linker and configure output into structured diagnostics.

qcc in QNX SDP 8.0 drives GCC and GNU ld, so the formats here are GCC's. Builds run with LC_ALL=C
so GCC prints ASCII quotes, but the patterns accept the UTF-8 quotes too.
"""
import re
from dataclasses import dataclass

Q = "['‘’`]"  # any quote GCC or ld may print

GCC_LINE = re.compile(
    r"^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?:(?P<col>\d+):)?\s*"
    r"(?P<sev>fatal error|error|warning|note):\s*(?P<msg>.*)$"
)
MISSING_HEADER = re.compile(r"^(?P<header>\S+): No such file or directory")
INCLUDE_HINT = re.compile(rf"did you forget to {Q}#include <(?P<header>[^>]+)>{Q}"
                          rf"|include {Q}<(?P<header2>[^>]+)>{Q} or provide a declaration")
DEFINED_IN = re.compile(rf"{Q}(?:std::)?(?P<symbol>\w+){Q} is defined in header {Q}<(?P<header>[^>]+)>{Q}")
IMPLICIT = re.compile(rf"implicit declaration of function {Q}(?P<symbol>\w+){Q}")
UNDECLARED = re.compile(
    rf"{Q}(?:std::)?(?P<symbol>\w+){Q} (?:undeclared|was not declared in this scope|has not been declared)"
    rf"|unknown type name {Q}(?P<type>\w+){Q}"
    rf"|{Q}(?P<member>\w+){Q} is not a member of {Q}std{Q}"
)
WERROR = re.compile(r"\[-Werror=(?P<flag>[\w=+-]+)\]\s*$")
UNDEFINED_REF = re.compile(rf"undefined reference to {Q}(?P<symbol>[^'’`]+){Q}")
MULTIPLE_DEF = re.compile(rf"multiple definition of {Q}(?P<symbol>[^'\u2019`]+){Q}")
MISSING_LIB = re.compile(r"cannot find -l(?P<lib>[\w+.-]+)")
CMAKE_ERROR = re.compile(r"^CMake Error(?: at (?P<file>[^:]+):(?P<line>\d+))?")
CONFIGURE_ERROR = re.compile(r"^configure: error: (?P<msg>.*)$")
MESON_ERROR = re.compile(r"^(?P<file>[^\s:][^:]*):(?P<line>\d+):(?P<col>\d+): ERROR: (?P<msg>.*)$")


@dataclass
class Diagnostic:
    kind: str  # missing_header, implicit_decl, undeclared, werror, undefined_ref, multiple_def,
    #            missing_lib, hash_error, cmake_error, configure_error, error
    message: str
    file: str = ""
    line: int = 0
    symbol: str = ""
    header: str = ""  # a header the compiler itself suggested, or the missing one
    flag: str = ""
    raw: str = ""

    def key(self):
        return (self.kind, self.file, self.line, self.symbol, self.header, self.flag, self.message)


def parse(log: str) -> list[Diagnostic]:
    """Every error in a build log, in order, without duplicates. Notes are folded into the error above."""
    out: list[Diagnostic] = []
    seen = set()

    def add(d: Diagnostic):
        if d.key() not in seen:
            seen.add(d.key())
            out.append(d)

    last: Diagnostic | None = None
    lines = log.splitlines()
    for i, raw in enumerate(lines):
        line = raw.rstrip()
        m = GCC_LINE.match(line)
        if m:
            sev, msg = m["sev"], m["msg"]
            where = dict(file=m["file"], line=int(m["line"]), raw=line)
            if sev == "note":
                h = INCLUDE_HINT.search(msg) or DEFINED_IN.search(msg)
                if h and last is not None and not last.header and last.kind in ("implicit_decl", "undeclared"):
                    last.header = h["header"] or h.groupdict().get("header2") or ""
                continue
            if sev == "warning" and not WERROR.search(msg):
                last = None
                continue
            d = _classify(msg, where)
            add(d)
            last = d
            continue
        if (m := UNDEFINED_REF.search(line)):
            add(Diagnostic("undefined_ref", line.strip(), symbol=m["symbol"], raw=line))
        elif (m := MULTIPLE_DEF.search(line)):
            add(Diagnostic("multiple_def", line.strip(), symbol=m["symbol"], raw=line))
        elif (m := MISSING_LIB.search(line)):
            add(Diagnostic("missing_lib", line.strip(), symbol=m["lib"], raw=line))
        elif (m := CMAKE_ERROR.match(line)):
            body = " ".join(x.strip() for x in lines[i + 1:i + 6] if x.strip())
            add(Diagnostic("cmake_error", body or line, file=m["file"] or "", line=int(m["line"] or 0), raw=line))
        elif (m := CONFIGURE_ERROR.match(line)):
            add(Diagnostic("configure_error", m["msg"], raw=line))
        elif (m := MESON_ERROR.match(line)):
            add(Diagnostic("error", m["msg"], file=m["file"], line=int(m["line"]), raw=line))
    return out


def _classify(msg: str, where: dict) -> Diagnostic:
    if (m := MISSING_HEADER.match(msg)):
        return Diagnostic("missing_header", msg, header=m["header"], **where)
    if msg.startswith("#error"):
        return Diagnostic("hash_error", msg, **where)
    if (m := WERROR.search(msg)):
        if (i := IMPLICIT.search(msg)):
            return Diagnostic("implicit_decl", msg, symbol=i["symbol"], flag=m["flag"], **where)
        return Diagnostic("werror", msg, flag=m["flag"], **where)
    if (m := IMPLICIT.search(msg)):
        return Diagnostic("implicit_decl", msg, symbol=m["symbol"], **where)
    if (m := UNDECLARED.search(msg)):
        return Diagnostic("undeclared", msg, symbol=m["symbol"] or m["type"] or m["member"], **where)
    return Diagnostic("error", msg, **where)
