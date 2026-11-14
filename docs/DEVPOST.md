# Devpost submission text

Category: **Developer Tooling & Host Tools**. Every number below is copied from a file a script wrote, and each
one names that file:
- C/C++ libraries: the README headline and `results/ports.csv`, written by `scripts/ports_csv.py`;
- the language-model step: `docs/MODEL_STEP.md`, written by `scripts/model_md.py`;
- Rust crates: `docs/rust/CRATES.md`, written by `scripts/crates_md.py`;
- real-time: `docs/RT_RESULTS.md`, written by `scripts/rt_md.py`.

When the campaign is re-run, copy the new numbers from those files. Never type one a script did not print.

All targets are QNX 8.0 in QEMU: x86_64 under KVM, and aarch64 on QEMU `virt` (emulated). No hardware was used.

## Name
qnx-porter

## Tagline (under 200 characters)
Point it at an open-source C/C++ library or Rust crate: it builds it for QNX 8.0, fixes what breaks with
reviewable patches, and proves the port with the library's own tests on QNX.

## How qnx-porter meets the four judging criteria

### Technological implementation
qnx-porter drives the QNX SDP 8.0 toolchain end to end, and a port counts only when the library's own tests ran
on a QNX 8.0 target.
- **Real QNX builds, two architectures.** It writes a CMake toolchain file, a Meson cross file or autotools
  `--host` flags around `qcc` (`gcc_ntox86_64` or `gcc_ntoaarch64le`, sysroot `$QNX_TARGET`), builds, parses
  every compiler, linker, CMake and configure error, and applies QNX rules to them.
- **The library's own tests run on QNX.** ctest, meson test and make check run each test binary on the target
  over ssh. The build tree appears there at its host path through QNX's `ln -sP`, suites that refuse root run
  through QNX's `on -u`, and QNX's `timeout` caps each test.
- **Results** (README headline, written by `scripts/ports_csv.py`):

  > aarch64le: 58 of 61 libraries built for QNX 8.0; 1546 of 1642 of their own tests passed on a QNX 8.0 target
  > (43 libraries with tests that ran); 32 patches, 32 by rules (29 of the 31 libraries oss.qnx.com does not
  > list built); x86_64: 58 of 61 libraries built for QNX 8.0; 1563 of 1658 of their own tests passed on a QNX
  > 8.0 target (43 libraries with tests that ran); 31 patches, 31 by rules (29 of the 31 libraries oss.qnx.com
  > does not list built).

  Both architectures are at the newest release tag of each library. For example, on x86_64
  mbedtls 4.2.0 passed 148/148 of its tests on QNX and json-c 0.19 28/28 (`results/ports.csv`).
- **Crash triage from QNX core dumps.** When a test crashes on the target, the core is copied back and read
  with the SDP's own gdb. A `printf("%s", NULL)`, which glibc prints as `(null)` and QNX's libc faults on, is
  fixed by a rule, and the fix stays only if more tests pass. json-c, libconfig, tinyxml2 and capstone now pass.
- **aarch64 found its own problems**, each now a rule with a test (`docs/LEARNINGS.md`): cmocka guessed a
  32-bit word size, yaml-cpp's tests assumed signed `char`, and QNX's aarch64 libc names its strlen frame
  differently, which crash triage now recognises.
- **Rust crates** (`docs/rust/CRATES.md`): `qnx-porter crate` builds `std` with `-Zbuild-std`, links with
  `qcc`, and runs the crate's own tests on QNX 8.0. x86_64: 21 of 22 crates built; 2751 of 2764 of their own
  tests passed (18 crates with tests that ran). aarch64 on QEMU `virt`: 21 of 22 crates built; 2721 of 2733 of
  their own tests passed (18 crates with tests that ran).
- **QNX libc differences found by the tests**, each with a small reproducer (`docs/qnx-reports/`): `strtod()`
  rounding, `strftime()` with `%Ex`, `fchdir()` needing `O_DIRECTORY`, and `qsort()` with an inconsistent
  comparator. The reports are drafts and have not been sent.
- **Python on QNX, over our port.** The SDP's CPython 3.13.7 on the QNX target, with our zlib port loaded in
  place of the image's zlib, passes CPython's own `test_zlib` and `test_gzip`: 148 tests, 2 skipped, the same as
  over the image's zlib (`docs/PYTHON_ON_QNX.md`).
