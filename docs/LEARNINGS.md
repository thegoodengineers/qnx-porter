# Learnings and status

Dated entries. Labels: [Verified] ran it ourselves, [To verify] from documentation, not yet run.

## 10 Nov 2026
- [Verified] QNX SDP 8.0 was not installed on the build machine (no `~/qnx800`, no `qcc`). Everything that
  needs no SDP is built and tested: 35 pytest tests on Linux (WSL Ubuntu 22.04) and in CI.
- [Verified] oss.qnx.com lists 2,498 packages (13,931 builds) through its public API; the qnx-ports GitHub
  organisation has 239 repos. Many obvious picks are already there: lz4, zstd, inih, pcre2, cJSON, expat,
  libuv, sqlite, zlib, utf8proc, miniz, libdeflate. Our 12 candidates are on neither
  (`results/candidates_check.csv`, from `scripts/check_candidates.py`).
- [Verified] QNX's `mkqnximage` runs QEMU targets only on Ubuntu hosts (QNX 8.0 docs, mkqnximage page), so
  the agent is Linux-host only; Windows users run it in WSL2.
- [To verify] SDP 8.0 ships `x86_64-pc-nto-qnx8.0.0-gcc` style drivers for autotools/meson. `qnx-porter doctor`
  checks it. If missing, switch `gnu_env()` / `meson_cross()` in `qnx_porter/qnx.py` to `qcc -Vgcc_ntox86_64`.
- [To verify] The QEMU image's sshd accepts root with the `--ssh-ident` key, and the image has `tar`.

- [Verified] From QNX's 8.0 docs (C Library Reference, io-sock Networking APIs, Migrating to QNX OS 8.0):
  libsocket still exists; dlopen, pthread_setname_np, pipe2, clock_gettime are in libc; mmap documents
  `MAP_ANON`; `gettid()` is in `<process.h>`; the socket API is ported from FreeBSD 14.3; SDP 8.0 uses GCC 12.
  Correction: QNX 8.0 *has* inotify (moved to libfsnotify); our first hint said it had none.
  These became 22 rows in docs/LINUX_ISMS.md, each with a test.
- [Verified] On the host, GCC's wording for `#error`, the one-argument `pthread_setname_np`, and ld's
  "multiple definition" matches what the parser expects (checked with gcc 11 in WSL and gcc 13 in CI).

## 11 Nov 2026: first real SDP install
- [Verified, corrected later the same day] The broken first install had gcc/g++ only with a version suffix
  (`x86_64-pc-nto-qnx8.0.0-gcc-12.2.0`). The complete install (build 141) also has the plain
  `x86_64-pc-nto-qnx8.0.0-gcc`. `gnu_tool()` in `qnx_porter/qnx.py` takes the plain name when present and the
  versioned one otherwise. `qcc -V` lists 12.2.0 `gcc_ntox86_64` (default) and `gcc_ntoaarch64le`.
- [Verified] Our first install was incomplete: 4,019 of 8,726 files under `~/qnx800` were 0 bytes (including
  `cc1` and the target libc), the Software Center log stopped mid-unarchive after a connection reset, and qcc
  failed with `cc1: Exec format error`. `qnx-porter doctor` now checks for this ("SDP complete") and
  compiles a socket program with qcc before saying ok.
- [Verified] Ubuntu 22.04's pip 22 cannot install a pyproject-only package in editable mode; upgrade pip
  with `--user` first. Docs updated.

## 11 Nov 2026: QNX 8.0 running in QEMU, first port
- [Verified] After the SDP was repaired, `qnx-porter doctor` is all ok, including a qcc compile and link.
- [Verified] The mkqnximage QEMU image boots QNX 8.0 (`QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc
  x86_64`), but sshd stops at boot: `/usr/libexec/sshd-auth does not exist or is not executable`. The SDP has
  `sshd-auth`; mkqnximage does not put it in the image. A one-line `local/snippets/ifs_files.custom` entry
  with an absolute path (`/usr/libexec/...`; a relative path lands in `/proc/boot`) fixes it, then
  `mkqnximage --build` (a snippet change alone says "Nothing to do"). Now in `scripts/qemu_target.sh`.
- [Verified] QNX's `qemu/net.sh` starts dnsmasq with `--except-interface=lo0`; on WSL that collides with
  10.255.255.254 on `lo`, so DHCP never starts. We run dnsmasq with `--except-interface=lo --port=0`.
