# Limitations

What qnx-porter does not do, or has not shown yet. C/C++ numbers are from [`results/ports.csv`](../results/ports.csv)
(x86_64 campaign, 12 Nov 2026) unless a line says otherwise. The other numbers come from the generated page each
line links.

## Where it was tested
- **QEMU only.** The x86_64 target runs under KVM. The aarch64 target is QEMU `virt`, fully emulated and much
  slower. No real hardware was used: the team has no Raspberry Pi 5 or other board. Results on aarch64 are
  "aarch64 on QEMU", not results on a device.
- **aarch64 on QEMU is done for the C/C++ campaign and the Rust crates**, as a separate run from x86_64
  ([docs/LEARNINGS.md](LEARNINGS.md), 12–13 Nov 2026). Under host load, ssh to the emulated target timed out and
  tests were lost; libjpeg-turbo, nng and flac were re-run on a quiet host. Some differences from x86_64 are not
  explained yet: libsrtp 9/12 (8/12 on x86_64), libjpeg-turbo registers 574 tests on aarch64 against 590 on
  x86_64, and nng 80/86 against 82/86.
- **QNX SDP 8.0 build 141 only.** QNX 7.x is not a goal.
- **Linux host only** (Ubuntu 22.04 in WSL2 on Windows), because QNX's QEMU image tooling (`mkqnximage`)
  is Linux-only.
- **Older library versions.** The published C/C++ results use the 2024 pins in `campaign-2024.yaml`.
  `campaign.yaml` names newer upstream releases; results at those versions are not published yet.

## How much the tests prove
- **33 of the 57 libraries that built ran at least one of their own tests on QNX.**
  - 19 more register no tests in their default CMake build: BLAKE3, Micro-CDR, benchmark, c-ares, inih,
    kissfft, libcbor, libcoap, libdeflate, libpng, lz4, miniz, mosquitto, msgpack-c, open62541, opus, spdlog,
    tomlplusplus, xxHash. Some have tests behind an option we left off, or tests that need another library
    built first.
  - For these 19, "built" means the library compiles and links for QNX 8.0, nothing more.
- **5 built libraries are build-only on purpose**, because their suites need what the target lacks:
  - sqlite needs Tcl;
  - paho.mqtt.c needs an MQTT broker;
  - flatcc's tests run on the build host;
  - nanopb's need scons and protoc;
  - tinycbor has no test runner we drive.
- **Some tests in a suite cannot run there and are reported as "not runnable"**, never as passed (both
  architectures):
  - cmark (4 tests) and googletest (18) need python3.10 on the target;
  - libpng (32) and opus (5) need cmake on the target.
- **Things the test image lacks cause failures that are not QNX bugs**, and the reports say so: `killall`
  (libmodbus), `/bin/echo` (pcre2grep), internet access (nng), enough memory for one zstd test (2 GiB target),
  a `locale` command (pcre2).
- **One run per architecture.** A flaky test can pass or fail by chance. nng's `sockaddr_test` failed in one
  run and passed when run again by hand.

## What the agent fixes, and what it does not
- **The headline C/C++ numbers use rules only.** The language-model step was off in the campaign, and 0 of its
  patches are by the model.
- **The language-model step was measured separately**, on libuv and libwebsockets, the libraries the rules
  could not build that are not Linux-only by design ([docs/MODEL_STEP.md](MODEL_STEP.md), 2024 pins, x86_64
  only). Both now build; model patches kept: 2, reverted: 0. Its limits:
  - Two libraries is a small sample. No patch was reverted in this run, so the revert path is shown only by
    the tests (`tests/test_agent_loop.py`), with a stand-in model.
  - A model's answer can differ from run to run; the page shows the latest run.
  - Building is not passing. libuv: 0/2 test binaries pass; inside them, its own subtests are 384 ok, 46 not
    ok, 9 skipped. libwebsockets registers no tests in its default build.
  - It was not run on aarch64.
- **4 libraries did not build with rules only:**
  - libgpiod and can-utils use Linux-only kernel interfaces, as expected. No fix makes them QNX programs.
  - libuv and libwebsockets stop on errors no rule covers. QNX's own ports change exactly those lines. With the
    model step they build (above).
- **Finding is not always fixing.** The `printf-null` rule fixes a `printf("%s", NULL)` crash only when the
  call is in plain code it can rewrite: json-c, libconfig, tinyxml2 and capstone. It does not fix libxml2 (the
  printf is inside its generic error code) or nng (a tail call hides the caller in the backtrace). Those are
  reported, not patched.
