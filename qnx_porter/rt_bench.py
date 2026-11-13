"""Measure one core call of a ported library on the QNX target, the way a real-time thread would see it.

The harness (BENCH_C) runs the call N times (after WARMUP untimed calls) in a SCHED_FIFO thread at priority
60, timing each call with ClockCycles() (rdtsc on x86_64, CNTVCT_EL0 on aarch64: the SDP's
<x86_64/neutrino.h> and <aarch64/neutrino.h>) and converting with SYSPAGE_ENTRY(qtime)->cycles_per_sec.
It runs three times (RUNS):
  idle             nothing else of ours running;
  loaded           one SCHED_RR priority 10 thread per CPU churning the heap (malloc/memset/free) and caches;
  loaded_isolated  the same load, with the CPUs split by QNX runmasks (ThreadCtl(_NTO_TCTL_RUNMASK)): the
                   measured thread on CPU 0, the load on the others.
The load is lower priority, so it cannot preempt the measured thread; it interferes through shared caches,
memory bandwidth, the allocator's lock and the kernel. Each run prints min / median / p99 / p99.9 / max in
microseconds as one JSON line. max is the worst case seen in that run, not a bound.

SDP 8.0's <sched.h> defines no adaptive-partitioning commands for SchedCtl() (only a query and CPU
on/offline) and the SDP ships no `aps` utility, so runmask isolation is how this benchmark separates the
real-time work from the load.

The call for each library is in bench/specs.yaml: a few lines of C written against the library's public API.
"""
import json
import math
import re
import shlex
import subprocess
from pathlib import Path

from .target import Target

PRIORITY, LOAD_PRIORITY, WARMUP = 60, 10, 200
RUNS = {"idle": "0 0", "loaded": "-1 0", "loaded_isolated": "-1 1"}  # argv[2] load threads (-1: one per CPU), argv[3] isolate
STATS = ("min", "median", "p99", "p999", "max")

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
static int isolate;
static unsigned ncpu;
@GLOBALS@

static int setup(void) { @SETUP@ return 0; }
static int one_call(void) { @CALL@ }

static uintptr_t all_cpus(void) { return ncpu >= 8 * sizeof(uintptr_t) ? ~(uintptr_t)0 : ((uintptr_t)1 << ncpu) - 1; }