- [Verified] On WSL, QEMU started in the background dies when the `wsl` call exits; `setsid nohup` keeps it.
- [Verified] The image has `sh`, `ksh`, `tar`, `diff`, `cmp`, `sed`, `awk`; no `bash`, `perl` or `python3`.
- [Verified] **json-c's first run said 0/25 tests passed, and it was our fault, not QNX's.** json-c registers
  its tests as shell scripts (`test1.test`), and CMake applies `CMAKE_CROSSCOMPILING_EMULATOR` only to
  executable targets, so ctest ran the scripts on Linux, which then tried to exec QNX binaries ("not
  found"). Fix: `ctest_on_target()` in `qnx_porter/target.py` reads `ctest --show-only=json-v1` and runs every
  test command on QNX, applying ctest's WILL_FAIL / regex / skip rules itself. Generated scripts also
  hard-code host paths, so `Target.sync()` makes the copied trees appear at the same absolute path on QNX
  with a path-space link (`ln -sP /data/qnx-porter/home /home`).
- [Verified] json-c json-c-0.18-20240915 then built with qcc in one round with **no patches**, and **24 of 25**
  of its own tests passed on QNX 8.0. `test_json_patch` dies with "Memory fault" on the case
  `Out of bounds (lower)` (patch path `/bar/-1`), where Linux prints "Invalid argument". Not investigated
  further yet. (Correction, 12 Nov: the SDP does have `x86_64-nto-qnx8.0.0-gdb`, and the image does keep
  core dumps in /data/var/dumper; see the 12 Nov entry.)

## 11 Nov 2026: the campaign on QNX 8.0 (four runs, logs in results/runs/)
Summaries as printed by `scripts/run_campaign.py`:
- Run 1: 4/10 built, 68/72 tests passed. Run 2: 9/10, 292/381. Run 3: 9/10, 372/381. Run 4: 10/10, 372/381.
  Then cmocka re-run after the regex fix: 46/46, giving the final 374/381 in results/ports.csv.

What each run taught us (all [Verified] on the target):
- **Our bugs, not QNX's:** (1) CMake reads `CMAKE_*_INIT` only into a fresh cache, so every flag fix after
  round 1 was silently ignored; mbedtls "received" `-lsocket` twelve times. (2) Autotools ran `configure` in
  the wrong folder. (3) Automake builds its test programs only inside `make check`, after we had copied the
  tree to QNX, so libsodium showed 0/80; it is 80/80 now. (4) `.sh` tests need `SH_LOG_COMPILER`. (5) A
  proved fix was reverted when it let the build reach the linker (new link errors are progress). (6) CMake's
  pass regexes let `.` match newlines; Python needs DOTALL (cmocka 44/46 -> 46/46).
- **QNX 8.0 facts the rules now encode** (each from a real error, see docs/LINUX_ISMS.md rows 14b-14f):
  `isinf`/`isfinite` become `__isinf`/`__isfinite` in libm (yyjson); `inet_pton` is `__inet_pton` in
  libsocket (mbedtls); `<sys/errno.h>` does not exist (nng); `<sys/socket.h>` includes `<stdbool.h>`, which
  breaks a library's own `bool` typedef (paho.mqtt.c); glibc's `htobe32` family is in `<net/netbyte.h>`, only
  with `__EXT_BSD` (paho.mqtt.c). Defining those as `-D` function-like macros broke the make shell, and
  bswap macros collided with QNX's own declarations, so the fix is a small header that includes
  `<net/netbyte.h>`; we compiled it with qcc under strict `_POSIX_C_SOURCE` and ran it on the target.
- **Tests that hang:** paho.mqtt.c's 103 tests wait up to 540 s each for an MQTT broker. A test killed on
  the host side kept running on QNX, so each test now runs under QNX's own `timeout -s KILL` (300 s cap).
  paho.mqtt.c is marked build-only in campaign.yaml with that reason.
- **Open failures (7 of 381 at the end of 11 Nov; 5 after 12 Nov):** json-c `test_json_patch` "Memory fault" on patch path `/bar/-1`; libconfig's
  test binary "Memory fault" at start; libmodbus's test script needs `killall` (QNX: `slay`); nng
  `httpclient` and resolver need the internet; nng `udp_test` returns a different error for two invalid
  addresses ("udp send ipc address" expects EADDRINVAL or ENOTSUP); nng `sockaddr_test` failed in the run and
  passed when re-run by hand. The two crashes were diagnosed on 12 Nov (below).

## 12 Nov 2026: the two "Memory fault" crashes, root-caused and fixed by the agent
- [Verified] We were wrong on 11 Nov: the SDP has `x86_64-nto-qnx8.0.0-gdb` 14.2 (we had looked with
  `head -3`, which showed only the aarch64 entries). The mkqnximage image runs `dumper -d /data/var/dumper`,
  so every crash left `<binary>.core` there.
- [Verified] json-c `test_json_patch`: backtrace from the core with the SDP gdb (debug build):
  `strlen <- _Putfld <- _Printf <- printf <- test_json_patch_op at tests/test_json_patch.c:31`. The test case
  after "Out of bounds (lower)" has neither `comment` nor `error`, so `printf("Testing '%s', ...")` gets NULL.
  json-c's own `test_json_patch.expected` contains `Testing '(null)', ...`: the test was written against
  glibc's behaviour.
- [Verified] libconfig `libconfig_tests`: `strlen <- _Putfld <- _Printf <- snprintf <-
  parse_string_and_compare_error at tests/tests.c:99`; `config_error_file()` is NULL when parsing a string,
  and the test expects the text `(null):...`.
- [Verified] The difference itself, one 8-line program (`printf("[%s]\n", (char *)NULL)`): glibc prints
  `[(null)]` and exits 0; on the QNX 8.0 target it prints `Memory fault (core dumped)` and exits 139.
  C makes this undefined, so neither libc is wrong; the tests are glibc-only. The libraries' own code is fine.
- [Verified] New in the agent: after the tests, `qnx_porter/crash.py` copies each core from the target,
  runs the SDP gdb on it with the target libraries, and writes the backtraces to `logs/crashes.log`. Builds
  now carry `-g` (debug info only, same code) so frames have file:line. The `printf-null` rule wraps each
  `%s` argument of the crashing call in `qnx_porter_str()`, which returns `"(null)"` for NULL, then rebuilds and
  re-runs; the patch is kept only if more tests pass. Result on QNX: json-c 25/25, libconfig 1/1 (its binary
  reports `13 tests; 13 passed, 0 failed`).

## 12 Nov 2026: 61 libraries, and what their failing tests were really about
Each item below was reproduced outside the campaign with a few-line program on the QNX 8.0 target and on
Linux; the programs and outputs are in [docs/qnx-reports/](qnx-reports/).
- [Verified] QNX `strtod()` is not correctly rounded (51% of 100,000 `%.17g` round trips wrong, up to 4 ulp);
  `sscanf("%lf")` is. Three libraries' tests hit it: pugixml, jansson (4 tests) and yaml-cpp (1 test).
  QNX `printf("%.20f")` also truncates the 20th decimal where glibc rounds it.
- [Verified] QNX `strftime()` writes nothing for `%Ex`, `%EX`, `%Ec` in the C locale; POSIX says they must
  fall back to `%x`, `%X`, `%c`. That is 2 of fmt's 3 failing tests; the third is `%a` printing `0x9.a52p+7`
  where glibc prints `0x1.34ap+10`, which C allows (not a bug, the test assumes glibc).
- [Verified] QNX `fchdir()` fails with ENOTDIR on a directory opened with `open(".", O_RDONLY)`; it works with
  `O_DIRECTORY`. googletest's QNX-only death-test code does exactly that, so `googletest-death-test-test` and
  `gtest_repeat_test` abort. With `O_DIRECTORY` added (one line), 61/61 death tests pass on QNX 8.0.
- [Verified] libsrtp's tests "shuffle" with `qsort()` and a comparator that answers at random (undefined in
  C). QNX's qsort then writes outside the array (480 of 2,000 calls in a guard-word test; glibc 0), which
  explains all three crashing libsrtp tests. The fix belongs in libsrtp's test helper, not in QNX.