- **Rules never rewrite real Linux-only code** such as epoll or inotify.

## Results that are not QNX bugs, or not yet confirmed
- The reports in [`docs/qnx-reports/`](qnx-reports/) are drafts and have not been sent:
  - `strtod` rounding: a QNX bug, reproduced with a stand-alone program.
  - `strftime` `%E*`: a QNX bug, reproduced the same way.
  - `fchdir` needs `O_DIRECTORY`: documented QNX behaviour, not a bug.
  - `qsort` with an inconsistent comparator: undefined C in libsrtp's tests.
- Five upstream contributions were sent on 14 Nov 2026 (nng x2, libsrtp, googletest issue, the yyjson recipe for
  qnx-ports/build-files) and are open, under review; none is merged yet
  ([`upstream/outbox/README.md`](../upstream/outbox/README.md)). The libconfig patch, the googletest PR, the
  mbedtls recipe and the full qnx-ports pull request text are not sent.
- pcre2's test 8 crashes deep in a recursive function. Running out of stack is likely but not confirmed.

## Real-time readiness
The harness ran on QNX 8.0 x86_64 in QEMU under KVM ([docs/RT_RESULTS.md](RT_RESULTS.md)).
- **QEMU timing is not hardware timing.** A virtual CPU can be descheduled by the host at any moment, so
  absolute numbers, and maxima most of all, say little about real hardware. For cJSON, expat, json-c, miniz,
  pcre2, xxHash and yyjson, idle p99 is above loaded p99, a sign of QEMU timing noise rather than of the
  library.
- **14 libraries measured.** libsodium and msgpack-c were not: their harness did not compile.
- **x86_64 only.** The latency harness has not run on aarch64 ([docs/RT_READINESS.md](RT_READINESS.md)).
- **One call per library, one input size,** and max is the worst case seen, not a bound.
- **The static scan counts library-wide.** It cannot tell which calls are on the path you use, and the score
  is a ranking heuristic, not a certification.

## Ports, recipes and comparisons
- **Static libraries.** The campaign builds static libraries (`BUILD_SHARED_LIBS=OFF`), and the generated
  build-files recipes do the same by default.
- **Recipes only for CMake projects.** libsodium, libmodbus (autotools), tinycbor (make) and inih (meson) built,
  but have no recipe yet.
- **Recipes were built with QNX's make for `nto-x86_64-o`** (34 of 34 built, [recipes/BUILD_CHECK.md](../recipes/BUILD_CHECK.md)).
  For `nto-aarch64-le`, only yyjson, wolfssl and flac were built.
- **The comparison with qnx-ports compares different versions and targets.** 13 of the 21 shared libraries are
  at different versions, and QNX's results are mostly from a Raspberry Pi 4.

## Licences
- **Scanner findings, not a legal review** ([docs/LICENCES.md](LICENCES.md)). Only top-level and first-level
  licence, copying, notice and README files were scanned, so a licence stated only in source headers is not
  seen. Of 61 libraries: 9 have a GPL or AGPL licence in their expression, 7 an LGPL licence, 9 a weak copyleft
  licence (LGPL, MPL, EPL or CPL), and 1 with no detected licence.

## Rust
The crates' own tests ran on QNX 8.0 x86_64 and aarch64 on QEMU ([docs/rust/CRATES.md](rust/CRATES.md)).
- **Tier 3 targets.** `x86_64-pc-qnx` and `aarch64-unknown-qnx` need nightly Rust and `-Zbuild-std`. The
  rustc book marks their full standard-library support "in progress".
- **The `nto-to-qnx` rule is a heuristic.** It lets QNX 8.0 take a dependency's QNX 7 code path. That path
  builds; whether it is correct on QNX 8.0 is shown only by the crate's tests on the target.
- **Some crates cannot be fully tested.** Doc tests are not run. regex and zstd are built as libraries only,
  because their published crates do not include the files their tests read. mio's tests need cargo features a
  default build leaves off, so none ran. nix does not build.
- **Failing tests not yet explained:** crossbeam-channel's `golang::select2` fails on x86_64 and passes on
  aarch64; not investigated yet.

## Weekly upstream check
- **Build only, rules only.** The weekly job ports each library at its upstream HEAD and checks that it
  builds; it runs no tests.
- **It needs a self-hosted runner with the SDP**, because GitHub's own runners cannot install it. It runs
  only while that machine is on.
