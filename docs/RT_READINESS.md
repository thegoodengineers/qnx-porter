# Real-time readiness report

A library that builds and passes its tests on QNX can still be wrong for a real-time thread: it may allocate,
block, sleep or lock on the path you call. `scripts/rt_report.py` answers two questions per ported library:

1. **What in its own code can make a real-time thread wait?** A static scan of the sources (`qnx_porter/rt.py`).
   Needs no SDP and no target.
2. **How long does one core call take on QNX, and how much worse does it get under load?** A benchmark built with
   `qcc` and run on the QNX target (`qnx_porter/rt_bench.py`, calls in `bench/specs.yaml`).

No latency figure is recorded in this repository yet. `results/rt_scan.csv` is the output of the static scan;
`results/rt.csv` and `results/rt/<arch>/<lib>.json` appear only after a run on a target, and only those files are a
source for any latency number.

## Part 1: static hazard scan

**What is scanned.** The library's own sources in the campaign's work tree, `<ports>/<lib>/work/src`: files
ending `.c .h .cc .cpp .cxx .hpp .hh .inl`. Skipped, because they are not the library a real-time thread links:

- folders named `test tests testing unittest unittests example examples sample samples demo demos fuzz fuzzing
  bench benchmark benchmarks doc docs tools tool cli programs apps contrib third_party thirdparty misc scripts
  util utils build cmake .git`;
- folders and file names starting with `test`, `bench`, `example` or `fuzz`; folders ending with `test` or
  `tests`; files ending with `_test`, `_tests` or `_demo` (for example sqlite's `mptest/`, flac's
  `test_libFLAC/`, opus's `opus_demo.c`);
- except names that start with the library's own name (Google `benchmark` keeps `include/benchmark/`,
  googletest keeps `googletest/`).

Comments and string literals are blanked before matching (newlines kept, so line numbers stay right).

**What it looks for** (regular expressions in `rt.CATEGORIES`; a name preceded by a letter, digit, `_`, `.` or
`->` is not counted, so `my_read(` and `ctx->read(` are not `read(`):

| Category | Matches | Why it matters for a real-time thread |
|---|---|---|
| `heap` | `malloc calloc realloc free strdup strndup aligned_alloc posix_memalign` calls; C++ `new T`, `delete p` | allocation time is not bounded and can fail; preallocate or use a pool on hot paths |
| `blocking_io` | `fopen fread fwrite fgets fputs fprintf printf puts open read write recv recvfrom send sendto accept connect select poll getaddrinfo fsync` calls | the caller waits on a device, a file system or the network |
| `sleep` | `sleep usleep nanosleep clock_nanosleep` | fine in a worker thread, a bug in a control loop |
| `process` | `fork vfork system popen exec* posix_spawn posix_spawnp` | slow; `fork` copies the address space |
| `signals` | `signal sigaction raise kill alarm setitimer` | asynchronous control flow; QNX prefers pulses for event delivery |
| `threads` | `pthread_create(`; `std::thread` / `std::jthread` being constructed (not the type named, e.g. `std::thread::id`) | threads the library starts itself run at a priority the caller did not choose |
| `locks` | `pthread_mutex_lock pthread_rwlock_rdlock pthread_rwlock_wrlock pthread_cond_wait pthread_cond_timedwait sem_wait mtx_lock cnd_wait` calls; `std::lock_guard unique_lock scoped_lock shared_lock condition_variable(_any)` | the wait lasts as long as another thread holds the lock: unbounded unless its hold time is known. On QNX a mutex's default protocol is priority inheritance |

For each category the scan records the count and the first three places (`file:line`), in `results/rt/<arch>/<lib>.json`.

**Static score** (`rt.static_score`): 100 minus a weight for each category present at all (count above zero):
heap 20, blocking_io 20, process 20, sleep 10, signals 10, threads 10, locks 10; floored at 0. Presence, not
count, because one `malloc` on a hot path matters as much as fifty. The weights are a judgement, not a
measurement; the score ranks libraries, it does not certify one.

**Limits of the scan.**
- Counts are library-wide. A static scan cannot tell which calls are on the path you use: zlib's `deflate()`
  allocates in `deflateInit()`, not per call, and the scan cannot see that difference. Read the examples.
- Only direct calls are seen. Allocation behind a library's own wrapper or macro (`sqlite3_malloc`, a
  user-supplied allocator) is counted once at the wrapper, not at every use.
- Command-line programs and debug helpers that live beside the library code, outside the skipped folders, are
  counted (for example flac's `src/flac/` and `src/metaflac/`). `printf` in a debug-only helper counts as I/O.
- Code inside `#if 0` or disabled `#ifdef` branches is counted.

`results/rt_scan.csv` has one row per library: `library, arch, commit` (upstream commit from `report.json`),
`sources` (`scanned` or `absent`), `files, lines`, one count per category, `static_score`.

## Part 2: latency on the QNX target

**Which libraries.** Those with a call in `bench/specs.yaml` (16: json-c, yyjson, cJSON, mbedtls, libsodium,
zlib, lz4, zstd, miniz, xxHash, BLAKE3, cglm, expat, pcre2, msgpack-c, inih) whose `report.json` says
`build_result: built`. Each spec is a few lines of C against the library's public API (`what` says what the
call does, for example "compress 1 KB (default level)"); `call` returns 0 on success.

**Build.** The harness (`rt_bench.BENCH_C` with the spec pasted in) is compiled on the host with
`qcc -V<gcc_ntox86_64|gcc_ntoaarch64le> -O2 -std=gnu11`, linked against the static archives (`*.a`) in the
campaign's build tree `<ports>/<lib>/work/build`, into `build/rt-bench/<arch>/<lib>/` (the command is in
`compile.log` there). Libraries built only as shared objects fail here, and the report says so.

