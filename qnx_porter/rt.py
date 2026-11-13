"""Real-time readiness: what in a library's own code can make a real-time thread wait, and how long it takes.

Part 1, `scan()`: a static scan of the library's sources (tests, examples, fuzzers, benchmarks and tools
excluded) for calls a real-time designer has to know about: heap allocation, blocking I/O, sleeps, process
creation, signals, threads and locks. Comments and string literals are blanked first. It reports counts and
the first places found; it cannot tell which of them sit on a hot path, and says so.

Part 2 (rt_bench.py): latency of one core call per library, measured on the QNX target in a SCHED_FIFO
thread, idle, under load, and under load with runmask isolation.
"""
import re
from pathlib import Path

SKIP_DIRS = {"test", "tests", "testing", "example", "examples", "fuzz", "fuzzing", "bench", "benchmark",
             "benchmarks", "doc", "docs", "demo", "demos", "contrib", "third_party", "thirdparty", "tools",
             "programs", "apps", "samples", "sample", "unittest", "unittests", ".git", "build", "cmake",
             "misc", "scripts", "util", "utils", "cli", "tool"}
SKIP_PREFIXES = ("test", "bench", "example", "fuzz")  # folder names and file stems starting with these
DIR_SUFFIXES = ("test", "tests")  # folder names ending with these (sqlite's mptest/)
FILE_SUFFIXES = ("_test", "_tests", "_demo")  # file stems ending with these (opus_demo.c)
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
    "threads": (r"\bpthread_create\s*\(|\bstd::j?thread\s*(?:\w+\s*)?[({]",  # a thread started, not a type named
                "threads the library creates itself: their priority is not the caller's"),
    "locks": (r"\b(?:pthread_mutex_lock|pthread_rwlock_rdlock|pthread_rwlock_wrlock|pthread_cond_wait|"
              r"pthread_cond_timedwait|sem_wait|mtx_lock|cnd_wait)\s*\(|"
              r"\bstd::(?:lock_guard|unique_lock|scoped_lock|shared_lock|condition_variable(?:_any)?)\b",
              "locks and condition waits: the wait is as long as another thread holds the lock (unbounded "
              "unless its hold time is known); on QNX a mutex's default protocol is priority inheritance"),
}
WEIGHTS = {"heap": 20, "blocking_io": 20, "sleep": 10, "process": 20, "signals": 10, "threads": 10, "locks": 10}


def _strip(text: str) -> str:
    """Comments and string literals removed, newlines kept so line numbers stay right."""
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    return re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])*\'', blank, text, flags=re.S)


def _skipped(name: str, keep: str, folder: bool) -> bool:
    """A folder or file stem that is not the library itself. Names starting with `keep` (the library's own
    name, e.g. Google's `benchmark`) are never skipped."""
    name = name.lower()
    if keep and name.startswith(keep.lower()):
        return False
    return name.startswith(SKIP_PREFIXES) or (name in SKIP_DIRS or name.endswith(DIR_SUFFIXES) if folder
                                              else name.endswith(FILE_SUFFIXES))


def sources(src: Path, keep: str = ""):
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if p.suffix in EXTS and p.is_file() and not _skipped(p.stem, keep, False) \
                and not any(_skipped(part, keep, True) for part in rel.parts[:-1]):
            yield p, rel.as_posix()


def scan(src: Path, max_examples: int = 3, keep: str = "") -> dict:
    """{category: {"count", "examples": ["file:line"], "why"}}, plus files and lines scanned and a 0-100 score."""
    found = {k: {"count": 0, "examples": [], "why": why} for k, (_, why) in CATEGORIES.items()}
    files = lines = 0
    for p, rel in sources(src, keep):
        text = _strip(p.read_text(encoding="utf-8", errors="replace"))
        files += 1
        lines += text.count("\n") + 1
        for k, (pattern, _) in CATEGORIES.items():
            for m in re.finditer(pattern, text):
                found[k]["count"] += 1
                if len(found[k]["examples"]) < max_examples:  # line numbers only for the few we keep
                    found[k]["examples"].append(f"{rel}:{text.count(chr(10), 0, m.start()) + 1}")
    return {"files": files, "lines": lines, "hazards": found, "static_score": static_score(found),
            "limits": "Library-wide counts of direct calls in the library's own sources. A static scan cannot "
                      "tell which calls are on a hot path, and does not see calls hidden behind the library's "
                      "own wrappers or macros; check the examples against the API you call."}


def static_score(found: dict) -> int:
    """100 minus a weight for each kind of hazard present (counts above zero), floored at 0.

    Deliberately coarse: presence, not count, because one malloc on a hot path matters as much as fifty.
    The weights are a judgement, not a measurement.
    """
    return max(0, 100 - sum(w for k, w in WEIGHTS.items() if found[k]["count"]))