- [Verified] Test-harness gaps, now fixed in the agent: `cmake -E copy_if_different` setup steps (libjpeg-turbo:
  8 of them feed 410 tests) now run as the QNX shell commands that do the same; the target had no resolv.conf
  (static address, dhcpcd never writes it), so libevent's evdns test found no name server.
- [Verified] New build rules: `wcswidth-compat` (flac; QNX libc has `wcwidth` only), `qcc-sysroot` (libpng's
  own script passes `--sysroot`, which qcc rejects), and stub archives are now visible to `find_library()`
  (libccd stopped at "Could NOT find required library librt").
- [Not investigated yet] libevent `main/fork`: after a forked child exits, the parent's event loop never
  sees its own `SIGUSR1`, and the test's alarm ends it. pcre2 test 8 (internal code sizes) and pcre2grep
  output differences.
- [Verified cause, environment] zstd: `zstreamtest` sets `hashLog = 29` (a hash table of about 2 GiB) and
  gets "Allocation error : not enough memory" on our 2 GiB QEMU target; `fuzzer` reached 5,151 of 30,000
  iterations before the runner's 300 s cap. Neither is a porting problem; a larger target would tell more.
- Expected not to port, and reported as such: libgpiod (Linux GPIO character device) and can-utils (SocketCAN).

## Still to do
1. Offer the two test fixes upstream (json-c, libconfig): `printf("%s", NULL)` in their tests is undefined C.
2. Runs with the language model on for the long tail (needs `QNX_PORTER_API_KEY` / `QNX_PORTER_MODEL`).
3. libcbor's tests (build cmocka for QNX first and point libcbor at it) and an MQTT broker for paho.mqtt.c.
4. Demo video shots, and aarch64 on real hardware.