- **Contributions sent upstream** (14 Nov 2026; opened, under review, none merged): the nng fix for the
  POLLHUP hang (issue #2419, PR #2420) and its `<sys/errno.h>` include (issue #2421, PR #2422), libsrtp's test
  shuffle (cisco/libsrtp PR #841), the googletest `fchdir()` report (issue #5170), and qnx-porter's yyjson
  recipe for QNX's own qnx-ports/build-files (PR #343).
- **No hand-typed numbers.** Every table is written by a script from the per-library reports, and CI fails if
  the README's generated sections differ from what the script writes.

### Design: a complete product
- **One install, a few commands.** `python3 -m pip install --user qnx-porter` (on PyPI), then
  `qnx-porter doctor` (checks the SDP, compiles a test program and, optionally, checks the target),
  `qnx-porter port <git URL> --tag <release> --target root@<qnx-ip>`, and `qnx-porter crate <name> --version <v>`.
  `scripts/run_campaign.py` ports a whole list and regenerates the results.
- **One folder per library**, the same every time: `REPORT.md`, `report.json`, one numbered patch per change
  with its rule, reason and the compiler error it answers, a combined `qnx.patch`, the toolchain file, every
  build and test log, the test results as JUnit XML for CI dashboards (`logs/tests.junit.xml`), and an SPDX SBOM
  that includes our `qnx.patch` and its hash.
- **Fits QNX's own workflow.** Recipes in qnx-ports/build-files layout for CMake ports QNX does not have, each
  built with QNX's recursive make (`recipes/BUILD_CHECK.md`, generated), and a licence table with copyleft flags
  (`docs/LICENCES.md`, generated). It complements QNX's own agent skills, which build natively on the target
  with `abuild`: qnx-porter cross-compiles on the host with the SDP and runs each library's own suite test by
  test (README, "Related work").
- **Runs in CI.** A GitHub Action (`action.yml`) ports the repository it runs in on a self-hosted runner with
  the SDP. A weekly workflow re-ports every library at its upstream default branch and records whether it
  still builds.
- **Learnable.** A website, a codelab in QNX's codelab format, an architecture diagram with one box per source
  file (`docs/ARCHITECTURE.md`), and a limitations page with numbers (`docs/LIMITATIONS.md`).

### Potential impact: why a real-time OS needs this
- **Nothing builds on the target.** A QNX system in a car, a robot or a medical device has no compiler, so
  every library is cross-compiled with `qcc`, and most upstream projects ship no QNX toolchain file.
- **The host cannot run what it built.** "It compiled" proves little, so qnx-porter counts only test results
  from a QNX 8.0 target.
- **QNX's libc is POSIX, not glibc.** The same Linux-isms break library after library, which is why most of
  porting can be rules, collected once in `docs/LINUX_ISMS.md`.
- **QNX's markets review every change.** Automotive, medical and industrial teams cannot take a silently
  patched dependency. Every change here is a separate patch with its reason, rules run the same way every time,
  and a model's patch is reverted unless a rebuild proves it. This is a review aid, not a safety certification.
- **Real-time readiness, measured** (`docs/RT_RESULTS.md`). A library that passes its tests can still allocate,
  block or lock on the call a control loop makes. A static hazard scan covers every library, and a harness
  built with `qcc` measured one call for 14 libraries at SCHED_FIFO priority 60: idle, under load, and under
  load with the measuring thread isolated by a QNX runmask (`ThreadCtl(_NTO_TCTL_RUNMASK)`, timed with
  `ClockCycles()`). zlib, the one library where isolation at least halved loaded p99, went from 139.248 to
  24.535 us. These were measured in QEMU on a laptop: they rank libraries; they are not a latency guarantee.
- **Libraries those systems need:** TLS and crypto, MQTT, Modbus, OPC UA and CoAP, messaging, parsers and
  codecs. The headline also counts how many campaign libraries that oss.qnx.com does not list now build.
- **Checked against QNX's own hand-made ports** (`docs/related/qnx-ports-comparison.md`). In libevent,
  mosquitto, googletest, tinyxml2, jansson and pugixml, qnx-porter found the same QNX change or cause on its
  own. In libxml2, libwebsockets and libuv, it found the problem at the same place, but in the rules-only run
  only QNX's port fixed it. With the language-model step, libuv and libwebsockets now build (below).
- **Other languages stand on C.** Python's `zlib` and `sqlite3` modules and Rust's `rusqlite` use C libraries
  from our campaign. Many Rust crates support QNX 7 but not QNX 8.0 through a dependency (getrandom, errno,
  rustix); two rules fix that without editing the crate.

### Innovation & AI creativity
- **A language model that has to prove itself on QNX.** Rules handle what they can. For an error no rule
  covers, a language model must answer with a unified diff and a reason. The diff must pass
  `git apply --check`, and it is kept only if a rebuild with `qcc` clears the error. Otherwise it is reverted
  and shown as reverted.
- **Measured** (`docs/MODEL_STEP.md`, at the 2024 pins on x86_64): no rule could build libuv or libwebsockets.
  With the model step, "2 of the 2 libraries the rules could not build now build. Model patches kept: 2,
  reverted: 0." Each took one model call. libuv then ran its own tests on QNX through `on -u`: 384 subtests ok,
  46 not ok, 9 skipped.
- **It matches what QNX-aware engineers did, without seeing it.** The model's libuv fix makes the same two
  changes as upstream libuv's own QNX change, PR #4801 (merged after the version we ported). Its libwebsockets
  fix changes the same lines as QNX's own libwebsockets port.
- **Crash triage as a porting step.** A crash on the target becomes a QNX core dump, a backtrace from the SDP's
  gdb, a source location, and a mechanical fix that is kept only if more tests pass.
- **Rust on QNX 8.0 through its dependencies.** The `nto-to-qnx` rule lets QNX 8.0 take a dependency's QNX 7
  code path through cargo's `[patch]`. That is a heuristic, so the crate's own tests on the target decide.

## Inspiration
QNX 8.0 is free for non-commercial use, and QNX runs a ports site and a prize category for ports, because every
library that has never been built for QNX is a reason a team picks another OS. Most porting work is the same
again and again: a header glibc includes implicitly and QNX does not, sockets living in `libsocket`, `-lpthread`
and `-lrt` pointing at libraries whose functions are already in QNX's libc, `-Werror` tripping on new warnings.
That part should be a tool. Real Linux-only code like epoll deserves a person's or a language model's attention,
with every change visible.

## What it does
`qnx-porter port <git URL> --tag <release> --target root@<qnx-ip>`:
1. Clones the library at the tag and detects CMake, Meson, autotools or Make.
2. Generates a QNX SDP 8.0 toolchain: a CMake toolchain file using `qcc` with
   `CMAKE_C_COMPILER_TARGET gcc_ntox86_64` (or `gcc_ntoaarch64le` with `--arch aarch64le`) and `$QNX_TARGET` as
   sysroot, a Meson cross file, or `--host=x86_64-pc-nto-qnx8.0.0` for autotools.
3. Builds, and parses every GCC, linker, CMake, Meson and configure error into structured diagnostics.
4. Applies deterministic QNX rules first, each backed by QNX 8.0 documentation or the build that found it
   (`docs/LINUX_ISMS.md`). Each change is a numbered patch file with the rule, the reason and the exact error it
   answers.
5. Sends only what no rule handles to an optional language model, with QNX-specific hints, under the checks
   above.
6. When the build is clean, runs the library's **own** test suite on a QNX 8.0 target in QEMU, built with QNX's
   `mkqnximage`.
7. When a test crashes on QNX, reads the core dump with the SDP's gdb and fixes the crash if it is mechanical.
8. Writes `ports/<library>/` with the report, every patch, the toolchain file, the logs and an SBOM.

`qnx-porter crate <name> --version <v>` does the same for a Rust crate from crates.io.

## Evidence of QNX use
| Claim | File, function, output |
|---|---|
| Finds and checks QNX SDP 8.0 | `qnx_porter/qnx.py`: `sdp_env()` sources `qnxsdp-env.sh`; `doctor()` runs `qcc -V` and compiles a test program |
| Generates the QNX toolchain | `qnx_porter/qnx.py`: `cmake_toolchain()`, `meson_cross()`, `gnu_env()`, `ARCHES` (`gcc_ntox86_64`, `gcc_ntoaarch64le`); saved per port as `ports/<library>/qnx-toolchain.cmake` and `ports-aarch64le/<library>/qnx-toolchain.cmake` |
| Invokes qcc | `qnx_porter/build.py`: `Job.steps()` builds the configure/build commands, `run()` executes them; logs in `ports/<library>/logs/round-NN.log` |
| QNX 8.0 porting knowledge, with sources | `qnx_porter/fixes.py` `_rule()`, `qnx_porter/linuxisms.py`; table in `docs/LINUX_ISMS.md` |
| Runs the library's tests on QNX 8.0 | `qnx_porter/target.py`: `ctest_on_target()`, `Target.sync()`, `write_wrapper()`, `remote_command()`; output `ports/<library>/logs/tests.log` and `tests.junit.xml` (`junit_from_log()`) |
| QNX path-space links | `qnx_porter/target.py`: `link_command()` (QNX `ln -sP`), called from `Target.sync()` |
| QNX `on -u` and `timeout` | `qnx_porter/target.py`: `remote_command()`; `run_as: qnxuser` for libuv in `campaign.yaml`; output `ports-model/libuv/logs/tests.log` |
| Reads QNX core dumps | `qnx_porter/crash.py`: `collect()` copies cores from the target, `backtrace()` runs the SDP's gdb; output `ports-2024/json-c/logs/crashes.log` |
| Real-time harness on QNX | `qnx_porter/rt_bench.py`: `BENCH_C` (SCHED_FIFO, `ThreadCtl(_NTO_TCTL_RUNMASK)`, `ClockCycles()`, `SYSPAGE_ENTRY(qtime)->cycles_per_sec`), `compile_bench()` with `qcc`, `run_bench()`; output `results/rt/x86_64/<library>.json` |
| Rust on QNX 8.0 | `qnx_porter/crate.py`: `cargo_env()` (SDP `qcc`/`q++`), `build_tests()` (`-Zbuild-std`), `run_tests()`; output `ports-rust*/<crate>/logs/tests.log` |
| Builds the QNX target | `scripts/qemu_target.sh` (`mkqnximage`, sshd-auth snippet, bridge networking; `QNX_TARGET_ARCH=aarch64le` for aarch64 on QEMU) |
| Target identity | `Target.uname()`; field `target` in every `report.json` |
| One command | `scripts/run_campaign.py` (`preflight()` stops if qcc is missing, `check_target()` if the target is) |

## How we built it
The agent is Python 3 with the standard library only (no runtime dependencies); the campaign script adds PyYAML
to read `campaign.yaml`. The loop is in `qnx_porter/agent.py`; rules in `fixes.py` and `linuxisms.py`; error
parsing in `errors.py`; the target runner in `target.py`; crash triage in `crash.py`; Rust crates in `crate.py`;
the real-time scan and harness in `rt.py` and `rt_bench.py`; the language-model client in `llm.py` (any
chat-completions endpoint, configured only through `QNX_PORTER_API_KEY`, `QNX_PORTER_MODEL` and
`QNX_PORTER_BASE_URL`). pytest tests run in CI without QNX, including full runs of the porting loop on a
deliberately broken library with the host compiler. The repository was created on 10 Nov 2026, during the
submission period.

## Challenges we ran into
- Our first SDP install was silently incomplete: many files were empty and qcc failed with
  "cc1: Exec format error". `qnx-porter doctor` now detects that and compiles a test program before saying ok.
- The QEMU image from mkqnximage booted QNX 8.0, but sshd exited: `sshd-auth` was not in the image. One
  snippet line fixed it; `scripts/qemu_target.sh` now does it.
- Our first campaign runs failed mostly because of our own tool: CMake ignores toolchain flag changes on an
  existing cache, automake builds tests only inside `make check`, and ctest never wraps script-based tests with
  the cross-compiling emulator. Every run's log is in `results/runs/`, and the README's "How we got here" table
  summarises each.
- The emulated aarch64 target needs the machine to itself: under host load, ssh to it timed out and tests were
  lost, so those libraries were re-run on a quiet host (`docs/LEARNINGS.md`).
- Real QNX 8.0 differences we turned into rules: `isinf` lives in libm, `inet_pton` is `__inet_pton` in
  libsocket, `<sys/errno.h>` does not exist, glibc's `htobe32` family is in `<net/netbyte.h>`.

## Accomplishments that we're proud of
- A port counts only when the library's own tests ran on QNX 8.0, on two architectures (headline above).
- A language-model step that is measured, reverts what it cannot prove, and matched upstream libuv's own QNX
  fix without seeing it.
- Rust crates' own test suites running on QNX 8.0 x86_64 and aarch64 on QEMU.
- Every change is a patch file with a reason, and every number is written by a script.

## What we learned
- A port that compiles proves little. Our own first test runner reported failures that were bugs in the
  runner, not in QNX; only reading every test's output on the target told the two apart.
- QNX's libc follows POSIX where glibc is generous, and the same few differences come back in library after
  library. That is what makes most of porting a rule rather than a judgement.
- A crash on the target is often glibc-only behaviour in the test, not a QNX bug: read the core dump before
  blaming the OS.

## What's next
- Publish the campaign at the latest upstream release of each library (`campaign.yaml`); the published results
  use the 2024 pins (`campaign-2024.yaml`).
- Run on real hardware. Every result so far is from QEMU, and the real-time numbers above mean little until
  they are measured on a board.
- Follow the five contributions sent upstream on 14 Nov 2026 through review (nng issues #2419 and #2421 with
  PRs #2420 and #2422, cisco/libsrtp PR #841, google/googletest issue #5170, qnx-ports/build-files PR #343 for
  yyjson; all open, none merged), and send the drafted QNX libc reports if the team decides to.
- build-files recipes for the autotools, Meson and Make ports, which the recipe generator does not write yet.

## Built with
python, rust, qnx, qnx-sdp-8.0, qcc, qemu, cmake, meson, autotools, cargo, git, github-actions

## Links
- Repo: https://github.com/thegoodengineers/qnx-porter
- Website: https://thegoodengineers.github.io/qnx-porter/
- Codelab: https://thegoodengineers.github.io/qnx-porter/codelab-port-a-library.html
- Video: `video/out/qnx-porter-demo.mp4` in the repo; the YouTube link is added at submission.
- PyPI: https://pypi.org/project/qnx-porter/
- Architecture: https://github.com/thegoodengineers/qnx-porter/blob/main/docs/ARCHITECTURE.md
