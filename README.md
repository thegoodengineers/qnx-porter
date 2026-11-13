# qnx-porter

[![tests](https://github.com/thegoodengineers/qnx-porter/actions/workflows/test.yml/badge.svg)](https://github.com/thegoodengineers/qnx-porter/actions/workflows/test.yml)

**Point it at an open-source C/C++ library. It builds the library for QNX 8.0, fixes what breaks,
and proves the port by running the library's own tests on a QNX 8.0 target.**

Built for the [QNX Global Hackathon](https://qnx.devpost.com/) (Developer Tooling & Host Tools) by
Chirag, Bhumika, Ayush and Abhijeet (The Good Engineers).

## Why it matters
- QNX 8.0 is free for non-commercial use, but most open-source C/C++ libraries have never been built
  for it. QNX runs its own ports site ([oss.qnx.com](https://oss.qnx.com)) and a prize category for ports,
  because every missing library is a reason a team picks another OS.
- Porting is repetitive: the same missing headers, the same `-lsocket`, the same Linux-only calls,
  library after library. That part should be automatic, and every change should be reviewable.
- A port that compiles is not a port. qnx-porter counts a library as ported only when its own test
  suite runs on QNX 8.0.

## Why C and C++
**QNX itself is built for C and C++.** QNX OS for Safety 8.0 ships C and C++ toolchains classified for ISO 26262
and IEC 61508, plus a certified C library and C++ library
([QNX OS for Safety 8.0](https://qnx.software/en/software/products-and-solutions/qnx-os-and-os-for-safety),
[certified tools](https://qnx.software/en/software/technologies/safety-certified/certified-tools),
[product brief](https://qnx.software/content/dam/qnx-xwalk/pdf/product-briefs/qnx-os-for-safety-product-brief.pdf)).
The OS's own interfaces, such as the C library reference, resource managers and message passing, are C APIs.

**Other languages stand on C libraries.** Python's [`zlib`](https://docs.python.org/3/library/zlib.html) and
[`sqlite3`](https://docs.python.org/3/library/sqlite3.html) modules use the zlib and SQLite C libraries.
[PyNaCl](https://pypi.org/project/PyNaCl/) wraps libsodium. In Rust,
[`rusqlite`](https://crates.io/crates/rusqlite) links SQLite through
[`libsqlite3-sys`](https://crates.io/crates/libsqlite3-sys). [`flate2`](https://crates.io/crates/flate2) can
use zlib through [`libz-sys`](https://crates.io/crates/libz-sys). If the C library does not build for QNX,
nothing above it does. All three are in our campaign:
- zlib: built, 2/2 tests pass on QNX 8.0.
- libsodium: built, 80/80 tests pass.
- sqlite: built. Its test suite needs Tcl on the target, so it was not run.

([`results/ports.csv`](results/ports.csv)).

## Related work: QNX's own ports
QNX maintains hand-made build recipes in [qnx-ports](https://github.com/qnx-ports)
([build-files](https://github.com/qnx-ports/build-files)): a person adapts each library and writes its recipe.
qnx-porter generates a port and then tests it:
- it applies documented rules to the compiler's errors;
- every change is a patch with its reason;
- a library counts as ported only when its own tests run on a QNX target.

The two meet in three places:
- 21 of our 61 libraries also have a qnx-ports recipe. We compared them library by library in
  [docs/related/qnx-ports-comparison.md](docs/related/qnx-ports-comparison.md).
- For the 34 CMake ports that qnx-ports does not have, we generate recipes in their layout
  ([recipes/build-files/](recipes/build-files/)).
- The draft pull request text is in [docs/upstream/](docs/upstream/qnx-ports-build-files-PR.md). It has not
  been sent.

## For judges, start here
- **Demo video:** [`video/out/qnx-porter-demo.mp4`](video/out/qnx-porter-demo.mp4) (YouTube link: added at submission).
  Every command in it ran for real against the QNX 8.0 target; `video/make.sh` re-records it.
- **Evidence of QNX use:** see [Evidence of QNX use](#evidence-of-qnx-use) below. Every claim points at a file.
- **Headline** (written by `scripts/ports_csv.py`): <!-- headline:start -->x86_64: 57 of 61 libraries built for QNX 8.0; 1332 of 1366 of their own tests passed on a QNX 8.0 target (33 libraries with tests that ran); 25 patches, 25 by rules (29 of the 31 libraries oss.qnx.com does not list built).<!-- headline:end -->
  See [Results](#results-on-qnx-80).
- **Results:** [`results/ports.csv`](results/ports.csv), written by `scripts/ports_csv.py` from each
  port's own `ports/<library>/report.json`. No number in this README or the video comes from anywhere else.
- **Every patch the agent made:** `ports/<library>/patches/*.patch`, each with the rule, the reason and
  the exact compiler error it answers. `ports/<library>/REPORT.md` is the summary.
- **Which libraries QNX already ships:** the `on_oss_qnx_com` column of `results/ports.csv` (the campaign
  queries all of oss.qnx.com on every run). The first ten candidates were chosen as new to QNX:
  [`results/candidates_check.csv`](results/candidates_check.csv), written by `scripts/check_candidates.py`.
- **Checked against QNX's own hand-made ports:** 21 of our libraries also have a recipe in
  [qnx-ports](https://github.com/qnx-ports). [docs/related/qnx-ports-comparison.md](docs/related/qnx-ports-comparison.md)
  compares them library by library. It covers where we found the same QNX change, where QNX fixed something our
  run only reported, and where the two sides differ.
- Setup: [SETUP.md](SETUP.md). Tutorial: [docs/CODELAB.md](docs/CODELAB.md).

## Results on QNX 8.0
61 libraries, ported by `scripts/run_campaign.py` on 12 Nov 2026 with QNX SDP 8.0 (build 141, qcc 12.2.0).
Their own test suites ran on QNX 8.0 x86_64 in QEMU (`mkqnximage`). Rules only, no language model. The
libraries are infrastructure an embedded team reaches for: parsers (JSON, XML, YAML, CBOR, TOML), compression,
crypto and TLS, messaging (MQTT, nng, OPC UA, CoAP, Modbus), logging and formatting, test frameworks, codecs.
"none built" means the library's build registers no tests, or registers them only behind an option we left off.
"not run" means the suite needs something the target lacks (the Note says what). The table is generated from
`ports/*/report.json`:

<!-- results:start -->
| Library | Version | Arch | Build | Tests on QNX 8.0 | Patches (rule / model) | Minutes | Note |
|---|---|---|---|---|---|---|---|
| [BLAKE3](ports/BLAKE3/REPORT.md) | 1.5.4 | x86_64 | built | none built | 0 (0 / 0) | 0.1 | portable C: its CMake has SIMD flags only for compilers it knows, not qcc |
| [Micro-CDR](ports/Micro-CDR/REPORT.md) | v2.0.1 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [benchmark](ports/benchmark/REPORT.md) | v1.9.1 | x86_64 | built | none built | 0 (0 / 0) | 0.6 |  |
| [c-ares](ports/c-ares/REPORT.md) | v1.34.3 | x86_64 | built | none built | 0 (0 / 0) | 0.5 |  |
| [cJSON](ports/cJSON/REPORT.md) | v1.7.18 | x86_64 | built | 19/19 | 0 (0 / 0) | 0.5 |  |
| [can-utils](ports/can-utils/REPORT.md) | v2023.03 | x86_64 | failed | not run | 0 (0 / 0) | 0.1 | Linux SocketCAN tools: expected not to port |
| [capstone](ports/capstone/REPORT.md) | 5.0.3 | x86_64 | built | 24/24 | 1 (1 / 0) | 5.2 |  |
| [cglm](ports/cglm/REPORT.md) | v0.9.4 | x86_64 | built | 1/1 | 0 (0 / 0) | 0.5 |  |
| [cmark](ports/cmark/REPORT.md) | 0.31.1 | x86_64 | built | 1/1 | 0 (0 / 0) | 0.3 |  |
| [cmocka](ports/cmocka/REPORT.md) | cmocka-1.1.7 | x86_64 | built | 46/46 | 0 (0 / 0) | 0.4 |  |
| [expat](ports/expat/REPORT.md) | R_2_6_4 | x86_64 | built | 2/2 | 0 (0 / 0) | 2.5 |  |
| [flac](ports/flac/REPORT.md) | 1.4.3 | x86_64 | built | 7/10 | 1 (1 / 0) | 8.7 |  |
| [flatcc](ports/flatcc/REPORT.md) | v0.6.1 | x86_64 | built | not run | 0 (0 / 0) | 0.2 | build only: its tests run the just-built flatcc compiler on the build host |
| [fmt](ports/fmt/REPORT.md) | 11.0.2 | x86_64 | built | 17/20 | 1 (1 / 0) | 6.9 |  |
| [googletest](ports/googletest/REPORT.md) | v1.15.2 | x86_64 | built | 25/27 | 1 (1 / 0) | 9.8 |  |
| [inih](ports/inih/REPORT.md) | r58 | x86_64 | built | none built | 0 (0 / 0) | 0.2 |  |
| [jansson](ports/jansson/REPORT.md) | v2.14 | x86_64 | built | 209/213 | 1 (1 / 0) | 1.2 |  |
| [json-c](ports/json-c/REPORT.md) | json-c-0.18-20240915 | x86_64 | built | 25/25 | 1 (1 / 0) | 0.8 |  |
| [kissfft](ports/kissfft/REPORT.md) | 131.1.0 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [libcbor](ports/libcbor/REPORT.md) | v0.11.0 | x86_64 | built | none built | 0 (0 / 0) | 0.2 |  |
| [libccd](ports/libccd/REPORT.md) | v2.1 | x86_64 | built | 3/3 | 0 (0 / 0) | 0.3 |  |
| [libcoap](ports/libcoap/REPORT.md) | v4.3.5 | x86_64 | built | none built | 1 (1 / 0) | 0.7 |  |
| [libconfig](ports/libconfig/REPORT.md) | v1.7.3 | x86_64 | built | 1/1 | 1 (1 / 0) | 0.5 |  |
| [libdeflate](ports/libdeflate/REPORT.md) | v1.22 | x86_64 | built | none built | 0 (0 / 0) | 0.3 |  |
| [libevent](ports/libevent/REPORT.md) | release-2.1.12-stable | x86_64 | built | 20/24 | 2 (2 / 0) | 11.9 |  |
| [libgpiod](ports/libgpiod/REPORT.md) | v2.2.4 | x86_64 | failed | not run | 0 (0 / 0) | 0.3 | Linux GPIO character-device API: expected not to port |
| [libjpeg-turbo](ports/libjpeg-turbo/REPORT.md) | 3.0.4 | x86_64 | built | 590/590 | 0 (0 / 0) | 5.1 |  |
| [libmodbus](ports/libmodbus/REPORT.md) | v3.1.11 | x86_64 | built | 0/1 | 0 (0 / 0) | 1.0 |  |
| [libogg](ports/libogg/REPORT.md) | v1.3.5 | x86_64 | built | 2/2 | 0 (0 / 0) | 0.2 |  |
| [libpng](ports/libpng/REPORT.md) | v1.6.44 | x86_64 | built | none built | 1 (1 / 0) | 0.5 |  |
| [libsamplerate](ports/libsamplerate/REPORT.md) | 0.2.2 | x86_64 | built | 12/13 | 0 (0 / 0) | 0.5 |  |
| [libsodium](ports/libsodium/REPORT.md) | 1.0.20-RELEASE | x86_64 | built | 80/80 | 0 (0 / 0) | 6.0 |  |
| [libsrtp](ports/libsrtp/REPORT.md) | v2.6.0 | x86_64 | built | 8/12 | 1 (1 / 0) | 0.8 |  |
| [libtommath](ports/libtommath/REPORT.md) | v1.3.0 | x86_64 | built | 1/1 | 0 (0 / 0) | 0.4 |  |
| [libuv](ports/libuv/REPORT.md) | v1.49.2 | x86_64 | failed | not run | 0 (0 / 0) | 0.3 |  |
| [libwebsockets](ports/libwebsockets/REPORT.md) | v4.3.3 | x86_64 | failed | not run | 1 (1 / 0) | 0.8 |  |
| [libxml2](ports/libxml2/REPORT.md) | v2.13.5 | x86_64 | built | 7/8 | 0 (0 / 0) | 2.3 |  |
| [libyaml](ports/libyaml/REPORT.md) | 0.2.5 | x86_64 | built | 2/2 | 0 (0 / 0) | 0.2 |  |
| [lz4](ports/lz4/REPORT.md) | v1.10.0 | x86_64 | built | none built | 0 (0 / 0) | 0.5 |  |
| [mbedtls](ports/mbedtls/REPORT.md) | v3.6.2 | x86_64 | built | 130/130 | 1 (1 / 0) | 4.6 |  |
| [miniz](ports/miniz/REPORT.md) | 3.0.2 | x86_64 | built | none built | 0 (0 / 0) | 0.2 |  |
| [mosquitto](ports/mosquitto/REPORT.md) | v2.0.20 | x86_64 | built | none built | 1 (1 / 0) | 0.5 |  |
| [msgpack-c](ports/msgpack-c/REPORT.md) | c-6.1.0 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [nanopb](ports/nanopb/REPORT.md) | 0.4.9 | x86_64 | built | not run | 0 (0 / 0) | 0.0 | build only: its tests use scons and protoc |
| [nng](ports/nng/REPORT.md) | v1.9.0 | x86_64 | built | 82/86 | 1 (1 / 0) | 4.3 |  |
| [open62541](ports/open62541/REPORT.md) | v1.4.6 | x86_64 | built | none built | 0 (0 / 0) | 2.4 |  |
| [opus](ports/opus/REPORT.md) | v1.5.2 | x86_64 | built | none built | 0 (0 / 0) | 0.5 |  |
| [paho.mqtt.c](ports/paho.mqtt.c/REPORT.md) | v1.3.14 | x86_64 | built | not run | 3 (3 / 0) | 0.4 | build only: the test suite needs an MQTT broker on the target |
| [pcre2](ports/pcre2/REPORT.md) | pcre2-10.44 | x86_64 | built | 1/3 | 0 (0 / 0) | 0.7 |  |
| [pugixml](ports/pugixml/REPORT.md) | v1.14 | x86_64 | built | 0/1 | 0 (0 / 0) | 0.9 |  |
| [spdlog](ports/spdlog/REPORT.md) | v1.15.0 | x86_64 | built | none built | 1 (1 / 0) | 0.7 |  |
| [sqlite](ports/sqlite/REPORT.md) | version-3.47.2 | x86_64 | built | not run | 0 (0 / 0) | 2.7 | build only: its test suite needs Tcl on the target |
| [tinycbor](ports/tinycbor/REPORT.md) | v0.6.0 | x86_64 | built | not run | 0 (0 / 0) | 0.0 |  |
| [tinyxml2](ports/tinyxml2/REPORT.md) | 10.0.0 | x86_64 | built | 1/1 | 1 (1 / 0) | 0.4 |  |
| [tomlplusplus](ports/tomlplusplus/REPORT.md) | v3.4.0 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [wolfssl](ports/wolfssl/REPORT.md) | v5.7.4-stable | x86_64 | built | 1/1 | 2 (2 / 0) | 1.9 |  |
| [xxHash](ports/xxHash/REPORT.md) | v0.8.2 | x86_64 | built | none built | 0 (0 / 0) | 0.2 |  |
| [yaml-cpp](ports/yaml-cpp/REPORT.md) | 0.8.0 | x86_64 | built | 0/1 | 1 (1 / 0) | 5.0 |  |
| [yyjson](ports/yyjson/REPORT.md) | 0.10.0 | x86_64 | built | 12/12 | 1 (1 / 0) | 1.5 |  |
| [zlib](ports/zlib/REPORT.md) | v1.3.1 | x86_64 | built | 2/2 | 0 (0 / 0) | 0.3 |  |
| [zstd](ports/zstd/REPORT.md) | v1.5.6 | x86_64 | built | 1/4 | 0 (0 / 0) | 9.2 |  |
<!-- results:end -->

**What the failures are.** Each one was reproduced outside the campaign before being named. Details are in
[docs/LEARNINGS.md](docs/LEARNINGS.md), each test's QNX output is in `ports/<library>/logs/tests.log`, and the
reproducers are in [docs/qnx-reports/](docs/qnx-reports/):
- **QNX C library behaviour** (draft reports, not sent):
  - `strtod()` is not correctly rounded (pugixml, jansson, yaml-cpp).
  - `strftime()` writes nothing for `%Ex`/`%EX`/`%Ec` (fmt).
  - `fchdir()` needs `O_DIRECTORY` (googletest's death tests). QNX documents this.
  - `qsort()` writes outside the array when the comparator is inconsistent (libsrtp's tests use a random
    comparator).
- **Undefined C that glibc tolerates:** `printf("%s", NULL)`. The agent reads the core dump and fixes it in
  json-c, libconfig, tinyxml2 and capstone (all now pass). It finds the same thing but cannot place the fix
  in libxml2 (library code) and nng (behind a tail call).
- **What the test image lacks:** `killall` (libmodbus), `/bin/echo` (pcre2grep), internet access (nng),
  2 GiB of memory for one zstd test, a `locale` command (pcre2 skips those tests), Tcl (sqlite), an MQTT
  broker (paho), cmake on the target (libpng's tests are CMake scripts).
- **Did not build** (4): libgpiod and can-utils use Linux-only kernel interfaces, as expected. libuv
  (`struct qtime_entry` has no `nsec` in QNX 8.0) and libwebsockets (`TCPCTL_KEEPCNT`) stop on errors no rule
  covers yet. QNX's own ports of these two libraries change exactly those lines.

**How we got here** (each line is the summary the campaign script printed; logs in [`results/runs/`](results/runs/)):

| Run | Built | Tests passed on QNX | What we changed before the next run |
|---|---|---|---|
| 1 | 4/10 | 68/72 | CMake ignored flag fixes after round 1; autotools configured in the wrong folder; new rules for libm, `__inet_pton`, `<sys/errno.h>`, `bool` |
| 2 | 9/10 | 292/381 | automake test programs were never copied to QNX; `.sh` tests ran on Linux |
| 3 | 9/10 | 372/381 | a proved fix was reverted when it let the link step run; endian names from `<net/netbyte.h>` |
| 4 | 10/10 | 372/381 | CMake pass regexes need DOTALL (cmocka re-run: 46/46) |
| 5 (json-c, libconfig only) | 2/2 | 26/26 | crash triage from QNX core dumps + `printf-null` rule (both crashes were `printf("%s", NULL)`) |
| 6 (61 libraries) | 50/61 | 1185/1345 | `cmake -E` test helpers run as QNX shell commands; rules `wcswidth-compat`, `qcc-sysroot`; a resolv.conf on the target |
| 7 (61 libraries) | 57/61 | 1332/1366 | final run; re-runs into the same log: 6 libraries after a DNS outage, sqlite without editline, CRLF-safe and MSVC-safe `printf-null` patches, libccd once CMake could find the stub `librt` |

Runs 6 and 7 count tests the way the campaign script did on the day. Run 6 counted libraries whose suite
registered no tests as "tests ran". Since run 7, the summary and the headline count only libraries with at
least one test.


## How it works
The full pipeline as a diagram, one box per source file: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
```
git URL + tag
   │
   ▼
detect build system ──► CMake | Meson | autotools | Make
   │
   ▼
generate QNX toolchain ──► qnx-toolchain.cmake (qcc -Vgcc_ntox86_64, sysroot $QNX_TARGET)
   │                       qnx-cross.ini (meson) | --host=x86_64-pc-nto-qnx8.0.0 (autotools)
   ▼
build ──► parse GCC / ld / CMake / configure errors
   │            │
   │            ├─ deterministic rule? ──► patch + reason ──┐
   │            ├─ else model (optional) ──► diff, git apply --check, kept only if the rebuild clears it
   │            └─ else stop, report what is left and why   │
   ◄────────────────────────────── rebuild ◄────────────────┘
   │
   ▼
tests on the QNX 8.0 target ──► ctest / meson test / make check, each test binary run over ssh
   │
   ▼
ports/<library>/  REPORT.md · report.json · patches/ · qnx.patch · toolchain file · logs/
```

**Rules first.** Each rule acts only on what the compiler or linker said, plus facts about QNX's libc:

| Rule | Fires on | Change |
|---|---|---|
| `add-include` | implicit declaration / undeclared symbol | `#include` the header GCC's own note names, or the POSIX header from a table |
| `qnx-source` | the header is already included but the symbol is hidden | `-D_QNX_SOURCE` |
| `link-libsocket` | `undefined reference to socket/getaddrinfo/...` | `-lsocket` (QNX keeps sockets in libsocket) |
| `stub-lib` | `cannot find -lpthread/-lrt/-ldl` | an empty archive, because QNX has these in libc |
| `no-werror` | a warning promoted by `-Werror` | `-Wno-error=<that warning>` |
| `guard-linux-header` | `<sys/epoll.h>`, `<sys/sendfile.h>`, ... missing and unused by the file | `#ifndef __QNX__` around the include |
| `byteswap-builtins`, `prctl-set-name`, `pthread-setname*` | `<byteswap.h>`, `prctl(PR_SET_NAME)`, BSD/macOS thread-name calls | QNX's `__builtin_bswap*`, `pthread_setname_np(tid, name)` |
| `qnx-platform-guard` | `#error "Unsupported platform"` after an OS `#if` chain | QNX joins the BSD/Unix branch; kept only if the rebuild proves it |
| `map-anon`, `msg-nosignal`, `link-libfsnotify`, `fcommon` | `MAP_ANONYMOUS`, `MSG_NOSIGNAL`, inotify, GCC 12 `-fno-common` | see the corpus |

All 35 patterns, where each QNX fact comes from, and the test for each:
[docs/LINUX_ISMS.md](docs/LINUX_ISMS.md). Linux-only code that is actually *used* (epoll loops, sendfile)
is never rewritten by a rule; it goes to the model with a QNX-specific hint, or is reported as blocked.

**The model is optional and checked.** Set `QNX_PORTER_API_KEY` and `QNX_PORTER_MODEL` (any
OpenAI-compatible endpoint, set with `QNX_PORTER_BASE_URL`). It must answer with a unified diff and
a one-sentence reason. The diff must pass `git apply --check`; after the rebuild, if the error it targeted
is still there or the error count grew, the agent reverts it and marks it `reverted` in the report.

## Evidence of QNX use
The path from "a git URL" to "tests passed on QNX 8.0", function by function:

| Step | What touches QNX | Exact place |
|---|---|---|
| 1. Find the SDP | sources `~/qnx800/qnxsdp-env.sh` to get `QNX_HOST` and `QNX_TARGET` | [`qnx.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/qnx.py) `sdp_env()` |
| 2. Check it | runs `qcc -V` and looks for `gcc_ntox86_64`; checks the `x86_64-pc-nto-qnx8.0.0-gcc` drivers | `qnx.py` `doctor()` (CLI: `qnx-porter doctor`) |
| 3. Write the QNX toolchain | CMake: `CMAKE_SYSTEM_NAME QNX`, `CMAKE_C_COMPILER $QNX_HOST/usr/bin/qcc`, `CMAKE_C_COMPILER_TARGET gcc_ntox86_64`, `CMAKE_SYSROOT $QNX_TARGET`. Meson: a cross file with `system = 'qnx'`. Autotools: `--host=x86_64-pc-nto-qnx8.0.0` | `qnx.py` `cmake_toolchain()`, `meson_cross()`, `gnu_env()`, `ARCHES`; saved per port as `ports/<library>/qnx-toolchain.cmake` |
| 4. Invoke qcc | the configure and build commands that drive qcc through that toolchain; output goes to `ports/<library>/logs/round-NN.log` | [`build.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/build.py) `Job.steps()` builds the commands, `run()` executes them; called from [`agent.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/agent.py) `port()` |
| 5. Fix what QNX rejects | 35 Linux-isms and the QNX 8.0 answer to each (libsocket, libfsnotify, libc-provided pthread/rt/dl, `MAP_ANON`, `pthread_setname_np`, `<process.h>`, `_QNX_SOURCE`, ...), sourced from QNX's 8.0 documentation | [`fixes.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/fixes.py) `_rule()`, [`linuxisms.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/linuxisms.py); sources per fact in [docs/LINUX_ISMS.md](docs/LINUX_ISMS.md) |
| 6. Start the QNX target | QEMU image made by QNX's `mkqnximage --type=qemu --arch=x86_64` from the SDP | [SETUP.md](SETUP.md) step 4 |
| 7. Run tests on QNX | copies the build to the target (`tar` over ssh), then ctest / meson test / make check run every test binary on QNX through a generated wrapper (`CMAKE_CROSSCOMPILING_EMULATOR`, meson `exe_wrapper`, automake `LOG_COMPILER`) | [`target.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/target.py) `Target.sync()`, `write_wrapper()`, `remote_command()`, `main()`; output `ports/<library>/logs/tests.log` |
| 8. Record the target | `uname -a` from the QNX target in every report | `target.py` `Target.uname()`; `ports/<library>/report.json` field `target` |
| 9. One command for all of it | stops early if `qcc` or the target is missing | [`scripts/run_campaign.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/scripts/run_campaign.py) `preflight()`, `check_target()` |

Real output from our runs (11 Nov 2026):
```
$ qnx-porter doctor                      # on the build host, WSL Ubuntu 22.04
ok  qcc          /home/chirag/qnx800/host/linux/x86_64/usr/bin/qcc
ok  qcc targets  cc: targets available in /home/chirag/qnx800/host/linux/x86_64/etc/qcc: ...
ok  SDP complete no empty compiler or libc files
ok  qcc builds hello ok
$ ssh root@172.31.1.11 uname -a          # the QEMU target
QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
$ tail -1 ports/mbedtls/logs/tests.log   # written by ctest_on_target()
130/130 tests passed on the QNX target
```
The one patch mbedtls needed, as the agent wrote it ([`ports/mbedtls/patches/0001-link-libsocket.patch`](ports/mbedtls/patches/0001-link-libsocket.patch)):
```
Subject: [qnx-porter 0001] link-libsocket
Source: deterministic rule
Reason: `__inet_pton` is in QNX's libsocket, not in libc as on Linux: link with -lsocket.
Error: x509_crt.c:(.text+0x843): undefined reference to `__inet_pton'
```

## Why a real-time OS needs this tooling
- **Nothing builds on the target.** A QNX system in a car, a robot or a medical device has no compiler; every
  library is cross-compiled with qcc against the SDP's sysroot. On Linux you can `./configure && make` on the
  machine itself. On QNX, each library needs a cross toolchain file and build flags first, and most upstream
  projects ship neither.
- **The host cannot run what it built.** QNX binaries do not run on the build machine, so "it compiled" proves
  little. qnx-porter runs the library's own tests on a QNX 8.0 target and counts only those results.
- **QNX's libc is POSIX, not glibc.** Linux code relies on things glibc adds (implicit headers, `epoll`,
  `prctl`, sockets in libc), so the same breakages come back in every library. That is why the fixes can be
  rules, collected once in [docs/LINUX_ISMS.md](docs/LINUX_ISMS.md).
- **The markets QNX serves review every change.** Automotive, medical and industrial teams cannot take a
  silently patched dependency. Every change here is a separate patch with the rule, the reason and the
  compiler error that caused it. Rules run the same way every time, and a model's patch is reverted unless the
  rebuild proves it. This is a review aid, not a safety certification.
- **The libraries chosen are the ones those systems need:** TLS (mbedtls), crypto (libsodium), MQTT
  (paho.mqtt.c), Modbus (libmodbus), messaging (nng), CBOR and JSON. None was on oss.qnx.com when checked
  ([results/candidates_check.csv](results/candidates_check.csv)).

## Quick start
```bash
python3 -m pip install --user --upgrade pip   # Ubuntu 22.04's pip 22 cannot do editable installs
python3 -m pip install --user -e ".[test]"
python3 -m pytest -q                                   # no QNX needed
source ~/qnx800/qnxsdp-env.sh && qnx-porter doctor
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11
python3 scripts/run_campaign.py                       # every library in campaign.yaml, then the CSV
```
Build and run requirements: **QNX SDP 8.0**, target **x86_64 QEMU** (from `mkqnximage`) or **aarch64le**
hardware with ssh, toolchain **qcc / GCC from SDP 8.0**, host **Ubuntu 22.04/24.04 or WSL2**. Details: [SETUP.md](SETUP.md).

## Known limits
- Linux host only (WSL2 on Windows), because QNX's QEMU tooling is Ubuntu-only.
- Tests that need a network peer or root-only devices are counted as they run; nothing is excluded by hand.
- A rule never rewrites Linux-only code (epoll, inotify, ...). That is the model's job, or a person's.
- The model is never trusted: a diff that does not clear its error is reverted and shown as reverted.

## Licence
Apache-2.0. Patches produced for a library are offered under that library's own licence.
