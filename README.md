# qnx-porter

[![tests](https://github.com/thegoodengineers/qnx-porter/actions/workflows/test.yml/badge.svg)](https://github.com/thegoodengineers/qnx-porter/actions/workflows/test.yml)

**qnx-porter cross-compiles an open-source C/C++ library or Rust crate for QNX 8.0 with the SDP's `qcc`, fixes
what breaks with one reviewable patch per change, and counts the port only when the library's own tests pass on
a QNX 8.0 target.**

Built for the [QNX Global Hackathon](https://qnx.devpost.com/) (Developer Tooling & Host Tools) by
Chirag, Bhumika, Ayush and Abhijeet (The Good Engineers).

## Results at a glance
Every target is QNX 8.0 in QEMU: x86_64 under KVM, and aarch64 on QEMU `virt` (emulated). No hardware was used.
Each line links the generated file its numbers come from.
- **C/C++ libraries, x86_64 and aarch64 on QEMU:** how many built, and how many of their own tests passed on
  QNX 8.0, is the [headline](#for-judges-start-here), written by `scripts/ports_csv.py`. Every library, test
  count and patch: [Results](#results-on-qnx-80) and [`results/ports.csv`](results/ports.csv).
- **The language-model step, measured** ([docs/MODEL_STEP.md](docs/MODEL_STEP.md)): no rule could build libuv
  or libwebsockets at their 2024 pins; with the model step, "2 of the 2 libraries the rules could not build now
  build. Model patches kept: 2, reverted: 0." The model's libuv fix makes the same two changes as upstream
  libuv's own QNX change, [PR #4801](https://github.com/libuv/libuv/pull/4801), which the model never saw.
- **Rust crates** ([docs/rust/CRATES.md](docs/rust/CRATES.md)): x86_64, 21 of 22 crates built and 2751 of 2764
  of their own tests passed; aarch64 on QEMU `virt`, 21 of 22 built and 2721 of 2733 passed.
- **Real-time** ([docs/RT_RESULTS.md](docs/RT_RESULTS.md)): a static hazard scan of every library, and the
  latency of one call for 14 libraries at SCHED_FIFO priority 60: idle, under load, and under load with the
  measuring thread isolated by a QNX runmask. zlib, the one library where isolation at least halved loaded p99,
  went from 139.248 to 24.535 us. Measured in QEMU on a laptop: it ranks libraries, it guarantees no latency.
- **Against QNX's own ports** ([comparison](docs/related/qnx-ports-comparison.md)): library by library against
  QNX's hand-made qnx-ports recipes: where qnx-porter found the same QNX change on its own, and where QNX fixed
  what our run only reported.
- **Recipes for QNX's build-files** ([recipes/BUILD_CHECK.md](recipes/BUILD_CHECK.md)): generated in
  qnx-ports/build-files layout for CMake ports QNX does not have, each built with QNX's recursive make.
- **SBOM and licences** ([docs/LICENCES.md](docs/LICENCES.md)): an SPDX SBOM per port with our `qnx.patch` and
  its hash ([example](ports/mbedtls/sbom.spdx.json)), and a copyleft flag per library.
- **Codelab** ([web page](https://thegoodengineers.github.io/qnx-porter/codelab-port-a-library.html),
  [source](docs/codelab/port-a-library.md)): port a CMake C library to QNX 8.0 and run its own tests in QEMU.
- **What you get per library** (json-c as the example): [patches with their reasons](ports/json-c/patches/),
  one [`qnx.patch`](ports/json-c/qnx.patch), a [CMake toolchain file](ports/json-c/qnx-toolchain.cmake), the
  per-test [QNX log](ports/json-c/logs/tests.log) and [JUnit XML](ports/json-c/logs/tests.junit.xml), the
  [crash triage](ports/json-c/logs/crashes.log) from QNX core dumps, an [SPDX SBOM](ports/json-c/sbom.spdx.json),
  and a [REPORT.md](ports/json-c/REPORT.md) that says what changed and why.
- **Install:** `python3 -m pip install --user qnx-porter`. **Website:**
  [thegoodengineers.github.io/qnx-porter](https://thegoodengineers.github.io/qnx-porter/).

Not done: no real hardware; the upstream reports and pull requests are drafted, not sent. Everything else that
is missing, with numbers: [docs/LIMITATIONS.md](docs/LIMITATIONS.md).

## For judges, start here
- **Demo video:** [`video/out/qnx-porter-demo.mp4`](video/out/qnx-porter-demo.mp4) (YouTube link: added at submission).
  Every command in it ran for real against the QNX 8.0 target; `video/make.sh` re-records it.
- **Evidence of QNX use:** see [Evidence of QNX use](#evidence-of-qnx-use) below. Every claim points at a file.
- **Headline** (written by `scripts/ports_csv.py`): <!-- headline:start -->aarch64le: 58 of 61 libraries built for QNX 8.0; 1546 of 1642 of their own tests passed on a QNX 8.0 target (43 libraries with tests that ran); 32 patches, 32 by rules (29 of the 31 libraries oss.qnx.com does not list built); x86_64: 58 of 61 libraries built for QNX 8.0; 1563 of 1658 of their own tests passed on a QNX 8.0 target (43 libraries with tests that ran); 31 patches, 31 by rules (29 of the 31 libraries oss.qnx.com does not list built).<!-- headline:end -->
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
- Codelab: [Port a CMake C library to QNX 8.0 and run its own tests on a QEMU target](docs/codelab/port-a-library.md) ([web page](https://thegoodengineers.github.io/qnx-porter/codelab-port-a-library.html)).

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
- zlib v1.4: built, 4/4 tests pass on QNX 8.0 x86_64 (12 more are CMake packaging checks that need cmake on
  the target).
- libsodium 1.0.22: built, 101/101 tests pass.
- sqlite 3.54.1: built. Its test suite needs Tcl on the target, so it was not run.

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

**QNX's agent skills.** QNX also publishes [qnx-agent-skills](https://github.com/qnx/qnx-agent-skills)
([codelab](https://qnx.github.io/codelabs/qnx-agent-skills/index.html)): instructions that turn a general coding
agent into a QNX 8.0 porting companion. It builds natively on a self-hosted QNX target with Alpine's `abuild`, and
it packages the result as an `apk`. The two tools are complementary:

| | qnx-agent-skills | qnx-porter |
|---|---|---|
| Where it builds | on the QNX target, with the target's own toolchain | on the host, cross-compiled with the SDP's `qcc`, as product teams build |
| Who changes the source | the coding agent, guided by its skills | documented rules first; a language model only for errors no rule covers, and only if qcc and the target accept the change |
| Tests | `abuild`'s check step | the library's own registered suite (ctest, meson, make check) runs test by test on the target; results go to `tests.log` and JUnit XML |
| Output | an `apk`, a REPORT.md | patches with reasons, a toolchain file, a qnx-ports recipe, an SPDX SBOM, a REPORT.md |

A port qnx-porter makes can be the starting point for an `APKBUILD`. We have not built that bridge.

## Results on QNX 8.0
61 libraries, ported by `scripts/run_campaign.py` with QNX SDP 8.0 (build 141, qcc 12.2.0) for two
architectures:
- **x86_64:** on 13 Nov 2026, at the newest release tag of each library ([`campaign.yaml`](campaign.yaml)),
  with tests on QNX 8.0 x86_64 in QEMU under KVM. Log: [`results/runs/campaign-8.log`](results/runs/campaign-8.log).
- **aarch64le:** on 14 Nov 2026, at the same newest release tags, with tests on QNX 8.0 aarch64 on QEMU `virt`,
  fully emulated. Log: [`results/runs/campaign-aarch64-3.log`](results/runs/campaign-aarch64-3.log) (the run,
  then a rerun of cJSON after the main-stack rule was made to read 24 backtrace frames).

The two architectures differ in four libraries only: mbedtls 147/148 on aarch64 (its PBKDF2 suite was killed at
the 300 s per-test limit on the emulated target; it passes on x86_64), flac 6/10 against 7/10, libsrtp 9/12
against 8/12, and libjpeg-turbo 646/646 against 662/662 (`results/ports.csv`).

The results at the 2024 tags (12–13 Nov 2026) are kept in [`ports-2024/`](ports-2024/) (x86_64, run 7) and
[`ports-aarch64le-2024/`](ports-aarch64le-2024/) (aarch64): the codelab, the video and the upstream drafts quote
them.

Both targets were built with `mkqnximage`. Rules only, no language model. The
libraries are infrastructure an embedded team reaches for: parsers (JSON, XML, YAML, CBOR, TOML), compression,
crypto and TLS, messaging (MQTT, nng, OPC UA, CoAP, Modbus), logging and formatting, test frameworks, codecs.
"none built" means the library's build registers no tests, or registers them only behind an option we left off.
"not run" means the suite needs something the target lacks (the Note says what). The table is generated from
`ports/*/report.json`:

<!-- results:start -->
| Library | Version | Arch | Build | Tests on QNX 8.0 | Patches (rule / model) | Minutes | Note |
|---|---|---|---|---|---|---|---|
| [BLAKE3](ports/BLAKE3/REPORT.md) | 1.8.7 | x86_64 | built | none built | 0 (0 / 0) | 0.2 | portable C: its CMake has SIMD flags only for compilers it knows, not qcc |
| [Micro-CDR](ports/Micro-CDR/REPORT.md) | v2.0.2 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [benchmark](ports/benchmark/REPORT.md) | v1.10.0 | x86_64 | built | 85/87 | 0 (0 / 0) | 6.0 |  |
| [c-ares](ports/c-ares/REPORT.md) | v1.34.9 | x86_64 | built | 2/3 | 0 (0 / 0) | 5.8 |  |
| [cJSON](ports/cJSON/REPORT.md) | v1.7.19 | x86_64 | built | 19/19 | 1 (1 / 0) | 0.8 |  |
| [can-utils](ports/can-utils/REPORT.md) | v2025.01 | x86_64 | needs-qnx-equivalent | not run | 2 (2 / 0) | 0.1 | Linux SocketCAN tools: expected not to port |
| [capstone](ports/capstone/REPORT.md) | 5.0.9 | x86_64 | built | 24/24 | 1 (1 / 0) | 4.1 |  |
| [cglm](ports/cglm/REPORT.md) | v0.9.7 | x86_64 | built | 1/1 | 0 (0 / 0) | 0.6 |  |
| [cmark](ports/cmark/REPORT.md) | 0.31.2 | x86_64 | built | 1/1 | 0 (0 / 0) | 0.3 |  |
| [cmocka](ports/cmocka/REPORT.md) | cmocka-2.0.2 | x86_64 | built | 88/89 | 1 (1 / 0) | 2.7 |  |
| [expat](ports/expat/REPORT.md) | R_2_10_0 | x86_64 | built | 1/1 | 0 (0 / 0) | 2.1 |  |
| [flac](ports/flac/REPORT.md) | 1.5.0 | x86_64 | built | 7/10 | 1 (1 / 0) | 9.1 |  |
| [flatcc](ports/flatcc/REPORT.md) | v0.6.4 | x86_64 | built | not run | 0 (0 / 0) | 0.2 | build only: its tests run the just-built flatcc compiler on the build host |
| [fmt](ports/fmt/REPORT.md) | 12.2.1 | x86_64 | built | 20/21 | 1 (1 / 0) | 10.2 |  |
| [googletest](ports/googletest/REPORT.md) | v1.18.0 | x86_64 | built | 25/27 | 1 (1 / 0) | 13.9 |  |
| [inih](ports/inih/REPORT.md) | r63 | x86_64 | built | 17/17 | 0 (0 / 0) | 0.7 |  |
| [jansson](ports/jansson/REPORT.md) | v2.15.1 | x86_64 | built | 211/215 | 1 (1 / 0) | 1.1 |  |
| [json-c](ports/json-c/REPORT.md) | json-c-0.19-20260627 | x86_64 | built | 28/28 | 1 (1 / 0) | 1.3 |  |
| [kissfft](ports/kissfft/REPORT.md) | 131.2.0 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [libcbor](ports/libcbor/REPORT.md) | v0.14.0 | x86_64 | built | 28/28 | 0 (0 / 0) | 0.6 |  |
| [libccd](ports/libccd/REPORT.md) | v2.1 | x86_64 | built | 3/3 | 0 (0 / 0) | 0.3 |  |
| [libcoap](ports/libcoap/REPORT.md) | v4.3.5b | x86_64 | built | none built | 1 (1 / 0) | 0.8 |  |
| [libconfig](ports/libconfig/REPORT.md) | v1.8.3 | x86_64 | built | 1/1 | 1 (1 / 0) | 0.5 |  |
| [libdeflate](ports/libdeflate/REPORT.md) | v1.26 | x86_64 | built | 8/8 | 0 (0 / 0) | 0.4 |  |
| [libevent](ports/libevent/REPORT.md) | release-2.1.13-stable | x86_64 | built | 20/24 | 2 (2 / 0) | 10.2 |  |
| [libgpiod](ports/libgpiod/REPORT.md) | v2.3.2 | x86_64 | needs-qnx-equivalent | not run | 0 (0 / 0) | 0.9 | Linux GPIO character-device API: expected not to port |
| [libjpeg-turbo](ports/libjpeg-turbo/REPORT.md) | 3.2.1 | x86_64 | built | 662/662 | 0 (0 / 0) | 7.8 |  |
| [libmodbus](ports/libmodbus/REPORT.md) | v3.2.0 | x86_64 | built | 0/1 | 0 (0 / 0) | 0.6 |  |
| [libogg](ports/libogg/REPORT.md) | v1.3.6 | x86_64 | built | 2/2 | 0 (0 / 0) | 0.2 |  |
| [libpng](ports/libpng/REPORT.md) | v1.6.59 | x86_64 | built | none built | 1 (1 / 0) | 0.6 |  |
| [libsamplerate](ports/libsamplerate/REPORT.md) | 0.2.2 | x86_64 | built | 12/13 | 0 (0 / 0) | 0.4 |  |
| [libsodium](ports/libsodium/REPORT.md) | 1.0.22-RELEASE | x86_64 | built | 101/101 | 0 (0 / 0) | 3.9 |  |
| [libsrtp](ports/libsrtp/REPORT.md) | v2.8.1 | x86_64 | built | 8/12 | 1 (1 / 0) | 7.3 |  |
| [libtommath](ports/libtommath/REPORT.md) | v1.3.0 | x86_64 | built | 1/1 | 0 (0 / 0) | 0.6 |  |
| [libuv](ports/libuv/REPORT.md) | v1.53.0 | x86_64 | built | 0/2 | 1 (1 / 0) | 5.3 |  |
| [libwebsockets](ports/libwebsockets/REPORT.md) | v5.1.0 | x86_64 | failed | not run | 1 (1 / 0) | 2.6 |  |
| [libxml2](ports/libxml2/REPORT.md) | v2.15.4 | x86_64 | built | 7/8 | 0 (0 / 0) | 2.6 |  |
| [libyaml](ports/libyaml/REPORT.md) | 0.2.5 | x86_64 | built | 2/2 | 0 (0 / 0) | 0.2 |  |
| [lz4](ports/lz4/REPORT.md) | v1.11.1 | x86_64 | built | none built | 0 (0 / 0) | 0.5 |  |
| [mbedtls](ports/mbedtls/REPORT.md) | v4.2.0 | x86_64 | built | 148/148 | 1 (1 / 0) | 12.5 |  |
| [miniz](ports/miniz/REPORT.md) | 3.1.2 | x86_64 | built | 1/1 | 0 (0 / 0) | 3.3 |  |
| [mosquitto](ports/mosquitto/REPORT.md) | v2.1.2 | x86_64 | built | none built | 3 (3 / 0) | 0.9 | 2.1 needs cJSON (our QNX port of it) and, on QNX, TLS: without it 2.1 has random bytes only from Linux getrandom(); OpenSSL from the SDP. Its tests need CUnit and a Python broker harness |
| [msgpack-c](ports/msgpack-c/REPORT.md) | c-7.0.2 | x86_64 | built | 5/5 | 0 (0 / 0) | 1.5 |  |
| [nanopb](ports/nanopb/REPORT.md) | 0.4.9.3 | x86_64 | built | not run | 0 (0 / 0) | 0.0 | build only: its tests use scons and protoc |
| [nng](ports/nng/REPORT.md) | v2.1.0 | x86_64 | built | 3/64 | 1 (1 / 0) | 188.2 |  |
| [open62541](ports/open62541/REPORT.md) | v1.5.10 | x86_64 | built | none built | 2 (2 / 0) | 1.9 |  |
| [opus](ports/opus/REPORT.md) | v1.6.1 | x86_64 | built | none built | 0 (0 / 0) | 0.6 |  |
| [paho.mqtt.c](ports/paho.mqtt.c/REPORT.md) | v1.3.16 | x86_64 | built | not run | 1 (1 / 0) | 0.3 | build only: the test suite needs an MQTT broker on the target |
| [pcre2](ports/pcre2/REPORT.md) | pcre2-10.49 | x86_64 | built | 1/3 | 0 (0 / 0) | 0.9 |  |
| [pugixml](ports/pugixml/REPORT.md) | v1.16 | x86_64 | built | 0/1 | 0 (0 / 0) | 0.9 |  |
| [spdlog](ports/spdlog/REPORT.md) | v1.17.0 | x86_64 | built | 1/1 | 1 (1 / 0) | 4.0 |  |
| [sqlite](ports/sqlite/REPORT.md) | version-3.54.1 | x86_64 | built | not run | 0 (0 / 0) | 1.9 | build only: its test suite needs Tcl on the target |
| [tinycbor](ports/tinycbor/REPORT.md) | v7.1 | x86_64 | built | 1/1 | 2 (2 / 0) | 0.3 |  |
| [tinyxml2](ports/tinyxml2/REPORT.md) | 11.0.0 | x86_64 | built | 1/1 | 1 (1 / 0) | 0.8 |  |
| [tomlplusplus](ports/tomlplusplus/REPORT.md) | v3.4.0 | x86_64 | built | none built | 0 (0 / 0) | 0.1 |  |
| [wolfssl](ports/wolfssl/REPORT.md) | v5.9.4-stable | x86_64 | built | 1/1 | 1 (1 / 0) | 2.5 |  |
| [xxHash](ports/xxHash/REPORT.md) | v0.8.4 | x86_64 | built | none built | 0 (0 / 0) | 0.2 |  |
| [yaml-cpp](ports/yaml-cpp/REPORT.md) | yaml-cpp-0.9.0 | x86_64 | built | 0/1 | 0 (0 / 0) | 7.1 |  |
| [yyjson](ports/yyjson/REPORT.md) | 0.13.0 | x86_64 | built | 12/12 | 0 (0 / 0) | 2.0 |  |
| [zlib](ports/zlib/REPORT.md) | v1.4 | x86_64 | built | 4/4 | 0 (0 / 0) | 0.3 |  |
| [zstd](ports/zstd/REPORT.md) | v1.5.7 | x86_64 | built | 1/4 | 0 (0 / 0) | 10.0 |  |
| [BLAKE3](ports-aarch64le/BLAKE3/REPORT.md) | 1.8.7 | aarch64le | built | none built | 0 (0 / 0) | 0.6 | portable C: its CMake has SIMD flags only for compilers it knows, not qcc |
| [Micro-CDR](ports-aarch64le/Micro-CDR/REPORT.md) | v2.0.2 | aarch64le | built | none built | 0 (0 / 0) | 0.9 |  |
| [benchmark](ports-aarch64le/benchmark/REPORT.md) | v1.10.0 | aarch64le | built | 85/87 | 0 (0 / 0) | 21.0 |  |
| [c-ares](ports-aarch64le/c-ares/REPORT.md) | v1.34.9 | aarch64le | built | 2/3 | 0 (0 / 0) | 11.3 |  |
| [cJSON](ports-aarch64le/cJSON/REPORT.md) | v1.7.19 | aarch64le | built | 19/19 | 1 (1 / 0) | 3.6 |  |
| [can-utils](ports-aarch64le/can-utils/REPORT.md) | v2025.01 | aarch64le | needs-qnx-equivalent | not run | 2 (2 / 0) | 0.1 | Linux SocketCAN tools: expected not to port |
| [capstone](ports-aarch64le/capstone/REPORT.md) | 5.0.9 | aarch64le | built | 24/24 | 1 (1 / 0) | 16.6 |  |
| [cglm](ports-aarch64le/cglm/REPORT.md) | v0.9.7 | aarch64le | built | 1/1 | 0 (0 / 0) | 2.7 |  |
| [cmark](ports-aarch64le/cmark/REPORT.md) | 0.31.2 | aarch64le | built | 1/1 | 0 (0 / 0) | 0.9 |  |
| [cmocka](ports-aarch64le/cmocka/REPORT.md) | cmocka-2.0.2 | aarch64le | built | 88/89 | 1 (1 / 0) | 7.5 |  |
| [expat](ports-aarch64le/expat/REPORT.md) | R_2_10_0 | aarch64le | built | 1/1 | 0 (0 / 0) | 7.1 |  |
| [flac](ports-aarch64le/flac/REPORT.md) | 1.5.0 | aarch64le | built | 6/10 | 1 (1 / 0) | 22.9 |  |
| [flatcc](ports-aarch64le/flatcc/REPORT.md) | v0.6.4 | aarch64le | built | not run | 0 (0 / 0) | 0.2 | build only: its tests run the just-built flatcc compiler on the build host |
| [fmt](ports-aarch64le/fmt/REPORT.md) | 12.2.1 | aarch64le | built | 20/21 | 1 (1 / 0) | 21.8 |  |
| [googletest](ports-aarch64le/googletest/REPORT.md) | v1.18.0 | aarch64le | built | 25/27 | 1 (1 / 0) | 49.4 |  |
| [inih](ports-aarch64le/inih/REPORT.md) | r63 | aarch64le | built | 17/17 | 0 (0 / 0) | 1.0 |  |
| [jansson](ports-aarch64le/jansson/REPORT.md) | v2.15.1 | aarch64le | built | 211/215 | 1 (1 / 0) | 5.1 |  |
| [json-c](ports-aarch64le/json-c/REPORT.md) | json-c-0.19-20260627 | aarch64le | built | 28/28 | 1 (1 / 0) | 5.1 |  |
| [kissfft](ports-aarch64le/kissfft/REPORT.md) | 131.2.0 | aarch64le | built | none built | 0 (0 / 0) | 0.5 |  |
| [libcbor](ports-aarch64le/libcbor/REPORT.md) | v0.14.0 | aarch64le | built | 28/28 | 0 (0 / 0) | 2.7 |  |
| [libccd](ports-aarch64le/libccd/REPORT.md) | v2.1 | aarch64le | built | 3/3 | 0 (0 / 0) | 3.8 |  |
| [libcoap](ports-aarch64le/libcoap/REPORT.md) | v4.3.5b | aarch64le | built | none built | 1 (1 / 0) | 3.7 |  |
| [libconfig](ports-aarch64le/libconfig/REPORT.md) | v1.8.3 | aarch64le | built | 1/1 | 1 (1 / 0) | 3.1 |  |
| [libdeflate](ports-aarch64le/libdeflate/REPORT.md) | v1.26 | aarch64le | built | 8/8 | 0 (0 / 0) | 1.0 |  |
| [libevent](ports-aarch64le/libevent/REPORT.md) | release-2.1.13-stable | aarch64le | built | 20/24 | 2 (2 / 0) | 18.9 |  |
| [libgpiod](ports-aarch64le/libgpiod/REPORT.md) | v2.3.2 | aarch64le | needs-qnx-equivalent | not run | 0 (0 / 0) | 0.5 | Linux GPIO character-device API: expected not to port |
| [libjpeg-turbo](ports-aarch64le/libjpeg-turbo/REPORT.md) | 3.2.1 | aarch64le | built | 646/646 | 0 (0 / 0) | 71.2 |  |
| [libmodbus](ports-aarch64le/libmodbus/REPORT.md) | v3.2.0 | aarch64le | built | 0/1 | 0 (0 / 0) | 1.2 |  |
| [libogg](ports-aarch64le/libogg/REPORT.md) | v1.3.6 | aarch64le | built | 2/2 | 0 (0 / 0) | 0.7 |  |
| [libpng](ports-aarch64le/libpng/REPORT.md) | v1.6.59 | aarch64le | built | none built | 1 (1 / 0) | 2.5 |  |
| [libsamplerate](ports-aarch64le/libsamplerate/REPORT.md) | 0.2.2 | aarch64le | built | 12/13 | 0 (0 / 0) | 3.7 |  |
| [libsodium](ports-aarch64le/libsodium/REPORT.md) | 1.0.22-RELEASE | aarch64le | built | 101/101 | 0 (0 / 0) | 10.9 |  |
| [libsrtp](ports-aarch64le/libsrtp/REPORT.md) | v2.8.1 | aarch64le | built | 9/12 | 1 (1 / 0) | 10.8 |  |
| [libtommath](ports-aarch64le/libtommath/REPORT.md) | v1.3.0 | aarch64le | built | 1/1 | 0 (0 / 0) | 3.1 |  |
| [libuv](ports-aarch64le/libuv/REPORT.md) | v1.53.0 | aarch64le | built | 0/2 | 1 (1 / 0) | 12.7 |  |
| [libwebsockets](ports-aarch64le/libwebsockets/REPORT.md) | v5.1.0 | aarch64le | failed | not run | 1 (1 / 0) | 3.8 |  |
| [libxml2](ports-aarch64le/libxml2/REPORT.md) | v2.15.4 | aarch64le | built | 7/8 | 0 (0 / 0) | 10.4 |  |
| [libyaml](ports-aarch64le/libyaml/REPORT.md) | 0.2.5 | aarch64le | built | 2/2 | 0 (0 / 0) | 0.9 |  |
| [lz4](ports-aarch64le/lz4/REPORT.md) | v1.11.1 | aarch64le | built | none built | 0 (0 / 0) | 0.9 |  |
| [mbedtls](ports-aarch64le/mbedtls/REPORT.md) | v4.2.0 | aarch64le | built | 147/148 | 1 (1 / 0) | 47.7 |  |
| [miniz](ports-aarch64le/miniz/REPORT.md) | 3.1.2 | aarch64le | built | 1/1 | 0 (0 / 0) | 1.9 |  |
| [mosquitto](ports-aarch64le/mosquitto/REPORT.md) | v2.1.2 | aarch64le | built | none built | 3 (3 / 0) | 10.2 | 2.1 needs cJSON (our QNX port of it) and, on QNX, TLS: without it 2.1 has random bytes only from Linux getrandom(); OpenSSL from the SDP. Its tests need CUnit and a Python broker harness |
| [msgpack-c](ports-aarch64le/msgpack-c/REPORT.md) | c-7.0.2 | aarch64le | built | 5/5 | 0 (0 / 0) | 1.5 |  |
| [nanopb](ports-aarch64le/nanopb/REPORT.md) | 0.4.9.3 | aarch64le | built | not run | 0 (0 / 0) | 0.1 | build only: its tests use scons and protoc |
| [nng](ports-aarch64le/nng/REPORT.md) | v2.1.0 | aarch64le | built | 3/64 | 1 (1 / 0) | 74.0 |  |
| [open62541](ports-aarch64le/open62541/REPORT.md) | v1.5.10 | aarch64le | built | none built | 2 (2 / 0) | 15.6 |  |
| [opus](ports-aarch64le/opus/REPORT.md) | v1.6.1 | aarch64le | built | none built | 0 (0 / 0) | 2.9 |  |
| [paho.mqtt.c](ports-aarch64le/paho.mqtt.c/REPORT.md) | v1.3.16 | aarch64le | built | not run | 1 (1 / 0) | 0.6 | build only: the test suite needs an MQTT broker on the target |
| [pcre2](ports-aarch64le/pcre2/REPORT.md) | pcre2-10.49 | aarch64le | built | 1/3 | 0 (0 / 0) | 6.9 |  |
| [pugixml](ports-aarch64le/pugixml/REPORT.md) | v1.16 | aarch64le | built | 0/1 | 0 (0 / 0) | 1.9 |  |
| [spdlog](ports-aarch64le/spdlog/REPORT.md) | v1.17.0 | aarch64le | built | 1/1 | 1 (1 / 0) | 14.8 |  |
| [sqlite](ports-aarch64le/sqlite/REPORT.md) | version-3.54.1 | aarch64le | built | not run | 0 (0 / 0) | 11.7 | build only: its test suite needs Tcl on the target |
| [tinycbor](ports-aarch64le/tinycbor/REPORT.md) | v7.1 | aarch64le | built | 1/1 | 2 (2 / 0) | 0.6 |  |
| [tinyxml2](ports-aarch64le/tinyxml2/REPORT.md) | 11.0.0 | aarch64le | built | 1/1 | 1 (1 / 0) | 1.9 |  |
| [tomlplusplus](ports-aarch64le/tomlplusplus/REPORT.md) | v3.4.0 | aarch64le | built | none built | 0 (0 / 0) | 1.2 |  |
| [wolfssl](ports-aarch64le/wolfssl/REPORT.md) | v5.9.4-stable | aarch64le | built | 1/1 | 1 (1 / 0) | 7.1 |  |
| [xxHash](ports-aarch64le/xxHash/REPORT.md) | v0.8.4 | aarch64le | built | none built | 0 (0 / 0) | 0.5 |  |
| [yaml-cpp](ports-aarch64le/yaml-cpp/REPORT.md) | yaml-cpp-0.9.0 | aarch64le | built | 0/1 | 1 (1 / 0) | 37.3 |  |
| [yyjson](ports-aarch64le/yyjson/REPORT.md) | 0.13.0 | aarch64le | built | 12/12 | 0 (0 / 0) | 6.8 |  |
| [zlib](ports-aarch64le/zlib/REPORT.md) | v1.4 | aarch64le | built | 4/4 | 0 (0 / 0) | 1.0 |  |
| [zstd](ports-aarch64le/zstd/REPORT.md) | v1.5.7 | aarch64le | built | 1/4 | 0 (0 / 0) | 12.9 |  |
<!-- results:end -->

**What the failures are.** Each one was reproduced outside the campaign before being named. Details are in
[docs/LEARNINGS.md](docs/LEARNINGS.md), each test's QNX output is in `ports/<library>/logs/tests.log`, and the
reproducers are in [docs/qnx-reports/](docs/qnx-reports/):
- **QNX C library behaviour** (draft reports, not sent):
  - `strtod()` is not correctly rounded (pugixml, jansson, yaml-cpp).
  - `strftime()` writes nothing for `%Ex`/`%EX`/`%Ec` (fmt 11.0.2 at the 2024 tag; fmt 12.2.1's chrono tests pass).
  - `fchdir()` needs `O_DIRECTORY` (googletest's death tests). QNX documents this.
  - `qsort()` writes outside the array when the comparator is inconsistent (libsrtp's tests use a random
    comparator).
  - `poll()` reports no `POLLHUP` when a pipe's writer closes (nng 2.1's tests hang at exit; a drafted nng
    fix takes them from 3/64 to 60/64 on QNX).
  - A process's main thread gets about 464 KiB of stack unless it is linked with `qcc -N`; Linux gives 8 MiB.
    cJSON 1.7.19's deep-recursion test overflowed it. The agent read the backtrace from the core dump and
    relinked with `-N8M` (rule `main-stack`): 19/19 ([`scripts/stack_probe.c`](scripts/stack_probe.c) measures it).
  - `malloc()` commits memory at once: 1 GiB took 5 to 9 s on the target, where Linux returns at once. expat
    2.10's suite needs 241 s on QNX, so it runs with a 900 s limit (`test_timeout` in `campaign.yaml`).
- **Different but allowed output that a test compares with glibc's:** `printf("%a")` (fmt 12 expects
  `0x1.34ap+10`, QNX prints `0x9.a52p+7`, both valid C), and an exact tie printed with three decimals
  (benchmark expects `976.562` for 976.5625, QNX prints `976.563`).
- **Undefined C that glibc tolerates:** `printf("%s", NULL)`. The agent reads the core dump and fixes it in
  json-c, libconfig, tinyxml2 and capstone (all now pass). It finds the same thing but cannot place the fix
  in libxml2 (library code) and nng (behind a tail call).
- **What the test image lacks:** `killall` (libmodbus), `/bin/echo` (pcre2grep), internet access (nng 1.9),
  the `en_US.UTF-8` locale (benchmark),
  2 GiB of memory for one zstd test, a `locale` command (pcre2 skips those tests), Tcl (sqlite), an MQTT
  broker (paho), cmake on the target (libpng's tests are CMake scripts).
- **Needs a QNX equivalent** (2, on both architectures, not counted as built): can-utils and libgpiod stop on
  Linux kernel headers (`<linux/types.h>`, `<linux/const.h>`). The porting advisor
  ([`qnx_porter/advisor.py`](qnx_porter/advisor.py)) then scans the source and names each Linux-only interface
  with QNX's equivalent and its QNX docs page: can-utils uses SocketCAN in 41 files (QNX: a `dev-can-*` driver
  with `CAN_DEVCTL_*` devctl commands), netlink in 4 and epoll in 5; libgpiod uses the GPIO character device in
  38 files (QNX: the board's GPIO resource manager, or the GPIO framework of SDP 8.0.5). See
  [`ports/can-utils/REPORT.md`](ports/can-utils/REPORT.md) and [`ports/libgpiod/REPORT.md`](ports/libgpiod/REPORT.md);
  log [`results/runs/advisor-1.log`](results/runs/advisor-1.log). libgpiod 2.3.2 needs meson 0.64 or newer, so
  that run used meson 1.6.1; with the host's meson 0.61.2 it stopped before compiling anything.
- **Did not build** (1): libwebsockets 5.1.0 defines its own `struct ifaddrs`, which clashes with QNX's `<ifaddrs.h>`. libuv 1.53.0
  builds with rules only, because upstream added QNX 8.0 support
  ([PR #4801](https://github.com/libuv/libuv/pull/4801)); 401 of its subtests pass on QNX and 31 fail, which we
  have not looked into. At the 2024 tags libuv (`struct qtime_entry` has no `nsec` in QNX 8.0) and
  libwebsockets (`TCPCTL_KEEPCNT`) did not build with rules; with the language-model step on, both built:
  [docs/MODEL_STEP.md](docs/MODEL_STEP.md).

**How we got here** (each line is the summary the campaign script printed; logs in [`results/runs/`](results/runs/)):

| Run | Built | Tests passed on QNX | What we changed before the next run |
|---|---|---|---|
| 1 | 4/10 | 68/72 | CMake ignored flag fixes after round 1; autotools configured in the wrong folder; new rules for libm, `__inet_pton`, `<sys/errno.h>`, `bool` |
| 2 | 9/10 | 292/381 | automake test programs were never copied to QNX; `.sh` tests ran on Linux |
| 3 | 9/10 | 372/381 | a proved fix was reverted when it let the link step run; endian names from `<net/netbyte.h>` |
| 4 | 10/10 | 372/381 | CMake pass regexes need DOTALL (cmocka re-run: 46/46) |
| 5 (json-c, libconfig only) | 2/2 | 26/26 | crash triage from QNX core dumps + `printf-null` rule (both crashes were `printf("%s", NULL)`) |
| 6 (61 libraries) | 50/61 | 1185/1345 | `cmake -E` test helpers run as QNX shell commands; rules `wcswidth-compat`, `qcc-sysroot`; a resolv.conf on the target |
| 7 (61 libraries) | 57/61 | 1332/1366 | final run at the 2024 tags (now in `ports-2024/`); re-runs into the same log: 6 libraries after a DNS outage, sqlite without editline, CRLF-safe and MSVC-safe `printf-null` patches, libccd once CMake could find the stub `librt` |
| 8 (61 libraries, newest tags, x86_64) | 58/61 | 1563/1658 | first pass 55/61 and 1430/1529; re-runs into the same log after: test suites turned on for 9 libraries (`uses:` for googletest, cmocka, cJSON), rules `main-stack` and `<sys/queue.h>`, `enable_testing()` for libogg 1.3.6, cmake/ctest test steps counted as not runnable, expat's `/dev/urandom` and 900 s limit. nng 2.1.0 stays at 3/64: [docs/qnx-reports/pipe-pollhup.md](docs/qnx-reports/pipe-pollhup.md) |

Runs 6 and 7 count tests the way the campaign script did on the day. Run 6 counted libraries whose suite
registered no tests as "tests ran". Since run 7, the summary and the headline count only libraries with at
least one test.


## Rust crates on QNX 8.0
`qnx-porter crate <name> --version <v>` ports a crate from crates.io and runs its own tests on a QNX 8.0 target.
Many widely used crates support QNX 7 but not QNX 8.0, often through a dependency (getrandom, errno, rustix,
signal-hook-registry). Two rules fix that without editing the crate's own code:
- `libc-update` updates a too-old pinned `libc`;
- `nto-to-qnx` lets QNX 8.0 take the dependency's QNX 7 path through cargo's `[patch]`.

The crates' own test suites then run on the target. Written by `scripts/crates_md.py` from `results/crates*.csv`:
<!-- crates:start -->
- x86_64 (QEMU, KVM): 21 of 22 crates built; 2751 of 2764 of their own tests passed (18 crates with tests that ran)
- aarch64 on QEMU `virt` (emulated): 21 of 22 crates built; 2721 of 2733 of their own tests passed (18 crates with tests that ran)
<!-- crates:end -->
Per crate, with every fix and every failing test explained: [docs/rust/CRATES.md](docs/rust/CRATES.md).

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
chat-completions endpoint, set with `QNX_PORTER_BASE_URL`). It must answer with a unified diff and
a one-sentence reason. The diff must pass `git apply --check`; after the rebuild, if the error it targeted
is still there or the error count grew, the agent reverts it and marks it `reverted` in the report. What it
did on the libraries the rules could not build, and how its fixes compare with upstream's own QNX changes:
[docs/MODEL_STEP.md](docs/MODEL_STEP.md).

## Evidence of QNX use
The path from "a git URL" to "tests passed on QNX 8.0", function by function:

| Step | What touches QNX | Exact place |
|---|---|---|
| 1. Find the SDP | sources `~/qnx800/qnxsdp-env.sh` to get `QNX_HOST` and `QNX_TARGET` | [`qnx.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/qnx.py) `sdp_env()` |
| 2. Check it | runs `qcc -V` and looks for `gcc_ntox86_64`; checks the `x86_64-pc-nto-qnx8.0.0-gcc` drivers | `qnx.py` `doctor()` (CLI: `qnx-porter doctor`) |
| 3. Write the QNX toolchain | CMake: `CMAKE_SYSTEM_NAME QNX`, `CMAKE_C_COMPILER $QNX_HOST/usr/bin/qcc`, `CMAKE_C_COMPILER_TARGET gcc_ntox86_64`, `CMAKE_SYSROOT $QNX_TARGET`. Meson: a cross file with `system = 'qnx'`. Autotools: `--host=x86_64-pc-nto-qnx8.0.0` | `qnx.py` `cmake_toolchain()`, `meson_cross()`, `gnu_env()`, `ARCHES`; saved per port as `ports/<library>/qnx-toolchain.cmake` |
| 4. aarch64 | the same toolchain with `qcc -Vgcc_ntoaarch64le` and the `aarch64-unknown-nto-qnx8.0.0` triplet | `qnx.py` `ARCHES["aarch64le"]`; saved per port as [`ports-aarch64le/<library>/qnx-toolchain.cmake`](ports-aarch64le/zlib/qnx-toolchain.cmake); the target's `uname -a` (`QEMU_virt aarch64le`) is in each `report.json` |
| 5. Invoke qcc | the configure and build commands that drive qcc through that toolchain; output goes to `ports/<library>/logs/round-NN.log` | [`build.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/build.py) `Job.steps()` builds the commands, `run()` executes them; called from [`agent.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/agent.py) `port()` |
| 6. Fix what QNX rejects | 35 Linux-isms and the QNX 8.0 answer to each (libsocket, libfsnotify, libc-provided pthread/rt/dl, `MAP_ANON`, `pthread_setname_np`, `<process.h>`, `_QNX_SOURCE`, ...), sourced from QNX's 8.0 documentation | [`fixes.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/fixes.py) `_rule()`, [`linuxisms.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/linuxisms.py); sources per fact in [docs/LINUX_ISMS.md](docs/LINUX_ISMS.md) |
| 7. Start the QNX target | QEMU image made by QNX's `mkqnximage --type=qemu --arch=x86_64` (or `aarch64le`) from the SDP | [SETUP.md](SETUP.md) step 4; [`scripts/qemu_target.sh`](scripts/qemu_target.sh) |
| 8. Run tests on QNX | copies the build to the target (`tar` over ssh), then ctest / meson test / make check run every test binary on QNX through a generated wrapper (`CMAKE_CROSSCOMPILING_EMULATOR`, meson `exe_wrapper`, automake `LOG_COMPILER`) | [`target.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/target.py) `Target.sync()`, `write_wrapper()`, `remote_command()`, `main()`; output `ports/<library>/logs/tests.log`, and the same results as JUnit XML in [`tests.junit.xml`](ports/mbedtls/logs/tests.junit.xml) (`junit_from_log()`) for CI dashboards |
| 9. QNX path-space links | the build tree appears on the target at its host path through QNX's `ln -sP`, so generated test scripts with absolute paths run unchanged | [`target.py`](qnx_porter/target.py) `link_command()`, called from `Target.sync()` |
| 10. Run as another user | suites that refuse root (libuv) run through QNX's `on -u <user>` (`run_as` in [`campaign.yaml`](campaign.yaml)); QNX's `timeout -s KILL` caps each test | `target.py` `remote_command()`; output [`ports-model/libuv/logs/tests.log`](ports-model/libuv/logs/tests.log) |
| 11. Crash triage | copies core dumps from the target (written by QNX's `dumper` in the `mkqnximage` image) and reads them with the SDP's own gdb (`x86_64-nto-qnx8.0.0-gdb`, `aarch64-nto-qnx8.0.0-gdb`) against the QNX target libraries | [`crash.py`](qnx_porter/crash.py) `collect()`, `backtrace()`, `printf_null()`; output [`ports/json-c/logs/crashes.log`](ports/json-c/logs/crashes.log) |
| 12. Record the target | `uname -a` from the QNX target in every report | `target.py` `Target.uname()`; `ports/<library>/report.json` field `target` |
| 13. One command for all of it | stops early if `qcc` or the target is missing | [`scripts/run_campaign.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/scripts/run_campaign.py) `preflight()`, `check_target()` |
| 14. Real-time harness | a C harness built with `qcc`, run on the target: `SCHED_FIFO` priority 60 (`pthread_setschedparam`), CPU isolation with `ThreadCtl(_NTO_TCTL_RUNMASK)`, timing with `ClockCycles()` and `SYSPAGE_ENTRY(qtime)->cycles_per_sec` | [`rt_bench.py`](qnx_porter/rt_bench.py) `BENCH_C`, `compile_bench()`, `run_bench()`; output `results/rt/x86_64/<library>.json`, summarised in [docs/RT_RESULTS.md](docs/RT_RESULTS.md) |
| 15. Rust crates | cargo builds `std` with `-Zbuild-std` for `x86_64-pc-qnx` / `aarch64-unknown-qnx` and uses the SDP's `qcc` / `q++` for C code | [`crate.py`](qnx_porter/crate.py) `cargo_env()`, `build_tests()`, `run_tests()`; output `ports-rust*/<crate>/logs/tests.log` |

Real output from our runs (11 Nov 2026):
```
$ qnx-porter doctor                      # on the build host, WSL Ubuntu 22.04
ok  qcc          /home/chirag/qnx800/host/linux/x86_64/usr/bin/qcc
ok  qcc targets  cc: targets available in /home/chirag/qnx800/host/linux/x86_64/etc/qcc: ...
ok  SDP complete no empty compiler or libc files
ok  qcc builds hello ok
$ ssh root@172.31.1.11 uname -a          # the QEMU target
QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
$ tail -1 ports/mbedtls/logs/tests.log   # written by ctest_on_target(); mbedtls v4.2.0
148/148 tests passed on the QNX target
```
The one patch mbedtls needed, as the agent wrote it ([`ports/mbedtls/patches/0001-link-libsocket.patch`](ports/mbedtls/patches/0001-link-libsocket.patch)):
```
Subject: [qnx-porter 0001] link-libsocket
Source: deterministic rule
Reason: `__inet_pton` is in QNX's libsocket, not in libc as on Linux: link with -lsocket.
Error: x509_crt.c:2846:(.text+0x7d1): undefined reference to `__inet_pton'
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
Install: `python3 -m pip install --user qnx-porter` (from PyPI), or from a clone as below.
```bash
python3 -m pip install --user --upgrade pip   # Ubuntu 22.04's pip 22 cannot do editable installs
python3 -m pip install --user -e ".[test]"
python3 -m pytest -q                                   # no QNX needed
source ~/qnx800/qnxsdp-env.sh && qnx-porter doctor
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11
python3 scripts/run_campaign.py                       # every library in campaign.yaml, then the CSV
```
Build and run requirements: **QNX SDP 8.0**, target **x86_64 QEMU** or **aarch64le QEMU `virt`**
(both built by `scripts/qemu_target.sh` with QNX's `mkqnximage`; any QNX 8.0 target reachable over ssh also
works, but we tested only these two), toolchain **qcc / GCC from SDP 8.0**, host **Ubuntu 22.04/24.04 or WSL2**. Details: [SETUP.md](SETUP.md).

## Known limits
The full list, with numbers: [docs/LIMITATIONS.md](docs/LIMITATIONS.md). In short:
- Linux host only (WSL2 on Windows), because QNX's QEMU tooling is Ubuntu-only.
- Tests that need a network peer or root-only devices are counted as they run; nothing is excluded by hand.
- A rule never rewrites Linux-only code (epoll, inotify, ...). That is the model's job, or a person's.
- The model is never trusted: a diff that does not clear its error is reverted and shown as reverted.

## Licence
Apache-2.0. Patches produced for a library are offered under that library's own licence.