static void *load(void *arg)
{
    struct sched_param p = { .sched_priority = @LOAD_PRIORITY@ };
    unsigned x = (unsigned)(uintptr_t)arg + 1;
    pthread_setschedparam(pthread_self(), SCHED_RR, &p);
    if (isolate)                           /* load on every CPU except 0 */
        ThreadCtl(_NTO_TCTL_RUNMASK, (void *)(all_cpus() & ~(uintptr_t)1));
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
    struct sched_param p = { .sched_priority = @PRIORITY@ };
    int prio_rc = pthread_setschedparam(pthread_self(), SCHED_FIFO, &p), mask_rc = 0;
    ncpu = (unsigned)sysconf(_SC_NPROCESSORS_ONLN);
    isolate = argc > 3 && atoi(argv[3]) == 1 && ncpu > 1;   /* nothing to split on one CPU */
    if (n < 1) { fprintf(stderr, "n must be positive\n"); return 2; }
    if (nload < 0)
        nload = (int)ncpu;
    if (isolate)                           /* the measured thread alone on CPU 0 */
        mask_rc = ThreadCtl(_NTO_TCTL_RUNMASK, (void *)(uintptr_t)1);
    pthread_t t[64];
    uint64_t *d = malloc(sizeof(uint64_t) * (size_t)n);
    for (size_t i = 0; i < sizeof in; i++)
        in[i] = (unsigned char)("qnx-porter benchmark input "[i % 27] ^ (i / 97));
    if (!d || setup() != 0) { fprintf(stderr, "setup failed\n"); return 2; }
    int started = 0;
    for (int i = 0; i < nload && i < 64; i++)
        started += pthread_create(&t[started], NULL, load, (void *)(uintptr_t)i) == 0;
    usleep(200000);                        /* let the load threads get going */
    for (int i = 0; i < @WARMUP@; i++)
        if (one_call() != 0) { fprintf(stderr, "call failed\n"); return 3; }
    for (int i = 0; i < n; i++) {
        uint64_t c0 = ClockCycles();
        int rc = one_call();
        d[i] = ClockCycles() - c0;
        if (rc != 0) { fprintf(stderr, "call failed at %d\n", i); return 3; }
    }
    stop = 1;
    for (int i = 0; i < started; i++)
        pthread_join(t[i], NULL);
    qsort(d, (size_t)n, sizeof d[0], cmp);
    uint64_t cps = SYSPAGE_ENTRY(qtime)->cycles_per_sec;
    double us = 1e6 / (double)cps;
    printf("{\"n\": %d, \"warmup\": %d, \"load_threads\": %d, \"cpus\": %u, \"isolated\": %d, \"runmask_rc\": %d, "
           "\"policy\": \"SCHED_FIFO\", \"priority\": %d, \"setschedparam_rc\": %d, "
           "\"cycles_per_sec\": %llu, \"clockcycles_global\": %d, \"min_us\": %.3f, \"median_us\": %.3f, "
           "\"p99_us\": %.3f, \"p999_us\": %.3f, \"max_us\": %.3f}\n",
           n, @WARMUP@, started, ncpu, isolate, mask_rc, p.sched_priority, prio_rc, (unsigned long long)cps,
           (SYSPAGE_ENTRY(qtime)->flags & QTIME_FLAG_GLOBAL_CLOCKCYCLES) != 0,
           d[0] * us, d[n / 2] * us, d[(size_t)n * 99 / 100] * us, d[(size_t)n * 999 / 1000] * us, d[n - 1] * us);
    return 0;
}
"""


def source(spec: dict) -> str:
    return (BENCH_C.replace("@INCLUDES@", spec.get("includes", ""))
            .replace("@GLOBALS@", spec.get("globals", ""))
            .replace("@SETUP@", spec.get("setup", ""))
            .replace("@CALL@", spec["call"])
            .replace("@PRIORITY@", str(PRIORITY)).replace("@LOAD_PRIORITY@", str(LOAD_PRIORITY))
            .replace("@WARMUP@", str(WARMUP)))


def compile_bench(spec: dict, src: Path, bdir: Path, out: Path, env: dict, qcc_target: str) -> tuple[bool, str]:
    """Build the harness with qcc against the library's own build tree (its static archives)."""
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


def run_bench(t: Target, binary: Path, name: str, n: int) -> dict:
    """Copy the harness to the target (cat over ssh, no scp/sftp needed); run it once per RUNS entry."""
    remote = f"{t.root}/bench/{name}"
    with binary.open("rb") as f:
        t.ssh(f"mkdir -p {shlex.quote(t.root)}/bench && cat > {shlex.quote(remote)} && chmod 755 "
              f"{shlex.quote(remote)}", stdin=f, capture_output=True, check=True, timeout=300)
    res = {}
    for label, args in RUNS.items():
        r = t.ssh(f"timeout -s KILL 600 {shlex.quote(remote)} {n} {args}", capture_output=True, text=True,
                  timeout=660)
        m = re.search(r"\{.*\}", r.stdout)
        res[label] = json.loads(m.group(0)) if (r.returncode == 0 and m) else \
            {"error": f"exit {r.returncode}: {(r.stdout + r.stderr).strip()[-300:]}"}
    return res


def rt_score(static_score: int, runs: dict | None) -> int | None:
    """The static score, minus up to 30 for jitter: 10 points per doubling of p99-under-load over idle median.

    A heuristic for ranking, not a certification; on QEMU the ratio includes the emulator's own jitter.
    """
    runs = runs or {}
    if "p99_us" not in runs.get("loaded", {}) or "median_us" not in runs.get("idle", {}):
        return None
    ratio = max(runs["loaded"]["p99_us"] / max(runs["idle"]["median_us"], 1e-3), 1.0)
    return max(0, round(static_score - min(30.0, 10 * math.log2(ratio))))
