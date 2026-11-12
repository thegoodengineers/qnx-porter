"""Measure one core call of a ported library on the QNX target, the way a real-time thread would see it.

The harness (BENCH_C) runs the call N times in a SCHED_FIFO thread at priority 60, timing each call with
ClockCycles() (the TSC on x86, CNTVCT_EL0 on ARM; QNX C Library Reference) and converting with
SYSPAGE_ENTRY(qtime)->cycles_per_sec. It runs twice: idle, and with one load thread per CPU at priority 10
churning the heap and the caches. It prints min / median / p99 / max in microseconds as JSON.

The call for each library is in bench/specs.yaml: a few lines of C written against the library's public API.
"""
import json
import re
import shlex
import subprocess
from pathlib import Path

from .target import SSH_OPTS, Target

BENCH_C = r"""/* qnx-porter real-time benchmark: generated, see qnx_porter/rt_bench.py */
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/neutrino.h>
#include <sys/syspage.h>
#include <unistd.h>
@INCLUDES@

static unsigned char in[1024], out[4096];
static volatile int stop;
@GLOBALS@

static int setup(void) { @SETUP@ return 0; }
static int one_call(void) { @CALL@ }

static void *load(void *arg)
{
    struct sched_param p = { .sched_priority = 10 };
    unsigned x = (unsigned)(uintptr_t)arg + 1;
    pthread_setschedparam(pthread_self(), SCHED_RR, &p);
    while (!stop) {                        /* heap churn and cache pressure */
        size_t n = 64 + x % 8192;
        unsigned char *m = malloc(n);
        x = x * 1103515245u + 12345u;
        if (m) { memset(m, (int)x, n); free(m); }
    }
    return NULL;
}

static int cmp(const void *a, const void *b)
{
    uint64_t x = *(const uint64_t *)a, y = *(const uint64_t *)b;
    return x < y ? -1 : x > y;
}

int main(int argc, char **argv)
{
    int n = argc > 1 ? atoi(argv[1]) : 10000, nload = argc > 2 ? atoi(argv[2]) : 0;
    struct sched_param p = { .sched_priority = 60 };
    int prio_rc = pthread_setschedparam(pthread_self(), SCHED_FIFO, &p);
    pthread_t t[64];
    uint64_t *d = malloc(sizeof(uint64_t) * (size_t)n);
    for (size_t i = 0; i < sizeof in; i++)
        in[i] = (unsigned char)("qnx-porter benchmark input "[i % 27] ^ (i / 97));
    if (!d || setup() != 0) { fprintf(stderr, "setup failed\n"); return 2; }
    for (int i = 0; i < nload && i < 64; i++)
        pthread_create(&t[i], NULL, load, (void *)(uintptr_t)i);
    usleep(200000);
    for (int i = 0; i < 200; i++)
        if (one_call() != 0) { fprintf(stderr, "call failed\n"); return 3; }
    for (int i = 0; i < n; i++) {
        uint64_t c0 = ClockCycles();
        int rc = one_call();
        d[i] = ClockCycles() - c0;
        if (rc != 0) { fprintf(stderr, "call failed at %d\n", i); return 3; }
    }
    stop = 1;
    for (int i = 0; i < nload && i < 64; i++)
        pthread_join(t[i], NULL);
    qsort(d, (size_t)n, sizeof d[0], cmp);
    double us = 1e6 / (double)SYSPAGE_ENTRY(qtime)->cycles_per_sec;
    printf("{\"n\": %d, \"load_threads\": %d, \"policy\": \"SCHED_FIFO\", \"priority\": 60, "
           "\"setschedparam_rc\": %d, \"min_us\": %.3f, \"median_us\": %.3f, \"p99_us\": %.3f, "
           "\"max_us\": %.3f}\n", n, nload, prio_rc, d[0] * us, d[n / 2] * us, d[(n * 99) / 100] * us,
           d[n - 1] * us);
    return 0;
}
"""


def source(spec: dict) -> str:
    return (BENCH_C.replace("@INCLUDES@", spec.get("includes", ""))
            .replace("@GLOBALS@", spec.get("globals", ""))
            .replace("@SETUP@", spec.get("setup", ""))
            .replace("@CALL@", spec["call"]))


def compile_bench(spec: dict, src: Path, bdir: Path, out: Path, env: dict, qcc_target: str) -> tuple[bool, str]:
    """Build the harness with qcc against the library's own build tree."""
    out.mkdir(parents=True, exist_ok=True)
    c = out / "bench.c"
    c.write_text(source(spec), encoding="utf-8")
    incs = [f"-I{(src / d) if not d.startswith('build') else (bdir / d.removeprefix('build').lstrip('/'))}"
            for d in spec.get("include_dirs", ["."])]
    libs = sorted(str(p) for p in bdir.rglob("*.a") if "CMakeFiles" not in p.parts and "stubs" not in p.parts)
    cmd = [f"{env['QNX_HOST'].rstrip('/')}/usr/bin/qcc", f"-V{qcc_target}", "-O2", "-std=gnu11",
           *spec.get("cflags", []), *incs, str(c), "-o", str(out / "bench"),
           "-Wl,--start-group", *libs, "-Wl,--end-group", "-lm", "-lsocket"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    (out / "compile.log").write_text("$ " + " ".join(shlex.quote(x) for x in cmd) + "\n" + r.stdout + r.stderr,
                                     encoding="utf-8")
    return r.returncode == 0, r.stderr[-1500:]


def run_bench(t: Target, binary: Path, name: str, n: int = 20000, load_threads: int = 4) -> dict:
    """Copy the harness to the target and run it idle and under load. Returns both result objects."""
    remote = f"{t.root}/bench/{name}"
    t.ssh(f"mkdir -p {shlex.quote(t.root)}/bench", capture_output=True, timeout=60)
    subprocess.run(["scp", "-q", *SSH_OPTS, "-P", str(t.port), str(binary), f"{t.host}:{remote}"],
                   check=True, capture_output=True, timeout=300)
    res = {}
    for label, k in (("idle", 0), ("loaded", load_threads)):
        r = t.ssh(f"timeout -s KILL 300 {shlex.quote(remote)} {n} {k}", capture_output=True, text=True, timeout=360)
        m = re.search(r"\{.*\}", r.stdout)
        res[label] = json.loads(m.group(0)) if (r.returncode == 0 and m) else \
            {"error": f"exit {r.returncode}: {(r.stdout + r.stderr).strip()[-300:]}"}
    return res


def rt_score(static_score: int, bench: dict | None) -> int | None:
    """The static score, minus up to 30 for jitter: 10 points per doubling of p99-under-load over idle median."""
    if not bench or "p99_us" not in bench.get("loaded", {}) or "median_us" not in bench.get("idle", {}):
        return None
    import math
    ratio = max(bench["loaded"]["p99_us"] / max(bench["idle"]["median_us"], 1e-3), 1.0)
    return max(0, round(static_score - min(30.0, 10 * math.log2(ratio))))
