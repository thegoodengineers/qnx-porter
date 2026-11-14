"""When a test crashes on the QNX target: fetch its core dump, read the backtrace, and fix what is mechanical.

mkqnximage images run QNX's `dumper`, which writes `<binary>.core` to /data/var/dumper. We copy each new core
to the host and read it with the SDP's own gdb (x86_64-nto-qnx8.0.0-gdb), using the QNX target libraries.

The one crash we fix automatically is glibc-only behaviour: `printf("%s", NULL)`. C leaves it undefined;
glibc prints "(null)", QNX's libc faults in strlen. Found in json-c's and libconfig's own tests, whose expected
output even contains "(null)".
"""
import re
import subprocess
from pathlib import Path

from .target import SSH_OPTS, Target

CORE_DIRS = ["/data/var/dumper", "/var/dumps"]
PRINTF_FMT_ARG = {"printf": 0, "fprintf": 1, "sprintf": 1, "dprintf": 1, "asprintf": 1, "snprintf": 2}
# Greedy up to the last ") at file:line": arguments can contain strings with parentheses in them.
FRAME = re.compile(r"^#\d+\s+(?:0x[0-9a-f]+ in )?(?P<func>[\w.:~<>]+) \(.*\)(?: at (?P<path>\S+):(?P<line>\d+))?\s*$",
                   re.M)
HELPER = ('/* qnx-porter: glibc prints "(null)" for a NULL %s argument; QNX\'s libc faults (it is undefined C). */\n'
          'static const char *qnx_porter_str(const char *s) { return s ? s : "(null)"; }\n')


def gdb_name(triplet: str) -> str:
    """x86_64-pc-nto-qnx8.0.0 -> x86_64-nto-qnx8.0.0-gdb (the SDP's name for its debugger)."""
    return re.sub(r"-(pc|unknown)-", "-", triplet) + "-gdb"


def clear_cores(t: Target) -> None:
    t.ssh("rm -f " + " ".join(f"{d}/*.core" for d in CORE_DIRS), capture_output=True, timeout=60)


def collect(t: Target, build: Path, env: dict, triplet: str, dest: Path) -> list[dict]:
    """Every core the tests left on the target: [{binary, core, backtrace}] (backtrace '' if no binary)."""
    r = t.ssh("ls " + " ".join(f"{d}/*.core" for d in CORE_DIRS) + " 2>/dev/null", capture_output=True,
              text=True, timeout=60)
    out = []
    for remote in r.stdout.split():
        name = Path(remote).name.removesuffix(".core")
        dest.mkdir(parents=True, exist_ok=True)
        local = dest / Path(remote).name
        subprocess.run(["scp", "-q", *SSH_OPTS, "-P", str(t.port), f"{t.host}:{remote}", str(local)],
                       capture_output=True, timeout=300)
        binaries = [p for p in build.rglob(name) if p.is_file() and p.stat().st_mode & 0o111]
        bt = backtrace(env, triplet, binaries[0], local) if binaries and local.exists() else ""
        out.append({"binary": str(binaries[0]) if binaries else name, "core": str(local), "backtrace": bt})
    return out


def backtrace(env: dict, triplet: str, binary: Path, core: Path) -> str:
    target = env.get("QNX_TARGET", "")
    arch = "x86_64" if triplet.startswith("x86_64") else "aarch64le"
    libs = f"{target}/{arch}/lib:{target}/{arch}/usr/lib"
    gdb = f"{env['QNX_HOST'].rstrip('/')}/usr/bin/{gdb_name(triplet)}"
    r = subprocess.run([gdb, "-q", "-batch", "-ex", f"set solib-search-path {libs}", "-ex", "bt 24",
                        str(binary), str(core)], capture_output=True, text=True, errors="replace", env=env,
                       timeout=300)
    return "\n".join(ln for ln in r.stdout.splitlines() if ln.startswith(("#", "Program terminated", "Core was")))


def frames(bt: str) -> list[tuple[str, str, int]]:
    seen, out = set(), []
    for m in FRAME.finditer(bt):
        key = m.group(0).split()[0]
        if key in seen:  # gdb prints frame #0 twice
            continue
        seen.add(key)
        out.append((m["func"], m["path"] or "", int(m["line"] or 0)))
    return out


def printf_null(bt: str, src: Path, in_tree) -> tuple[str, str, str] | None:
    """(rel path, reason, new text) if the crash is a NULL %s in a printf-family call in the library's code."""
    fr = frames(bt)
    if not fr or not fr[0][0].endswith(("strlen", "strnlen")):  # aarch64 libc: __generic_strlen
        return None
    for i, (func, _, _) in enumerate(fr[:6]):
        if func in PRINTF_FMT_ARG:
            caller = next(((p, ln) for _, p, ln in fr[i + 1:] if p and in_tree(src, p)), None)
            if not caller:
                return None
            rel = in_tree(src, caller[0])
            new = wrap_string_args(src / rel, func, caller[1])
            if new is None:
                return None
            return rel, (f"Crash on QNX: {func}() at {rel}:{caller[1]} formats a NULL pointer with %s (backtrace: "
                         f"strlen <- {func}). glibc prints \"(null)\" for that, QNX's libc faults; C leaves it "
                         "undefined. Each %s argument of that call now goes through qnx_porter_str(), which "
                         "prints \"(null)\" like glibc."), new
    return None


