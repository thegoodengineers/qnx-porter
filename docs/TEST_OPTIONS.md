# Turning on upstream test suites

Twenty libraries built for QNX at their old pins but registered no tests, or were not run. This table records,
at the tags `campaign.yaml` now pins, which option builds and registers each library's own tests, and what
happened when we tried it.

How each row was checked: `scripts/run_campaign.py --target none --no-model` with QNX SDP 8.0 (qcc,
x86_64-pc-nto-qnx8.0.0) on the WSL Ubuntu 22.04 build host (CMake 3.22.1), then `ctest --show-only=json-v1`
(or `meson introspect --tests`) in the build folder. "Tests listed" is that count. Cross-compiled only: none of
these tests has been run on a QNX target yet. `file` reported every listed test binary as a QNX executable
(interpreter `/usr/lib/ldqnx-64.so.2`).

## Test frameworks from earlier ports (`uses`)

The SDP ships no GoogleTest or cmocka, and mosquitto 2.1 needs cJSON. qnx-porter ports all three, so a library
can name them in `campaign.yaml` under `uses:`. Before it builds, each named port is installed from its own QNX
build tree into the library's `work/deps` (`cmake --install` with `DESTDIR`). The toolchain file adds that folder
as a find root, so CMake finds the headers, libraries and package configs. The folder goes to the target with
the tests. A library may only use one listed before it, and the campaign stops otherwise.

Checked by cross-building cmocka, googletest and cJSON, then libcbor, msgpack-c, c-ares and mosquitto against
them, with `--target none`. The counts below are `ctest -N` in each build folder.

## Tests that should run on the target

| Library | Tag | Option added | Tests listed | Target-side needs |
|---|---|---|---|---|
| benchmark | v1.10.0 | `-DBENCHMARK_ENABLE_TESTING=ON -DBENCHMARK_DOWNLOAD_DEPENDENCIES=ON` (was `TESTING=OFF`) | 87 | none. The build host downloads googletest v1.15.2 at configure time |
| libdeflate | v1.26 | `-DLIBDEFLATE_BUILD_TESTS=ON` | 8 | none. Links the SDP's zlib |
| spdlog | v1.17.0 | `-DSPDLOG_BUILD_TESTS=ON` | 1 (`spdlog-utests`, one Catch2 binary) | writable working folder and `rm`: the tests write log files under `test_logs/` and clear it with `system("rm -rf test_logs")`. The build host downloads Catch2 v3.5.0 at configure time |
| miniz | 3.1.2 | none: `BUILD_TESTS` defaults to ON at this tag | 1 (`catch_tests`) | none |
| tinycbor | v7.1 | none: v7.1 switched to CMake, and qnx-porter already passes `BUILD_TESTING=ON` | 1 (`tst_c90`) | none. Its Qt tests are skipped because the SDP has no Qt6 |
| libcbor | v0.14.0 | `-DWITH_TESTS=ON`, `uses: [cmocka]` | 28 | none |
| msgpack-c | c-7.0.2 | `-DMSGPACK_BUILD_TESTS=ON` (was OFF), `uses: [googletest]` | 5 | none |
| c-ares | v1.34.9 | `-DCARES_BUILD_TESTS=ON`, `uses: [googletest]` | 3 (`arestest`, one GoogleTest binary with its own subtests, and two fuzz-corpus replays) | not checked yet: `arestest` includes live-lookup tests, and the target image has no internet access |
| inih (meson) | r63 | none: meson option `tests` defaults to true | 17 | `/bin/sh` and `diff`: each test is `tests/runtest.sh`, which pipes the test program into `diff`. The SDP's target tree has no `diff` binary, so these may fail on the target if the image lacks one |

## Left out

| Library | Tag | Option | Why |
|---|---|---|---|
| open62541 | v1.5.10 | `-DUA_BUILD_UNIT_TESTS=ON` | configure fails: `Could NOT find CHECK` (the Check unit-test framework) |
| kissfft | 131.2.0 | `-DKISSFFT_TEST=ON` | configure fails: `pkg_check_modules(fftw3 REQUIRED)` finds no FFTW for QNX. The test suite also runs `testkiss.py`, which needs Python on the target |
| Micro-CDR | v2.0.2 | `-DUCDR_BUILD_TESTS=ON` | build fails: its superbuild fetches googletest release-1.11.0 and Fast-CDR v1.0.13 with `ExternalProject_Add` without the QNX toolchain, so the host-built `libgtest.a` does not link with QNX's `ld` (`undefined reference to symbol '_ZNSolsEPFRSoS_E@@GLIBCXX_3.4'`) |
| mosquitto | v2.1.2 | `-DWITH_TESTS=OFF` | the library builds again with `uses: [cJSON]` and TLS from the SDP's OpenSSL (without TLS, 2.1 takes random bytes only from Linux `getrandom()`, which QNX 8.0 lacks). Its tests need CUnit, which no port provides, and most are Python scripts that start a broker |
| libpng | v1.6.59 | `PNG_TESTS` (already ON) | 37 tests listed, all run through `cmake -P`, so they need CMake on the target |
| opus | v1.6.1 | `-DOPUS_BUILD_TESTING=ON` (already set) | 5 tests listed, all run through `cmake -P cmake/RunTest.cmake`, so they need CMake on the target |
| BLAKE3 | 1.8.7 | `BLAKE3_TESTING`, `BLAKE3_TESTING_CI` | the only test runs `ctest --build-and-test` and then `test.py`, so it needs CMake and Python on the target, and it builds with `-fsanitize=address,undefined` |
| libcoap | v4.3.5b | `-DENABLE_TESTS=ON` | builds a `testdriver` program but registers no CTest test, and links `-lcunit`, which the SDP does not ship |
| lz4 | v1.11.1 | none | `build/cmake` has no tests; upstream's tests are driven by `tests/Makefile` |
| xxHash | v0.8.4 | none | `build/cmake` has no tests; upstream's tests are driven by the top-level Makefile |
| tomlplusplus | v3.4.0 | meson `build_tests` | tests exist only in the meson build. qnx-porter picks CMake when a project ships both, and the CMake build has no tests |
