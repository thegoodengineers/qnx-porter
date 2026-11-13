# Limitations

What qnx-porter does not do, or has not shown yet. Numbers are from [`results/ports.csv`](../results/ports.csv)
(x86_64 campaign, 12 Nov 2026) unless a line says otherwise.

## Where it was tested
- **QEMU only.** The x86_64 target runs under KVM. The aarch64 target is QEMU `virt`, fully emulated and much
  slower. No real hardware was used: the team has no Raspberry Pi 5 or other board. Results on aarch64 are
  "aarch64 on QEMU", not results on a device.
- **QNX SDP 8.0 build 141 only.** QNX 7.x is not a goal.
- **Linux host only** (Ubuntu 22.04 in WSL2 on Windows), because QNX's QEMU image tooling (`mkqnximage`)
  is Linux-only.

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
- **Some tests in a suite cannot run there and are reported as "not runnable"**, never as passed:
  - cmark (4 tests) and googletest (18) need python3.10 on the target;
  - libpng (32) and opus (5) need cmake on the target.
- **Things the test image lacks cause failures that are not QNX bugs**, and the reports say so: `killall`
  (libmodbus), `/bin/echo` (pcre2grep), internet access (nng), enough memory for one zstd test (2 GiB target),
  a `locale` command (pcre2).
- **One run per architecture.** A flaky test can pass or fail by chance. nng's `sockaddr_test` failed in one
  run and passed when run again by hand.

## What the agent fixes, and what it does not
- **The published numbers use rules only.** The language-model step was off, and 0 patches are by the model.
  The model step exists and is never trusted: its diff is reverted unless a rebuild clears the error. Its
  effect has not been measured yet.
- **4 libraries did not build:**
  - libgpiod and can-utils use Linux-only kernel interfaces, as expected.
  - libuv and libwebsockets stop on errors no rule covers. QNX's own ports change exactly those lines.
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
- pcre2's test 8 crashes deep in a recursive function. Running out of stack is likely but not confirmed.

## Ports, recipes and comparisons
- **Static libraries.** The campaign builds static libraries (`BUILD_SHARED_LIBS=OFF`), and the generated
  build-files recipes do the same by default.
- **Recipes only for CMake projects.** 34 recipes were generated. libsodium, libmodbus (autotools), tinycbor
  (make) and inih (meson) built, but have no recipe yet. 3 recipes were built through QNX's make system
  (yyjson, wolfssl, flac); the other 31 have not been.
- **The comparison with qnx-ports compares different versions and targets.** 13 of the 21 shared libraries are
  at different versions, and QNX's results are mostly from a Raspberry Pi 4.

## Rust
- **Tier 3 targets.** `x86_64-pc-qnx` and `aarch64-unknown-qnx` need nightly Rust and `-Zbuild-std`. The
  rustc book marks their full standard-library support "in progress".
- **The `nto-to-qnx` rule is a heuristic.** It lets QNX 8.0 take a dependency's QNX 7 code path. That path
  builds; whether it is correct on QNX 8.0 is shown only by the crate's tests on the target.
- **Some crates cannot be fully tested.** Doc tests are not run. regex and zstd are built as libraries only,
  because their published crates do not include the files their tests read. nix does not build.

## Weekly upstream check
- **Build only, rules only.** The weekly job ports each library at its upstream HEAD and checks that it
  builds; it runs no tests.
- **It needs a self-hosted runner with the SDP**, because GitHub's own runners cannot install it. It runs
  only while that machine is on.