**Run.** The binary is copied to `<target-dir>/bench/<lib>` on the target (`cat` over ssh, so no scp or sftp
server is needed) and run three times, each under QNX's `timeout -s KILL 600`:

| Run | Load | CPU placement |
|---|---|---|
| `idle` | none of ours | scheduler's choice |
| `loaded` | one thread per online CPU, `SCHED_RR` priority 10, looping `malloc` of 64 to 8255 bytes, `memset`, `free` | scheduler's choice |
| `loaded_isolated` | the same load | runmasks via `ThreadCtl(_NTO_TCTL_RUNMASK)`: measured thread on CPU 0 only, load threads on every other CPU |

In each run the measuring thread sets itself to `SCHED_FIFO` priority 60, starts the load (if any), sleeps
200 ms, makes 200 untimed warm-up calls, then makes N timed calls (`--n`, default 20000). Each call is timed
with `ClockCycles()` before and after (`rdtsc` on x86_64, `CNTVCT_EL0` on aarch64, per the SDP's
`<x86_64/neutrino.h>` and `<aarch64/neutrino.h>`) and converted with `SYSPAGE_ENTRY(qtime)->cycles_per_sec`.
The sorted times give min, median, p99, p99.9 and max in microseconds.

The load runs at a lower priority than the measured thread, so it never preempts it. What it changes is the
shared state: caches, memory bandwidth, the allocator's lock (when the measured call allocates) and kernel
work. That is the interference a real-time thread sees from a busy system around it.

SDP 8.0's `<sched.h>` defines no adaptive-partitioning commands for `SchedCtl()` (only a query and CPU
on/offline) and the SDP ships no `aps` utility, so runmasks are how this benchmark separates the real-time work
from the load.

Each run's JSON also records what the run really got, so a bad run is visible rather than silently wrong:
`cpus` (online CPUs), `load_threads` (started), `isolated` (0 when there is only one CPU, since there is nothing
to split), `runmask_rc` (`ThreadCtl` result, -1 = failed), `setschedparam_rc` (non-zero = the thread did not get
`SCHED_FIFO` 60), `cycles_per_sec`, and `clockcycles_global` (whether the syspage says `ClockCycles()` is
synchronized across CPUs; if 0, times from a thread that migrated between CPUs in the non-isolated runs can be
off).

**Score with latency** (`rt_bench.rt_score`): the static score minus 10 points per doubling of the loaded p99
over the idle median, at most 30. A ranking heuristic like the static score, not a certification.

**Outputs.**
- `results/rt/<arch>/<lib>.json`: `scan` (counts, first places, limits); `bench` with
  `call`, `target` (`uname -a` of the target), `platform` (`qemu` or `hardware`), `iterations`, `measured` (one
  paragraph saying what was measured, as above), `timing_note`, and `runs` (the three JSON results, or an
  `error`); `static_score`, `rt_score`, `score_basis`, `generated`, `qnx_porter_commit`.
- `results/rt.csv`: one row per library with a call spec, and arch: `platform, target, iterations, cpus, call`, then
  `<run>_<min|median|p99|p999|max>_us` for the three runs, `static_score, rt_score, error`.

CSV rows are merged by (library, arch), so `--only` or a second architecture does not drop other rows.

## Running it

Work trees (`ports/*/work/`) are not in git, so point `--ports` at the folder where `scripts/run_campaign.py`
ran; its `report.json` files must be for the same commits as this repository's `ports/`.

Static scan only (no SDP, no target):

    nice -n 19 python3 scripts/rt_report.py --scan-only --ports <campaign checkout>/ports

On the idle x86_64 QEMU target (`scripts/qemu_target.sh start`; nothing else running on the target or the host):

    source ~/qnx800/qnxsdp-env.sh
    python3 scripts/rt_report.py --target root@172.31.1.11 --ports <campaign checkout>/ports

The same for aarch64le (only zlib's harness has been compiled for aarch64le so far, not run):

    python3 scripts/rt_report.py --arch aarch64le --target root@172.31.1.12 --ports <campaign checkout>/ports-aarch64le

Options: `--only lib,lib`, `--n` (timed calls per run, at least 1000), `--target-dir` (scratch folder on the
target, default `/data/qnx-porter`), `--platform hardware` when the target is a board.

## Limits

- **QEMU timing is not hardware timing.** Every target this project has used is the SDP's QEMU image. Under
  QEMU the virtual CPUs are host threads: the host OS can deschedule them at any moment, and the time counters
  are virtualized. Absolute latencies, and worst cases most of all, include the emulator and the host. They
  are not representative of QNX on hardware. Compare runs and libraries with each other, not with hardware
  figures. each JSON file says this in `timing_note` whenever `--platform` is `qemu` (the default).
- **max is the worst case seen, not a bound.** N calls with one input on one machine. A worst-case execution
  time needs analysis or far longer runs on the real board.
- **One call per library, one input size.** A different call (or `deflate` at level 9, or a 1 MB document) can
  behave very differently.
- **Isolation needs at least two CPUs.** With one CPU the `loaded_isolated` run is the `loaded` run again
  (`isolated: 0`). `scripts/qemu_target.sh build` makes the QEMU image with `--cpu=4`; the run records the
  CPU count it saw.
- **The scan is not run on the target.** It reads the host's copy of the ported sources; the benchmark is
  the only part that touches QNX.
- **The load is ours.** Device interrupts, network traffic and other processes are not part of it.
