# QNX hand-made port recipes: survey of 21 libraries

Source: GitHub `qnx-ports/build-files`, branch `main`, commit `1964dba24df0b5360bf98b817717f1c5b04224e5` (2026-11-02).
Read via `gh api` on 2026-11-12. Each port was read from `ports/<name>/` plus its CI workflow `.github/workflows/<name>.yml`
(libjpeg-turbo's workflow file is `libturbo-jpeg.yml`).

Where a port builds a `qnx-ports/<name>` **fork** instead of upstream, the QNX source changes live in that fork, not in
build-files. For those I also ran `gh api repos/<upstream>/compare/<tag>...qnx-ports:<repo>:<branch>` and summarise
the fork's QNX commits under "Fork source changes". Those lines come from the fork repos (GitHub API), **not from
build-files**. Fork default branch names likewise come from the GitHub API.

---

## 1. Conventions (from top-level README.md, docker/README.md, resources/, and the port directories)

**What the top-level README says**
- Each port has its own sub-directory under `ports/`, and its build instructions are in that sub-directory's `README.md`.
- Some projects build without modification, so they have no fork under github.com/qnx-ports.
- Two ways to build: the prepared Docker image (`docker/`, recommended) or directly on the host.
- Build and test results are posted to the "QNX Open-Source Dashboard" (oss.qnx.com).
- The README has a "Port Status" table with a CI badge per port. No version column for `ports/` (only the Conan table has versions).
- No CONTRIBUTING file and no port template doc. `.github/PULL_REQUEST_TEMPLATE.md` does not exist (404).

**Host / SDP / arch**
- Almost every port README says QNX ports are only supported from a Linux host.
- Docker: Ubuntu container, SDP mounted from the host. `--sdp-version` defaults to `qnx800` (docker/README.md).
- SDPs: QNX SDP 8.0 (`~/qnx800`) everywhere; many ports also build in CI against 7.1 (`~/qnx/710`). CI runner: `ubuntu-22.04-common`.
- Architectures: every port has `nto-aarch64-le/` and `nto-x86_64-o/`. Only googletest also has `nto-arm-le-v7/` (skipped on 8.0).
- Reference test target: Raspberry Pi 4 running QNX 8.0 (the "QNX Everywhere"/QSTI quick-start image), user `qnxuser`, home `/data/home/qnxuser`.

**Directory layout.** There are two styles.

*Style A: CMake wrapper (most ports)*
```
ports/<name>/
  Makefile                  # LIST=OS [CPU [VARIANT]]; include recurse.mk  (QNX recursive make)
  common.mk                 # include qconfig.mk/qmacros.mk/qtargets.mk; overrides the 'all' target;
                            #   runs cmake with CMAKE_ARGS, then make, then make install
  qnx.nto.toolchain.cmake   # CMAKE_SYSTEM_NAME=QNX, CC=qcc, CXX=q++, -Vgcc_nto<arch>, ar/ranlib = nto<cpu>-ar
  nto-aarch64-le/Makefile   # "include ../common.mk" (sometimes + CMAKE_SYSTEM_PROCESSOR)
  nto-x86_64-o/Makefile
  README.md
  [project_hooks.cmake]     # passed as -DCMAKE_PROJECT_INCLUDE (jansson, pugixml: link libmuslflt)
  [test scripts / test.toml / test.result]
```
*Style B: autotools or plain make through QNX `qmake-cfg.mk` "build-hooks" (c-ares, libxml2, zstd)*
```
ports/<name>/
  Makefile                  # LIST=OS CPU VARIANT; MAKEFILE=GNUmakefile; include recurse.mk
  build-hooks               # shell functions hook_preconfigure / hook_configure / hook_make / hook_postmake
  nto-*/GNUmakefile         # include qconfig.mk + $(MKFILES_ROOT)/qmake-cfg.mk
  [common.mk], [*.patch], README.md
```
sqlite is a hybrid: Style-A `common.mk` that calls upstream autotools `./configure` directly.

**Common flags in the template.** `CFLAGS += $(FLAGS)` (FLAGS comes from the QNX make system), often `-D_QNX_SOURCE`,
`LDFLAGS += -Wl,--build-id=md5`, `CMAKE_BUILD_TYPE ?= Release`, `PREFIX ?= /usr/local`. Install goes to
`$(INSTALL_ROOT_nto)` (= `$QNX_TARGET` by default). Libraries land in `<INSTALL_ROOT>/<cpuvardir>/usr/local/lib`, headers in
`<INSTALL_ROOT>/usr/local/include`. Staging is done with `INSTALL_ROOT_nto=<dir> USE_INSTALL_ROOT=true`.
`resources/qconf_override/qconf_override.mk` sets `INSTALL_ROOT_nto := /tmp/stages/target/qnx`.
`resources/` also ships meson cross files (`meson/<arch>/qnx{700,710,800}.ini`) and `.pc` files that the SDP omits.

**How upstream source is fetched.** The build never fetches source itself. The README tells the user to `git clone`,
and `QNX_PROJECT_ROOT=<path>` points the build at the clone. There are two patterns:
1. Clone the **qnx-ports fork** (default branch = a QNX branch such as `qnx_v1.13.0`). Used by: benchmark, c-ares,
   cJSON, googletest, jansson, libevent, libuv, libwebsockets, libxml2, libyaml, mosquitto, tinyxml2.
2. Clone **upstream** at a pinned tag/commit. Used by: libexpat `R_2_6_4`, libjpeg-turbo `3.1.0`, libpng `v1.6.46`,
   lz4 (no tag), pcre2 `pcre2-10.45`, pugixml (no tag), sqlite `version-3.50.0`, zlib `v1.3.1`, zstd `v1.5.6`
   (the README; CI pins commit `794ea1b0`).

**Patches.** Only libxml2 has a patch file in build-files (`libxml2.patch`, applied manually with `git apply`).
Other source edits are either carried in the fork, or are `sed` lines in the README/CI (libxml2: `configure.ac`
automake version). No other port has a patch.

**Running tests on target.** Same pattern in every README:
1. `scp` the libs to `~/lib` and the test binaries to `~/bin` (or a test dir) on the target.
2. `ssh qnxuser@<target>`.
3. `export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/data/home/qnxuser/lib`.
4. Run the test binaries one by one, or the port's helper script.

Test binaries are usually installed by the fork's CMake into `usr/local/bin/<name>_tests`. Only googletest's CI
runs tests automatically (`qnx-ports/test-tools` + `test/test.toml`, JUnit report). All other CI workflows only build.

---

## 2. Per-library details

### benchmark
- **Files:** `.gitignore`, `LICENSE.md`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** fork `qnx-ports/benchmark` (default branch `qnx_v1.8.3`; tag not stated in build-files). Needs googletest built first ("tested version 1.13.0 with QNX changes", README).
- **SDP / arch:** README uses `~/qnx800`. CI builds 8.0 only. aarch64le, x86_64.
- **Build system:** CMake.
  - Flags: `CFLAGS += -D_QNX_SOURCE`, `LDFLAGS += -Wl,--build-id=md5`.
  - CMake options: `-DBUILD_SHARED_LIBS=ON -DBENCHMARK_ENABLE_WERROR=OFF -DBENCHMARK_DOWNLOAD_DEPENDENCIES=OFF -DBENCHMARK_USE_BUNDLED_GTEST=OFF`.
  - Toolchain adds `-std=gnu++11` to CXX flags.
- **Patches in build-files:** none.
- **Fork source changes (3 commits over upstream; from the fork):**
  - `src/CMakeLists.txt`: skips `HAVE_PTHREAD_AFFINITY` and the `Threads::Threads` link on QNX.
  - `src/sysinfo.cc`: replaces C casts with `static_cast` in the QNX `SYSPAGE_ENTRY(cpuinfo)->speed` path.
  - `CMakeLists.txt` and `test/CMakeLists.txt`: QNX install/config changes.
  - `test/reporter_output_test.cc`: edited.
  - Adds a `qnx/` directory (an older copy of the build files).
- **Tests:** README lists about 40 test binaries and the flags to run each with (e.g. `--benchmark_min_time=0.01s`). No results stated.

### c-ares
- **Files:** `.gitignore`, `Makefile`, `README.md`, `build-hooks`, `nto-aarch64-le/GNUmakefile`, `nto-x86_64-o/GNUmakefile`
- **Upstream:** fork `qnx-ports/c-ares` (branch `qnx_v1.34`, 4 commits over upstream tag `v1.34.3`). README says QNX c-ares is now available for direct download from qnx.haxx.se.
- **SDP / arch:**
  - README: "Tested for QNX 7.1 and 8.0 SDPs".
  - Tested configurations: 8.0 aarch64le on RPi4, 8.0 x86_64 on QEMU, 7.1 x86_64 on VirtualBox.
  - CI builds 8.0 only.
- **Build system:** autotools via `qmake-cfg.mk` and `build-hooks`. CI runs `./buildconf` first, and the host needs `autoconf`.
  - configure: `--disable-symbol-hiding --enable-tests-build-override --enable-qcc-compat`, `CPPFLAGS+=-D_QNX_SOURCE`, `LIBS="-lregex"`.
  - Moves `-D_FORTIFY_SOURCE=2` from CFLAGS to CPPFLAGS and adds `-O2`.
  - `hook_make` installs only the lib and headers, stamps usage info (`usemsg`), and copies `arestest` to `<target>/tests/cares/`.
- **Patches in build-files:** none.
- **Fork source changes (from the fork):**
  - `configure.ac`: adds the `--enable-qcc-compat` option and `AC_PROG_CXX`. The comment says qcc doesn't support c90 and the QNX C++ stdlib needs a newer standard.
  - `src/lib/ares_init.c` (+344): adds `init_by_qnx_conf()`, which reads the resolver config through QNX `getconf()` (`#ifdef __QNX__`).
  - Small QNX hooks in `ares_destroy.c`, `ares_gethostbyaddr.c`, `ares_gethostbyname.c`, `ares_options.c`, `ares_private.h`, `ares_sysconfig*.c`.
  - Rewrites the m4 `ax_*` macros.
- **Tests:** README explains how to run `./arestest` on target, with gtest/gmock libs copied over. No results stated.

### cJSON
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** fork `qnx-ports/cJSON` (branch `qnx-v1.7.18`; tag not stated in build-files).
- **SDP / arch:** README uses `~/qnx800`. CI builds 8.0 only. aarch64le, x86_64.
- **Build system:** CMake.
  - Flags: `LDFLAGS += -Wl,--build-id=md5`. No `-D_QNX_SOURCE`.
  - Passes `-DGCC_VER`, which the toolchain turns into `-V<ver>,gcc_nto<arch>`.
  - Toolchain sets `CMAKE_SKIP_RPATH TRUE` and `CMAKE_FIND_ROOT_PATH_MODE_*` (INCLUDE/LIBRARY ONLY, PROGRAM NEVER).
- **Patches in build-files:** none.
- **Fork source changes (QNX commits, from the fork):**
  - "add support for QNX 7.1/8.0": installs the tests to `bin/cJSON_tests` when `QNX`.
  - "Install libunity.so in /lib": removes `-std=c89` from the compiler flags on QNX and installs `libunity.so`.
  - The fork branch also carries 18 non-QNX upstream commits (cJSON.c +199/-133).
- **Tests:** README lists 19 test binaries to run on target.
  - Known failure: the `file_test7_should_be_parsed_and_printed` test of `parse_examples` "currently fails" (`ports/cJSON/README.md`).
  - README's explanation: double `==` comparison in print makes cJSON print with higher precision than parsed.

### googletest
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-arm-le-v7/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`, `test/run_tests.sh`, `test/test.toml`
- **Upstream:** fork `qnx-ports/googletest` (branch `qnx_v1.13.0`). benchmark's README says "tested version 1.13.0".
- **SDP / arch:**
  - CI matrix: 7.1 and 8.0 (tests are built and run only on 8.0).
  - Arches: aarch64le, x86_64, armv7le. armv7 is skipped on 8.0 via `Makefile.dnm` or a guard in `nto-arm-le-v7/Makefile`.
- **Build system:** CMake.
  - CMake options: `-DBUILD_SHARED_LIBS=ON -Dgtest_build_tests/-Dgtest_build_samples/-Dgmock_build_tests=$(BUILD_TESTING)` (default OFF).
  - Toolchain: `CMAKE_CXX_STANDARD 17` and `-Wno-error=deprecated-declarations`.
- **Patches in build-files:** none.
- **Fork source changes (1 commit "Port for QNX", from the fork):**
  - CMake: drops the `INSTALL_INTERFACE` include dirs on QNX.
  - CMake: links `regex` for `shared_gmock_test_`.
  - CMake: installs the test binaries to `bin/googletest_tests`.
  - `gmock-actions.h`: extra `negation<is_same<tuple<OnceAction&&>,…>>` constraint for `__QNX__ < 800`.
  - `gtest-death-test.cc`: `open(".", O_RDONLY|O_DIRECTORY)` for the cwd fd on `__QNX__ >= 800`.
- **Tests:**
  - README: run e.g. `./gmock-actions_test` from `googletest_tests`.
  - `test/test.toml` marks 9 tests as not runnable ("These tests fail --gtest_list_tests"): gtest_no_test_unittest, gtest_stress_test, gmock_stress_test, gmock_output_test_, gtest_environment_test, gtest_repeat_test, gmock-more-actions_no_exception_test, gmock_no_rtti_test, shared_gmock_test_.
  - `test/test.toml` lists `gmock_leak_test_` (3 LeakTest cases) as "Expected failures".
  - CI runs these tests on 8.0 and publishes a JUnit report. No pass counts are written in the repo.

### jansson
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `project_hooks.cmake`, `qnx.nto.toolchain.cmake` (4 lines: QNX, qcc, q++), `qnxtests.sh`
- **Upstream:** fork `qnx-ports/jansson` (branch `qnx-v2.14`). `common.mk` sets `JANSSON_VERSION = 2.14`.
- **SDP / arch:** README uses `~/qnx800`. CI builds 8.0 only. Tests run on RPi4.
- **Build system:** CMake.
  - Linker flags: `LDFLAGS += -Wl,--build-id=md5 -Wl,--allow-shlib-undefined`.
  - CMake options: `-DJANSSON_BUILD_DOCS=OFF -DJANSSON_BUILD_SHARED_LIBS=ON -DJANSSON_INSTALL_TESTS=ON`, `-DCMAKE_PROJECT_INCLUDE=project_hooks.cmake`.
  - `project_hooks.cmake` links `libmuslflt.a` with `--whole-archive`. The point is correct float-to-string conversion. muslflt is a QNX-ports helper library that must be built first.
- **Patches in build-files:** none.
- **Fork source changes:** 1 commit, "Add JANSSON_INSTALL_TESTS CMake Option" (CMakeLists.txt +16).
- **Tests:**
  - `qnxtests.sh` runs 17 unit test binaries plus `json_process` over the valid/invalid/encoding-flags suites, then prints pass/fail totals.
  - `project_hooks.cmake` warns that without muslflt "tests involving floating point conversion will not pass".
  - No results stated.

### libevent
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** fork `qnx-ports/libevent` (branch `qnx-2.1.12-stable`, 1 commit over upstream `release-2.1.12-stable`).
- **SDP / arch:** CI matrix 7.1 and 8.0. README uses `~/qnx800`. aarch64le, x86_64.
- **Build system:** CMake.
  - Flags: `LDFLAGS += -lsocket`, `-DEVENT__DISABLE_OPENSSL=ON`, `CMAKE_BUILD_TYPE ?= Debug`.
  - Toolchain sets `CMAKE_SYSROOT=$QNX_TARGET`.
- **Patches in build-files:** none.
- **Fork source changes (1 commit "qnx port", from the fork):**
  - `cmake/Macros.cmake`: `set(CMAKE_REQUIRED_LIBRARIES socket)` when QNX, so the configure checks find the socket functions.
  - `signal.c`: does not set `SA_RESTART` on QNX (`#ifndef __QNX__`).
- **Tests:** not stated (the README has no test section).

### libexpat
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** upstream `libexpat/libexpat`, tag `R_2_6_4`. The build runs `expat/buildconf.sh` and points `QNX_PROJECT_ROOT` at `libexpat/expat`.
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI matrix 7.1 and 8.0.
- **Build system:** CMake (template B: `CMAKE_SYSTEM_PROCESSOR_ENDIAN`, `-V gcc_nto<cpuvardir>`).
  - Flags: `CFLAGS += -D_QNX_SOURCE -fPIC -O3`.
  - No library-specific `-D` options.
  - README warns that QSC may already ship another libexpat, so runtime linking can conflict.
- **Patches:** none.
- **Tests:** "Tests are not avaliable." (`ports/libexpat/README.md`)

### libjpeg-turbo
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** upstream `libjpeg-turbo/libjpeg-turbo`, tag `3.1.0`.
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI matrix 7.1 and 8.0 (workflow file `libturbo-jpeg.yml`; the README badge points at `libjpeg-turbo.yml`).
- **Build system:** CMake. Flags: `CFLAGS += -D_QNX_SOURCE`. No library-specific options (SIMD left at default).
- **Patches:** none.
- **Tests:** "Tests are avaliable; currently all tests are passed." (`ports/libjpeg-turbo/README.md`). Run `tjunittest` on target.

### libpng
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `install_all.sh`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** upstream `pnggroup/libpng`, tag `v1.6.46`. Its dependency zlib is cloned by `install_all.sh` (`git clone -b v1.3.1 madler/zlib`) and built first.
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI matrix 7.1 and 8.0.
- **Build system:** CMake.
  - Flags: `CFLAGS += -D_QNX_SOURCE -O3 -fPIC`.
  - Toolchain sets `AWK=awk`.
  - No library-specific options. QSC conflict warning in README.
- **Patches:** none.
- **Tests:** "Tests are avaliable; currently all tests are passed." (`ports/libpng/README.md`). Run `pngtest` and `pngstest` with `pngtest.png`.

### libuv
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake` (4 lines)
- **Upstream:** fork `qnx-ports/libuv` (branch `qnx-v1.51.0`, 4 commits over upstream `v1.51.0`).
- **SDP / arch:** CI matrix 7.1 and 8.0. Tests on RPi4 with the QNX 8.0 quick-start image.
- **Build system:** CMake.
  - Flags: `CFLAGS += -D_QNX_SOURCE`, `LDFLAGS += -lm -lsocket`.
  - `CFLAGS += -DQNX_IOPKT` if `$QNX_TARGET/<cpu>/lib/libfsnotify.so` is absent, i.e. the build targets the io-pkt network stack rather than io-sock.
  - CMake options: `-DBUILD_SHARED_LIBS=ON -DLIBUV_BUILD_TESTS=ON`.
- **Patches in build-files:** none.
- **Fork source changes (from the fork):**
  - `core.c`:
    - Skips `_SC_IOV_MAX` on QNX.
    - `uv_os_getpriority`/`setpriority` return `UV_ENOSYS` ("QNX priority is not process-based").
  - `fs.c`: adds `__QNX__` to the futimens/fdatasync platform lists.
  - `internal.h`: `UV__POLLRDHUP 0` on QNX.
  - `udp.c`:
    - Treats QNX like BSD for disconnect.
    - Source-specific multicast is gated on `!QNX_IOPKT` instead of `!__QNX__`.
    - Enables the sendmmsg path on QNX.
  - `qnx.c`: `uv_uptime` fix.
  - CMake installs the tests and fixtures to `bin/libuv_tests`.
  - Several tests adjusted (fs, poll, udp, process-title, process-priority).
- **Tests:** "Only two tests should fail" (`ports/libuv/README.md`):
  - `ipc_tcp_connection` (timeout).
  - `pipe_connect_to_file` (known failure, tracked internally).

### libwebsockets
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake` (4 lines)
- **Upstream:** fork `qnx-ports/libwebsockets` (branch `qnx-v4.5.8`, 3 commits over upstream `v4.5.8`). Depends on libuv being built first (README and CI). The sample output shows "LWS: 4.5.0-v4.5.0".
- **SDP / arch:** CI matrix 8.0 only. README targets 8.0 on RPi4.
- **Build system:** CMake.
  - Flags: `CFLAGS += -D_QNX_SOURCE`, `LDFLAGS += -lsocket`.
  - `-DOPENSSL_EXECUTABLE=$(QNX_HOST)/usr/bin/openssl`. No other `LWS_*` options.
- **Patches in build-files:** none.
- **Fork source changes ("Adding support for QNX SDP8", from the fork):**
  - `LwsCheckRequirements.cmake`: `PTHREAD_LIB ""` on QNX.
  - `libwebsockets.h`: defines `ETHER_ADDR_LEN` for `__QNX__`.
  - `private-lib-plat-unix.h`: replaces the hand-rolled endian macros and `TCPCTL_KEEP*` defines with `#include <sys/param.h>`.
  - `adopt.c`: guards a NULL `desc` in a `%s` format.
- **Tests:** README runs `libwebsockets-test-server` and `libwebsockets-test-client` and shows sample output. No pass/fail counts.
  - Notes that the web test needs the `share` dir path that is hard-coded at build time.

### libxml2
- **Files:** `.gitignore`, `Makefile`, `README.md`, `build-hooks`, `common.mk`, `libxml2.patch`, `nto-aarch64-le/GNUmakefile`, `nto-x86_64-o/GNUmakefile`, `run_libxml2_tests.sh`
- **Upstream:** fork `qnx-ports/libxml2` (default branch `qnx-2.13.5`; branches `qnx-2.14.4`, `qnx-2.13.8` etc.), or an upstream tarball plus `libxml2.patch`.
  - README: "Currently these versions are tested: 2.13.5, 2.13.8, 2.14.4".
- **SDP / arch:** README: cross-compiled on Ubuntu 24.04 for QNX 8.0 aarch64le on RPi4. CI builds 8.0 only. Has x86_64 dirs too.
- **Build system:** autotools via `qmake-cfg.mk` and `build-hooks`.
  - Runs `autogen.sh`, then `make distclean` (comment: "autogen with configure passthrough does not work for QNX").
  - Then runs `configure --prefix=$INSTALL_ROOT/usr --exec-prefix=$INSTALL_ROOT/<cpu>/usr --without-python`.
  - `hook_postmake` builds the `check_PROGRAMS` and installs them to `usr/local/libxml2_tests`.
  - The README's alternative direct-configure recipe uses `--enable-static --with-legacy --with-lzma --with-zlib --with-python=no`.
- **Source patches in build-files (`libxml2.patch`, 2 hunks):**
  - `SAX2.c`: under `#ifdef __QNX__`, passes `" "` instead of a NULL `systemId` to the "Can't resolve URI: %s" warning (QNX printf does not accept NULL `%s`).
  - `parser.c`: `xmlFatalErrMsg` substitutes `""` when `msg == NULL`.
- **sed edits (README Docker path and CI):** `sed -i 's/1.16.3/1.16.1/g' libxml2/configure.ac`, which lowers the required automake version to match the container.
- **Fork source changes:** 1 commit "port to QNX" over `v2.13.5`, touching only `SAX2.c` (+5). This matches the SAX2 hunk above.
- **Tests:**
  - `run_libxml2_tests.sh` runs runsuite, runtest, testapi, testchar, testdict, testlimits, testparser, testrecurse.
  - runxmlconf and testModule are commented out ("Not Used" / "Deprecated").
  - The W3C xmlts20080827 suite download is optional. No results stated.

### libyaml
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** fork `qnx-ports/libyaml` (branch `qnx-0.2.5`, 1 commit).
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI builds 8.0 only.
- **Build system:** CMake.
  - `-DBUILD_SHARED_LIBS=ON -DINSTALL_INCLUDE_DIR=...`.
  - Toolchain: `CMAKE_CXX_STANDARD 14`, `-std=gnu++11`.
  - After install, copies `libyaml.so` to `libyaml-0.so.2`.
- **Patches in build-files:** none.
- **Fork source changes:** "Fix install directories for QNX": installs `yaml.h` to `INSTALL_INCLUDE_DIR` and the tests to `bin/libyaml_tests`.
- **Tests:** README runs `run-parser-test-suite` (on `echo 'foo: bar'`) and `run-parser` on a JSON file. No results stated.

### lz4
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake` (5 lines, incl. `set(MACHINE rpi4)`)
- **Upstream:** upstream `lz4/lz4`, default branch. No tag stated in README or CI.
- **SDP / arch:** CI matrix 7.1 and 8.0. README uses `~/qnx800`.
- **Build system:** CMake, run from `$(QNX_PROJECT_ROOT)/build/cmake`.
  - Flags: `CFLAGS += -D_QNX_SOURCE -D__EXT_UNIX_SOURCE -Wno-unused-parameter`.
  - CMake options: `-DWITH_STATIC_LIB=OFF -DWITH_SHARED_LIB=ON`.
- **Patches:** none.
- **Tests:** README does a manual round trip with `lz4`, `lz4cat`, `unlz4` on a user file. No results stated.

### mosquitto
- **Files:** `LICENSE.md`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** fork `qnx-ports/mosquitto` (branch `qnx_v2.0.15`, 6 commits).
- **SDP / arch:** README uses `~/qnx800`. CI builds 8.0 only. aarch64le, x86_64.
- **Build system:** CMake.
  - Flags: `FLAGS += -g -D_QNX_SOURCE`, `LDFLAGS += -lsocket`.
  - CMake options: `-DWITH_CJSON=OFF -DDOCUMENTATION=OFF -DBUILD_TESTING=$(BUILD_TESTING)`, `-DCMAKE_MODULE_PATH=$(PROJECT_ROOT)`.
  - The `install` target also builds the tests using the fork's `Makefile.qnx` files and rsyncs them to `usr/local/bin/mqtt_tests`.
- **Patches in build-files:** none.
- **Fork source changes ("QNXOSG-38: Port mosquitto for 8.0" and path fixes, from the fork):**
  - `src/CMakeLists.txt`: does not define `WITH_EPOLL` on QNX (`HAVE_SYS_EPOLL_H AND NOT QNX`).
  - `cmake/FindOpenSSL.cmake`: points at the SDP's `libssl.so`/`libcrypto.so`.
  - `client/CMakeLists.txt`: installs the clients into `mqtt_tests`.
  - Adds QNX test harnesses: `test/broker/test_qnx.py`, `test/lib/test_qnx.py`, `test/client/test_qnx.sh`, `test/*/Makefile.qnx`.
  - Edits about 9 broker test .py files and `ptest.py`.
- **Tests:** README runs the broker, client, and lib suites on target.
  - Known flaky test on RPI4: `./02-subscribe-qos1.py`. It failed when run in batch but succeeded individually (`ports/mosquitto/README.md`).

### pcre2
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** upstream `PCRE2Project/pcre2`, tag `pcre2-10.45`.
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI matrix 7.1 and 8.0.
- **Build system:** CMake.
  - Flags: `CFLAGS += -D_QNX_SOURCE -O3 -fPIC`. Toolchain sets `AWK=awk`.
  - No library-specific options (JIT etc. left at default).
  - After install, copies the `pcre2*.h` headers into the arch-independent include dir. QSC conflict warning in README.
- **Patches:** none.
- **Tests:** "Test related to `locale` are failing due to the lack of support in QNX image" (`ports/pcre2/README.md`). Run upstream `RunTest` on target with `testdata/`.

### pugixml
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `project_hooks.cmake`, `qnx.nto.toolchain.cmake`
- **Upstream:** upstream `zeux/pugixml`, default branch. No tag stated.
- **SDP / arch:** "Supports: QNX 8.0, 7.1 on aarch64le and x86_64". CI matrix 7.1 and 8.0, built with tests.
- **Build system:** CMake.
  - Flags: `FLAGS += -g -D_QNX_SOURCE`.
  - CMake options: `-DBUILD_SHARED_LIBS=ON -DPUGIXML_BUILD_TESTS=$(PUGIXML_BUILD_TESTS)`, `-DCMAKE_PROJECT_INCLUDE=project_hooks.cmake`.
  - `project_hooks.cmake` links `libmuslflt.a` with `--whole-archive`, which the README recommends for float conversion.
  - Toolchain: `CMAKE_CXX_STANDARD 14`, CXX uses `-Vgcc_nto<arch>_cxx`.
  - With tests ON, copies the .so files, `pugixml-check`, and `tests/` to `../staging/<cpu>`.
- **Patches:** none.
- **Tests:** run `./pugixml-check` on target. The muslflt hook warns that without it, float-conversion tests "will not pass". No results stated.

### sqlite
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `test.result`
- **Upstream:** upstream `sqlite/sqlite`, tag `version-3.50.0` (`SQLITE_VERSION = 3.50.0`).
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI matrix 7.1 and 8.0.
- **Build system:** autotools `configure`, called directly from `common.mk` (no toolchain file).
  - Cross settings: `--host=$(CPU)-*-$(OS)`, `CC="qcc -Vgcc_nto<cpuvardir>"`, `CXX=q++`, `AR=nto<cpu>-ar`.
  - configure options: `--enable-threadsafe --enable-session --enable-static --enable-fts3 --enable-fts4 --enable-fts5 --soname=legacy`.
  - Flags: `CFLAGS += -D_QNX_SOURCE -O2 -fPIC`.
  - Amalgamation defines: `-DSQLITE_ENABLE_FTS3_PARENTHESIS -DSQLITE_ENABLE_COLUMN_METADATA -DSQLITE_SECURE_DELETE -DSQLITE_ENABLE_UNLOCK_NOTIFY -DSQLITE_ENABLE_RTREE -DSQLITE_ENABLE_GEOPOLY -DSQLITE_USE_URI -DSQLITE_ENABLE_DBSTAT_VTAB -DSQLITE_SOUNDEX -DSQLITE_MAX_VARIABLE_NUMBER=250000`.
- **Patches:** none.
- **Tests:** README says only fuzz tests are available, with results in `test.result`. `ports/sqlite/test.result` records:
  - "fuzzcheck: 0 errors out of 46391 tests in 286.746 seconds".
  - sessionfuzz: "339 cases, 0 crashes".

### tinyxml2
- **Files:** `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** fork `qnx-ports/tinyxml2` (branch `qnx_10.0.0`, 3 commits).
- **SDP / arch:** README uses `~/qnx800`. CI builds 8.0 only.
- **Build system:** CMake.
  - `-DBUILD_SHARED_LIBS=1 -DBUILD_TESTING=$(BUILD_TESTING)`.
  - Toolchain `-std=gnu++11`. No `-D_QNX_SOURCE`.
- **Patches in build-files:** none.
- **Fork source changes ("Port for QNX", from the fork):**
  - `tinyxml2.h`: changes the platform guard from `__QNXNTO__` to `__QNX__` (selects the `std::` C functions path).
  - `xmltest.cpp`: prints `"(null)"` instead of passing NULL to `%s`.
- **Tests:** run `./xmltest` from `tinyxml2_tests` on target. No results stated.

### zlib
- **Files:** `.gitignore`, `Makefile`, `README.md`, `common.mk`, `nto-aarch64-le/Makefile`, `nto-x86_64-o/Makefile`, `qnx.nto.toolchain.cmake`
- **Upstream:** upstream `madler/zlib`, tag `v1.3.1`.
- **SDP / arch:** "Supports QNX7.1 and QNX8.0". CI matrix 7.1 and 8.0.
- **Build system:** CMake. Flags: `CFLAGS += -D_QNX_SOURCE -O3 -fPIC`. No library-specific options.
  - README notes that QSC ships `libz.so` from zlib-ng as a drop-in replacement, and warns about conflicts.
- **Patches:** none.
- **Tests:** "Tests are avaliable; currently all tests are passed." (`ports/zlib/README.md`). Run `example`, `example64`, `minigzip`, `minigzip64`.

### zstd
- **Files:** `Makefile`, `README.md`, `build-hooks`, `common.mk`, `nto-aarch64-le/GNUmakefile`, `nto-x86_64-o/GNUmakefile`
- **Upstream:** upstream `facebook/zstd`. README clones `-b v1.5.6`; CI pins commit `794ea1b0afca0f020f4e57b6732332231fb23c70`.
- **SDP / arch:** CI matrix 7.1 and 8.0. README uses `~/qnx800`.
- **Build system:** upstream plain Makefiles via `qmake-cfg.mk` and `build-hooks`.
  - `hook_configure` rsyncs the source into the build dir.
  - `hook_make` runs `make -C lib lib-release install` with `DESTDIR=$INSTALL_ROOT_nto PREFIX=/usr/local`, then builds `examples/`.
  - `hook_postmake` installs the example executables to `usr/local/examples`.
  - No QNX-specific CFLAGS or LDFLAGS beyond what the QNX make system supplies.
- **Patches:** none.
- **Tests:** not stated. The README only describes the example programs.

---

## 3. Summary table

"Fork" = source comes from a `qnx-ports/<name>` fork whose QNX commits change upstream source. The count in the patches column is "patch files or sed edits in build-files" plus "QNX commits in the fork" (fork counts are from the GitHub compare API, not from build-files).

| library | upstream version | SDP versions | build system | QNX-specific flags | source patches (count) | test results stated |
|---|---|---|---|---|---|---|
| benchmark | fork `qnx_v1.8.3` | 8.0 (CI) | CMake | `-D_QNX_SOURCE`; `BENCHMARK_ENABLE_WERROR=OFF`, `BENCHMARK_DOWNLOAD_DEPENDENCIES=OFF`, `BENCHMARK_USE_BUNDLED_GTEST=OFF`; `-std=gnu++11` | 0 in build-files; fork 3 commits (no pthread affinity/Threads on QNX, casts) | no (only the list of how to invoke ~40 tests) |
| c-ares | fork `qnx_v1.34` (= v1.34.3 + 4) | 7.1, 8.0 (README); CI 8.0 | autotools (build-hooks) | `-D_QNX_SOURCE`, `LIBS=-lregex`, `--disable-symbol-hiding --enable-tests-build-override --enable-qcc-compat`, FORTIFY to CPPFLAGS | 0 in build-files; fork 4 commits (qcc-compat configure option, QNX resolver-config reader `init_by_qnx_conf`) | no |
| cJSON | fork `qnx-v1.7.18` | 8.0 | CMake | `-DGCC_VER`, `CMAKE_SKIP_RPATH`; no `-D_QNX_SOURCE` | 0; fork 2 QNX commits (drop `-std=c89`, install tests) | yes: `parse_examples` file_test7 fails (float print precision) |
| googletest | fork `qnx_v1.13.0` | 7.1, 8.0 (tests on 8.0) | CMake | `CXX_STANDARD 17`, `-Wno-error=deprecated-declarations`; armv7 skipped on 8.0 | 0; fork 1 commit (install dirs, regex link, gmock-actions `<800` fix, death-test cwd fd `>=800`) | yes: 9 tests skipped as unlistable, gmock_leak_test_ expected failures (test.toml) |
| jansson | fork `qnx-v2.14` (2.14) | 8.0 | CMake | `-Wl,--allow-shlib-undefined`; link `libmuslflt.a` (whole-archive); `JANSSON_BUILD_DOCS=OFF` | 0; fork 1 (JANSSON_INSTALL_TESTS option) | no (script prints totals; floats need muslflt) |
| libevent | fork `qnx-2.1.12-stable` | 7.1, 8.0 | CMake | `-lsocket`, `EVENT__DISABLE_OPENSSL=ON`, Debug build | 0; fork 1 (CMAKE_REQUIRED_LIBRARIES socket; no SA_RESTART on QNX) | not stated |
| libexpat | upstream `R_2_6_4` | 7.1, 8.0 | CMake | `-D_QNX_SOURCE -fPIC -O3` | 0 | "Tests are not avaliable" |
| libjpeg-turbo | upstream `3.1.0` | 7.1, 8.0 | CMake | `-D_QNX_SOURCE` | 0 | yes: all tests pass (tjunittest) |
| libpng | upstream `v1.6.46` (+zlib v1.3.1) | 7.1, 8.0 | CMake | `-D_QNX_SOURCE -O3 -fPIC`, `AWK=awk` | 0 | yes: all tests pass (pngtest, pngstest) |
| libuv | fork `qnx-v1.51.0` | 7.1, 8.0 | CMake | `-D_QNX_SOURCE`, `-lm -lsocket`, `-DQNX_IOPKT` if no libfsnotify; `LIBUV_BUILD_TESTS=ON` | 0; fork 4 (priority ENOSYS, POLLRDHUP=0, IOV_MAX, fs/udp platform lists, tests) | yes: only 2 fail (ipc_tcp_connection, pipe_connect_to_file) |
| libwebsockets | fork `qnx-v4.5.8` | 8.0 | CMake | `-D_QNX_SOURCE`, `-lsocket`, `OPENSSL_EXECUTABLE=$QNX_HOST/usr/bin/openssl`; needs libuv | 0; fork 3 (no pthread lib, ETHER_ADDR_LEN, sys/param.h endian, NULL `%s` guard) | no (sample server/client output only) |
| libxml2 | fork `qnx-2.13.5` (tested 2.13.5/2.13.8/2.14.4) | 8.0 (CI; README mentions 7.1 sourcing) | autotools (build-hooks) | `--without-python`; autogen then distclean then configure | 3 in build-files (2-hunk `libxml2.patch`: NULL `%s` in SAX2.c and parser.c; 1 sed on configure.ac automake 1.16.3 to 1.16.1); fork 1 (SAX2.c) | no |
| libyaml | fork `qnx-0.2.5` | 7.1, 8.0 (README); CI 8.0 | CMake | `BUILD_SHARED_LIBS=ON`, `CXX_STANDARD 14`; copies to `libyaml-0.so.2` | 0; fork 1 (install dirs) | no |
| lz4 | upstream default branch (no tag) | 7.1, 8.0 | CMake (`build/cmake`) | `-D_QNX_SOURCE -D__EXT_UNIX_SOURCE -Wno-unused-parameter`; static OFF, shared ON | 0 | no (manual CLI round trip) |
| mosquitto | fork `qnx_v2.0.15` | 8.0 | CMake | `-g -D_QNX_SOURCE`, `-lsocket`, `WITH_CJSON=OFF`, `DOCUMENTATION=OFF` | 0; fork 6 (no epoll on QNX, SDP OpenSSL paths, QNX test harness) | yes: `02-subscribe-qos1.py` fails in batch on RPi4, passes alone |
| pcre2 | upstream `pcre2-10.45` | 7.1, 8.0 | CMake | `-D_QNX_SOURCE -O3 -fPIC`, `AWK=awk` | 0 | yes: locale-related tests fail (no locale support in image) |
| pugixml | upstream default branch (no tag) | 7.1, 8.0 | CMake | `-g -D_QNX_SOURCE`, muslflt whole-archive, `CXX_STANDARD 14`, `_cxx` variant | 0 | no (muslflt hook warns float tests fail without it) |
| sqlite | upstream `version-3.50.0` | 7.1, 8.0 | autotools configure (from common.mk) | `-D_QNX_SOURCE -O2 -fPIC`; threadsafe, session, fts3/4/5, `--soname=legacy`; 10 `SQLITE_*` defines | 0 | yes: fuzzcheck 0 errors / 46391; sessionfuzz 0 crashes / 339 |
| tinyxml2 | fork `qnx_10.0.0` | 8.0 | CMake | `BUILD_SHARED_LIBS=1`, `-std=gnu++11` | 0; fork 3 (`__QNXNTO__` to `__QNX__` guard, NULL `%s` in test) | no |
| zlib | upstream `v1.3.1` | 7.1, 8.0 | CMake | `-D_QNX_SOURCE -O3 -fPIC` | 0 | yes: all tests pass (example/minigzip) |
| zstd | upstream `v1.5.6` (CI commit 794ea1b0) | 7.1, 8.0 | upstream make (build-hooks) | none beyond the QNX make system defaults; `DESTDIR`/`PREFIX=/usr/local` | 0 | not stated |