def deep_recursion(bt: str) -> str | None:
    """The function, if at least 8 frames of the (24-frame) backtrace are one function calling itself.

    24, not 12: on aarch64 QNX's malloc alone takes 5 frames (cJSON v1.7.19 misc_tests left only 6 recursive
    frames in a 12-frame backtrace, so the rule did not fire there while it did on x86_64).

    That is a stack overflow on QNX more often than on Linux: a QNX process's main thread gets about 464 KiB of
    stack unless it is linked with `qcc -N` (scripts/stack_probe.c measured 464 KiB by default and 7472 KiB with
    -N8M on the x86_64 target), where a Linux main thread usually has 8 MiB (ulimit -s 8192).
    """
    names = [f for f, _, _ in frames(bt)]
    top = max(set(names), key=names.count) if names else None
    return top if top and names.count(top) >= 8 else None


def _call_span(text: str, start: int) -> int | None:
    """Index just past the ')' that closes the '(' at text[start], skipping strings and chars."""
    depth, i, quote = 0, start, ""
    while i < len(text):
        c = text[i]
        if quote:
            if c == "\\":
                i += 1
            elif c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return None


def _split_args(inner: str) -> list[str]:
    args, depth, quote, cur, i = [], 0, "", "", 0
    while i < len(inner):
        c = inner[i]
        cur += c
        if quote:
            if c == "\\" and i + 1 < len(inner):
                cur += inner[i + 1]
                i += 1
            elif c == quote:
                quote = ""
        elif c in "\"'":
            quote = c
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == "," and depth == 0:
            args.append(cur[:-1])
            cur = ""
        i += 1
    args.append(cur)
    return args


SPEC = re.compile(r"%[-+ #0']*(\*|\d+)?(?:\.(\*|\d+))?(?:hh|h|ll|l|j|z|t|L)?([diouxXeEfFgGaAcspn%])")


def string_arg_positions(fmt: str) -> list[int]:
    """Which variadic arguments (0-based) a printf format string uses for %s."""
    pos, out = 0, []
    for m in SPEC.finditer(fmt):
        if m[3] == "%":
            continue
        pos += (m[1] == "*") + (m[2] == "*")
        if m[3] == "s":
            out.append(pos)
        pos += 1
    return out


def wrap_string_args(path: Path, func: str, line: int) -> str | None:
    text = path.read_text(encoding="utf-8", errors="surrogateescape")
    lines = text.splitlines(keepends=True)
    offset = sum(len(x) for x in lines[:max(line - 6, 0)])
    window_end = sum(len(x) for x in lines[:line])
    calls = [m for m in re.finditer(rf"\b{func}\s*\(", text[offset:window_end])]
    if not calls:
        return None
    start = offset + calls[-1].end() - 1  # the call nearest to the crash line
    end = _call_span(text, start)
    if end is None:
        return None
    args = _split_args(text[start + 1:end - 1])
    k = PRINTF_FMT_ARG[func]
    if len(args) <= k:
        return None
    literals = re.findall(r'"((?:[^"\\]|\\.)*)"', args[k])
    if not literals or re.sub(r'"((?:[^"\\]|\\.)*)"|\s', "", args[k]):
        return None  # the format is not a plain string literal: not mechanical
    changed = False
    for p in string_arg_positions("".join(literals)):
        j = k + 1 + p
        if j < len(args) and "qnx_porter_str(" not in args[j] and not args[j].strip().startswith('"'):
            lead = args[j][:len(args[j]) - len(args[j].lstrip())]
            args[j] = f"{lead}qnx_porter_str({args[j].strip()})"
            changed = True
    if not changed:
        return None
    new = text[:start + 1] + ",".join(args) + text[end - 1:]
    if "qnx_porter_str(const char *s)" not in new:
        new = _insert_helper(new)
    return new


def _insert_helper(text: str) -> str:
    lines = text.splitlines(keepends=True)
    depth, depths = 0, []  # #if nesting before each line
    for ln in lines:
        depths.append(depth)
        depth += 1 if re.match(r"\s*#\s*if", ln) else -1 if re.match(r"\s*#\s*endif\b", ln) else 0
    incs = [i for i, ln in enumerate(lines) if re.match(r"\s*#\s*include\b", ln)]
    at = incs[-1] + 1 if incs else 0
    # The last include can sit in a platform branch (tinyxml2's xmltest.cpp: `#else` of `_MSC_VER`); put the
    # helper after that branch's #endif, at the shallowest include depth (inside an include guard, not past it).
    base = min((depths[i] for i in incs), default=0)
    while at < len(lines) and depths[at] > base:
        at += 1
    return "".join(lines[:at] + ["\n", HELPER] + lines[at:])
