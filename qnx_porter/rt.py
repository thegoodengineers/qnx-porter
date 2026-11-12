"""Real-time readiness: what in a library's own code can make a real-time thread wait, and how long it takes.

Part 1, `scan()`: a static scan of the library's sources (tests, examples, fuzzers and benchmarks excluded)
for calls a real-time designer has to know about: heap allocation, blocking I/O, sleeps, process creation,
signals, threads and mutexes. It reports counts and the first places found; it cannot tell which of them
sit on a hot path, and says so.

Part 2 (rt_bench.py): latency of one core call per library, measured on the QNX target in a SCHED_FIFO
thread, with and without competing load.
"""
import re
from pathlib import Path

SKIP_DIRS = {"test", "tests", "testing", "example", "examples", "fuzz", "fuzzing", "bench", "benchmark",
             "benchmarks", "doc", "docs", "demo", "demos", "contrib", "third_party", "thirdparty", "tools",
             "programs", "apps", "samples", "sample", "unittest", "unittests", ".git", "build", "cmake",
             "misc", "scripts", "util", "utils"}
EXTS = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh", ".inl"}
NOT_MEMBER = r"(?<![\w.>])"  # not foo.read( or foo->read( or my_read(

CATEGORIES = {
    "heap": (r"\b(?:malloc|calloc|realloc|free|strdup|strndup|aligned_alloc|posix_memalign)\s*\(|"
             r"\bnew\s+[A-Za-z_:<]|\bdelete\s*(?:\[\s*\])?\s*[A-Za-z_(]",
             "heap allocation: time is not bounded and can fail; preallocate or use a pool on hot paths"),
    "blocking_io": (NOT_MEMBER + r"(?:fopen|fread|fwrite|fgets|fputs|fprintf|printf|puts|open|read|write|recv|"
                    r"recvfrom|send|sendto|accept|connect|select|poll|getaddrinfo|fsync)\s*\(",
                    "blocking I/O: the caller waits on a device, a file system or the network"),
    "sleep": (NOT_MEMBER + r"(?:sleep|usleep|nanosleep|clock_nanosleep)\s*\(",
              "sleeps: fine in a worker thread, a bug in a control loop"),
    "process": (NOT_MEMBER + r"(?:fork|vfork|system|popen|execl|execlp|execle|execv|execvp|execve|"
                r"posix_spawn|posix_spawnp)\s*\(",
                "process creation: slow, and fork copies the address space"),
    "signals": (NOT_MEMBER + r"(?:signal|sigaction|raise|kill|alarm|setitimer)\s*\(",
                "signals: asynchronous control flow; QNX prefers pulses for event delivery"),
    "threads": (r"\bpthread_create\s*\(|\bstd::thread\b",
                "threads the library creates itself: their priority is not the caller's"),
    "mutexes": (r"\bpthread_mutex_lock\s*\(|\bstd::(?:mutex|lock_guard|unique_lock|scoped_lock)\b",
                "locks: on QNX a mutex's default protocol is priority inheritance; check the lock's hold time"),
}
WEIGHTS = {"heap": 20, "blocking_io": 20, "sleep": 10, "process": 20, "signals": 10, "threads": 10, "mutexes": 10}


def _strip(text: str) -> str:
    """Comments and string literals removed, newlines kept so line numbers stay right."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', blank, text, flags=re.S)


def sources(src: Path):
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if p.suffix in EXTS and p.is_file() and not (set(part.lower() for part in rel.parts[:-1]) & SKIP_DIRS) \
                and not rel.name.lower().startswith(("test", "bench", "example", "fuzz")):
            yield p, rel.as_posix()


def scan(src: Path, max_examples: int = 3) -> dict:
    """{category: {"count", "examples": ["file:line"], "why"}}, plus files scanned and a 0-100 score."""
    found = {k: {"count": 0, "examples": [], "why": why} for k, (_, why) in CATEGORIES.items()}
    files = lines = 0
    for p, rel in sources(src):
        text = _strip(p.read_text(encoding="utf-8", errors="replace"))
        files += 1
        lines += text.count("\n") + 1
        for k, (pattern, _) in CATEGORIES.items():
            for m in re.finditer(pattern, text):
                found[k]["count"] += 1
                if len(found[k]["examples"]) < max_examples:
                    found[k]["examples"].append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}")
    return {"files": files, "lines": lines, "hazards": found, "static_score": static_score(found),
            "limits": "Library-wide counts. A static scan cannot tell which calls are on a hot path; "
                      "check the examples against the API you call."}


def static_score(found: dict) -> int:
    """100 minus a weight for each kind of hazard present (counts above zero), floored at 0.

    Deliberately coarse: presence, not count, because one malloc on a hot path matters as much as fifty.
    """
    return max(0, 100 - sum(w for k, w in WEIGHTS.items() if found[k]["count"]))
