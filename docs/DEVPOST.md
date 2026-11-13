# Devpost submission text

Category: **Developer Tooling & Host Tools**. Every number below comes from `results/ports.csv` or the README
headline, both written by `scripts/ports_csv.py` from the per-library reports. If the campaign is re-run, copy
the new numbers from the script's output; never type one it did not print.

## Name
qnx-porter

## Tagline (under 200 characters)
Point it at an open-source C/C++ library: it builds it for QNX 8.0, fixes what breaks with reviewable
patches, and proves the port by running the library's own tests on QNX.

## Inspiration
QNX 8.0 is free for non-commercial use, and QNX runs a ports site and a whole prize category for ports,
because every library that has never been built for QNX is a reason a team picks another OS. When we
looked at what porting actually involves, most of it is the same work again and again: a header glibc
includes implicitly and QNX does not, sockets living in `libsocket`, `-lpthread` and `-lrt` pointing at
libraries whose functions are already in QNX's libc, `-Werror` tripping on new warnings. That part should
be a tool. The rest, real Linux-only code like epoll, deserves a person's or a language model's attention, with
every change visible.

**Why C and C++.** QNX itself is built for C and C++: QNX OS for Safety 8.0 ships C and C++ toolchains
classified for ISO 26262 and IEC 61508, plus a certified C library and C++ library
(https://qnx.software/en/software/products-and-solutions/qnx-os-and-os-for-safety). Other languages stand on C
libraries. Python's `zlib` and `sqlite3` modules use the zlib and SQLite C libraries, PyNaCl wraps libsodium,
and Rust's `rusqlite` links SQLite through `libsqlite3-sys`. All three C libraries are in our campaign and all
three built for QNX 8.0: zlib passed 2/2 of its tests on QNX, libsodium 80/80, and sqlite was built only, because
its test suite needs Tcl on the target. Port the C layer, and the languages above it can follow.

**How this differs from QNX's own ports.** QNX maintains hand-made recipes in the qnx-ports organisation on
GitHub. qnx-porter instead generates the port and proves it with the library's own tests on a QNX target. 21 of
our 61 libraries also have a qnx-ports recipe, and we compared each one (`docs/related/qnx-ports-comparison.md`):
- in libevent, mosquitto, googletest, tinyxml2, jansson and pugixml we found the same QNX change or cause
  independently;
- in libxml2, libwebsockets and libuv we found the problem at the same place, but only QNX's port fixed it.

## What it does
`qnx-porter port <git URL> --tag <release> --target root@<qnx-ip>`:
1. Clones the library at the tag and detects CMake, Meson, autotools or Make.
2. Generates a QNX SDP 8.0 toolchain: a CMake toolchain file using `qcc` with
   `CMAKE_C_COMPILER_TARGET gcc_ntox86_64` (or `gcc_ntoaarch64le`) and `$QNX_TARGET` as sysroot, a Meson cross
   file, or `--host=x86_64-pc-nto-qnx8.0.0` for autotools.
3. Builds, and parses every GCC, linker, CMake, Meson and configure error into structured diagnostics.
4. Applies deterministic QNX rules first, each backed by QNX 8.0 documentation or the build that found it
   (`docs/LINUX_ISMS.md`): missing headers, libsocket and libfsnotify, libc-provided pthread/rt/dl,
   `MAP_ANON`, `prctl` to `pthread_setname_np`, OS `#if` chains that end in `#error`, GCC 12's `-fno-common`.
   Each change is a numbered patch file with the rule, the reason and the exact error it answers.
5. Sends only what no rule handles to an optional language model, with QNX-specific hints. The model must answer
   with a diff; it must pass `git apply --check`, and if the rebuild still shows the error, the agent
   reverts it and marks it reverted in the report.
6. When the build is clean, runs the library's **own** test suite (ctest, meson test or make check) on a
   QNX 8.0 target: the build tree is copied to the QEMU image from `mkqnximage` and every test command runs
   there over ssh.
7. When a test crashes on QNX, copies the core dump back, reads it with the SDP's gdb, and fixes the crash if it
   is mechanical: `printf("%s", NULL)`, which glibc prints as `(null)` and QNX's libc faults on. The fix stays
   only if more tests pass.
8. Writes `ports/<library>/`: REPORT.md, report.json, every patch, one combined `qnx.patch`, the toolchain
   file and every build and test log.

`scripts/run_campaign.py` runs it over every library in `campaign.yaml` and regenerates `results/ports.csv` and
the README table. Our campaign of 12 Nov 2026, rules only, no language model, with the tests run on QNX 8.0
x86_64 in QEMU:

> x86_64: 57 of 61 libraries built for QNX 8.0; 1332 of 1366 of their own tests passed on a QNX 8.0 target
> (33 libraries with tests that ran); 25 patches, 25 by rules (29 of the 31 libraries oss.qnx.com does not list
> built).

For example mbedtls passed 130/130 of its tests on QNX, libsodium 80/80, json-c 25/25 and libjpeg-turbo
590/590. The 4 libraries that did not build are libgpiod and can-utils (Linux-only kernel interfaces, as
expected), and libuv and libwebsockets, which stop on errors no rule covers yet. The README groups
the failing tests by cause, and the QNX libc differences behind some of them have reproducers in
`docs/qnx-reports/`.

Around the core loop:
- **aarch64 on QEMU:** `--arch aarch64le` cross-compiles for 64-bit Arm, and `scripts/qemu_target.sh` boots an
  aarch64 QNX 8.0 image on QEMU's `virt` machine for the tests. The results in the repository today are x86_64.
- **build-files recipes:** `scripts/emit_recipes.py` turns the 34 CMake ports qnx-ports does not have into
  recipes in qnx-ports/build-files layout, with the flags and patches that were tested.
- **Weekly upstream HEAD:** a GitHub Actions workflow on a self-hosted runner with the SDP re-ports every library
  at its upstream default branch each Monday and records whether it still builds for QNX 8.0.

## Evidence of QNX use
| Claim | File, function, output |
|---|---|
| Finds and checks QNX SDP 8.0 | `qnx_porter/qnx.py`: `sdp_env()` sources `qnxsdp-env.sh`; `doctor()` runs `qcc -V` and compiles a test program |
| Generates the QNX toolchain | `qnx_porter/qnx.py`: `cmake_toolchain()` (`qcc`, `gcc_ntox86_64`, sysroot `$QNX_TARGET`), `meson_cross()`, `gnu_env()` (`x86_64-pc-nto-qnx8.0.0`) |
| Invokes qcc | `qnx_porter/build.py`: `Job.steps()` builds the configure/build commands, `run()` executes them; logs in `ports/<library>/logs/round-NN.log` |
| QNX 8.0 porting knowledge, with sources | `qnx_porter/fixes.py` `_rule()`, `qnx_porter/linuxisms.py`; table in `docs/LINUX_ISMS.md` |
| Runs the library's tests on QNX 8.0 in QEMU (`mkqnximage`) | `qnx_porter/target.py`: `ctest_on_target()`, `Target.sync()` (QNX `ln -sP` path links), `write_wrapper()`, `remote_command()` (QNX `timeout`); output `ports/<library>/logs/tests.log`, e.g. `ports/mbedtls/logs/tests.log` ends "130/130 tests passed on the QNX target" |
| Reads QNX core dumps | `qnx_porter/crash.py`: `collect()` copies cores from the target, `backtrace()` runs the SDP's gdb; output `ports/<library>/logs/crashes.log` |
| Builds the QNX target | `scripts/qemu_target.sh` (mkqnximage, sshd-auth snippet, bridge networking; `QNX_TARGET_ARCH=aarch64le` for aarch64 on QEMU) |
| Target identity | `Target.uname()`; field `target` in every `ports/<library>/report.json` |
| One command | `scripts/run_campaign.py` (`preflight()` stops if qcc is missing, `check_target()` if the target is) |
| Results | `results/ports.csv`, written by `scripts/ports_csv.py` from the reports only |

## Potential impact: why an RTOS needs this
QNX targets have no compiler and cannot run the build machine's binaries, so every library must be
cross-compiled with qcc and tested on the target itself; most upstream projects ship no QNX toolchain file
and assume glibc. The same Linux-isms break library after library, which is why they can be rules. QNX's
markets (automotive, medical, industrial) review every dependency change, so each patch carries its rule,
reason and compiler error, and language-model patches are reverted unless a rebuild proves them. The campaign
targets libraries those systems need: TLS and crypto, MQTT, Modbus, OPC UA and CoAP, messaging, parsers and
codecs.

## How we built it
The agent is Python 3 with the standard library only (no runtime dependencies); the campaign script adds
PyYAML to read `campaign.yaml`. It installs anywhere the SDP does. The loop is in `qnx_porter/agent.py`; rules
in `fixes.py` and `linuxisms.py`; error parsing in `errors.py`; the target runner in `target.py`; crash triage
in `crash.py`; the language-model client in `llm.py` (any chat-completions endpoint, configured only through
`QNX_PORTER_API_KEY`, `QNX_PORTER_MODEL` and `QNX_PORTER_BASE_URL`). `docs/ARCHITECTURE.md` draws the whole
pipeline. pytest tests run in CI without QNX, including full runs of the porting loop on a deliberately broken
library with the host compiler. Candidates were checked against all of oss.qnx.com and the qnx-ports
organisation by `scripts/check_candidates.py`.

## Challenges we ran into
- Our first SDP install was silently incomplete: many files were empty and qcc failed with
  "cc1: Exec format error". `qnx-porter doctor` now detects that and compiles a test program before saying ok.
- The QEMU image from mkqnximage booted QNX 8.0, but sshd exited: `sshd-auth` was not in the image. One
  snippet line fixed it; `scripts/qemu_target.sh` now does it.
- Our first campaign runs failed mostly because of our own tool: CMake ignores toolchain flag changes on an
  existing cache, automake builds tests only inside `make check`, and ctest never wraps script-based tests with
  the cross-compiling emulator. We fixed each one and re-ran; every run's log is in `results/runs/`, and the
  README's "How we got here" table has the summary of each.
- A DNS outage cut our final run short partway through. Those libraries got an error report, the campaign
  carried on, and we re-ran just them with `--only` once the network was back.
- Real QNX 8.0 differences we turned into rules: `isinf` lives in libm, `inet_pton` is `__inet_pton` in
  libsocket, `<sys/socket.h>` includes `<stdbool.h>`, `<sys/errno.h>` does not exist, glibc's `htobe32`
  family is in `<net/netbyte.h>`.

## Accomplishments that we're proud of
- Every change is a patch file with a reason; nothing is hidden, and a language-model patch that does not help
  is reverted and shown as reverted.
- A port only counts when the library's own tests ran on QNX 8.0: 1332 of 1366 of them passed, across the 33
  libraries whose tests ran.
- 29 of the 31 libraries in our campaign that oss.qnx.com does not list built for QNX 8.0.
- Recipes for qnx-ports: 34 build-files recipes are generated (`recipes/build-files/ports/`). The pull request
  text is drafted, not sent (`docs/upstream/qnx-ports-build-files-PR.md`); opening it is the team's decision.
- QNX libc differences found by the tests, each with a small reproducer (`docs/qnx-reports/`): `strtod()`
  rounding, `strftime()` with `%Ex`, `fchdir()` needing `O_DIRECTORY`, and `qsort()` with an inconsistent
  comparator. The reports are drafted, not sent.

## What we learned
- A port that compiles proves little. Our own first test runner reported failures that were bugs in the runner,
  not in QNX; only reading every test's output on the target told the two apart.
- QNX's libc follows POSIX where glibc is generous, and the same few differences come back in library after
  library. That is what makes most of porting a rule rather than a judgement.
- A crash on the target is often glibc-only behaviour in the test, not a QNX bug: read the core dump before
  blaming the OS.
- Keep the evidence with the result: every number we publish is written by a script from the per-library
  reports, so the table cannot drift from the runs.

## What's next
- aarch64 on QEMU results in `results/ports.csv` next to x86_64.
- Opening the qnx-ports pull request with the generated recipes, if the team decides to.
- A build-files layout for the autotools, Meson and Make ports, which the recipe generator does not write yet.
- More rules from the errors that still stop libuv and libwebsockets.

## Built with
python, qnx, qnx-sdp-8.0, qcc, qemu, cmake, meson, autotools, git, github-actions

## Links
- Repo: https://github.com/thegoodengineers/qnx-porter
- Video: `video/out/qnx-porter-demo.mp4` in the repo; the YouTube link is added at submission.
- Codelab: https://github.com/thegoodengineers/qnx-porter/blob/main/docs/CODELAB.md
- Architecture: https://github.com/thegoodengineers/qnx-porter/blob/main/docs/ARCHITECTURE.md
