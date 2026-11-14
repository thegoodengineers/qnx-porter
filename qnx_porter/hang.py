"""Hang diagnosis on the QNX target: when a test is about to be killed at its time limit, record what it is doing.

A watcher started beside each test sleeps until LEAD seconds before the limit. If the test is still running then,
it records, for every process whose executable is under the port's trees:
  * `pidin -F "%a %b %N %J %B %K"`: each thread's state, what it is blocked on, and its last kernel call
    (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/p/pidin.html);
  * a TRACE_SECONDS kernel trace with `tracelogger -s` (the image runs the instrumented procnto-smp-instr)
    (https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/tracelogger.html).
The trace is read on the host with the SDP's `traceprinter`
(https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/traceprinter.html) and summarised
per thread: how often it ran and which kernel calls it made in the window. A thread that made no kernel call is
waiting (its pidin state says on what); a thread with thousands is spinning.
The watcher writes to a file, never to the ssh session, so a test that finishes is not slowed down.
"""
import os
import re
import shlex
import subprocess
from collections import Counter
from pathlib import Path

LEAD = 8           # seconds before the time limit at which the snapshot is taken
TRACE_SECONDS = 2  # length of the kernel trace
MIN_LIMIT = 20     # tests with a shorter limit get no watcher
MARK = "### qnx-porter hang snapshot"
PIDIN_FORMAT = "%a %b %N %J %B %K"
EVENT = re.compile(r"^t:0x[0-9a-f]+ CPU:(\d+) (\w+)\s*:(\S+)\s*(.*)$")
WHO = re.compile(r"pid:(\d+) tid:(\d+)")


def watcher(diag: str, work: str, limit: int) -> str:
    """Background shell that, LEAD s before `limit`, snapshots the test's processes into <diag>.txt/.kev."""
    # no `case` here: QNX's sh cannot parse `pattern)` inside $( ) ("syntax error: `;;' unexpected")
    pids = (f'for d in /proc/[0-9]*; do e=$(cat "$d/exefile" 2>/dev/null) || continue; '
            f'[ "${{e#*{shlex.quote(work)}}}" != "$e" ] && echo "${{d#/proc/}}"; done')
    delay = limit - LEAD
    # `exec` redirects inside the subshell: with `( ... ) >/dev/null &`, QNX's sh keeps copies of the ssh
    # session's descriptors that the watcher's sleep inherits, and every test's ssh then waited for the watcher.
    return (f'( exec </dev/null >/dev/null 2>&1; sleep {delay}; {{ echo "{MARK}, {delay} s after the start: pidin, then tracelogger -s {TRACE_SECONDS}"; '
            f'for p in $({pids}); do pidin -p "$p" -F "{PIDIN_FORMAT}"; done; }} > {diag}.txt 2>&1; '
            f'tracelogger -s {TRACE_SECONDS} -f {diag}.kev ) & w=$!; ')


def epilogue(diag: str) -> str:
    """After the test: stop the watcher; if the test was killed (137), print the snapshot."""
    return (f'kill $w 2>/dev/null; if [ $rc = 137 ] && [ -s {diag}.txt ]; then cat {diag}.txt; '
            f'else rm -f {diag}.txt {diag}.kev; fi; exit $rc')


def snapshot_pids(out: str) -> set[int]:
    """The pids pidin listed in the snapshot part of a test's output."""
    part = out.split(MARK, 1)[1] if MARK in out else ""
    return {int(m[1]) for m in re.finditer(r"^\s*(\d+)\s+\d+\s", part, re.M)}


def summary(trace: str, pids: set[int]) -> str:
    """Per thread of `pids`: times it ran and its kernel calls during the trace (traceprinter text)."""
    on_cpu: dict[str, tuple[int, int]] = {}
    runs, calls = Counter(), {}
    for ln in trace.splitlines():
        m = EVENT.match(ln)
        if not m:
            continue
        cpu, cls, name, rest = m.groups()
        if cls == "THREAD" and (w := WHO.search(rest)):
            who = (int(w[1]), int(w[2]))
            if name == "THRUNNING":
                on_cpu[cpu] = who
                if who[0] in pids:
                    runs[who] += 1
        elif cls == "KER_CALL" and (who := on_cpu.get(cpu)) and who[0] in pids:
            calls.setdefault(who, Counter())[name.split("/")[0]] += 1
    threads = sorted(set(runs) | set(calls))
    if not threads:
        return f"no thread of pid(s) {', '.join(map(str, sorted(pids))) or '?'} ran during the {TRACE_SECONDS} s trace: all waiting"
    lines = []
    for who in threads:
        c = calls.get(who, Counter())
        top = ", ".join(f"{k} x{v}" for k, v in c.most_common(4))
        lines.append(f"pid {who[0]} tid {who[1]}: ran {runs[who]} time(s), {sum(c.values())} kernel call(s)"
                     + (f" ({top})" if top else ""))
    quiet = sorted(pids - {p for p, _ in threads})
    if quiet:
        lines.append(f"pid(s) {', '.join(map(str, quiet))}: no thread ran during the trace")
    return "\n".join(lines)


def read_trace(kev: bytes, keep: Path) -> str:
    """traceprinter's text for a .kev file (kept at `keep`), or a note if the SDP's traceprinter is not found."""
    keep.write_bytes(kev)
    tp = Path(os.environ.get("QNX_HOST", "")) / "usr" / "bin" / "traceprinter"
    if not kev or not tp.exists():
        return ""
    return subprocess.run([str(tp), "-f", str(keep)], capture_output=True, text=True, errors="replace",
                          timeout=300).stdout
