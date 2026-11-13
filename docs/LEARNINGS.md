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
  These became the first 22 rows in docs/LINUX_ISMS.md, each with a test.
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
  QNX documents the requirement (the 8.0 `fchdir()` page lists ENOTDIR for it), so it is a QNX difference
  rather than a bug, and QNX's own googletest fork in qnx-ports makes the same one-line change.
- [Verified] QNX's own hand-made ports agree with two more findings: their jansson and pugixml ports link a
  separate float-conversion library (`libmuslflt.a`) because of the `strtod()` rounding, and their libxml2
  patch guards NULL `%s` arguments. Survey of their 21 ports that overlap ours:
  [docs/related/qnx-ports-survey.md](related/qnx-ports-survey.md).
- [Verified] libsrtp's tests "shuffle" with `qsort()` and a comparator that answers at random (undefined in
  C). QNX's qsort then writes outside the array (480 of 2,000 calls in a guard-word test; glibc 0), which
  explains all three crashing libsrtp tests. The fix belongs in libsrtp's test helper, not in QNX.
- [Verified] Test-harness gaps, now fixed in the agent: `cmake -E copy_if_different` setup steps (libjpeg-turbo:
  8 of them feed 410 tests) now run as the QNX shell commands that do the same; the target had no resolv.conf
  (static address, dhcpcd never writes it), so libevent's evdns test found no name server.
- [Verified] New build rules: `wcswidth-compat` (flac; QNX libc has `wcwidth` only), `qcc-sysroot` (libpng's
  own script passes `--sysroot`, which qcc rejects). A first attempt to make stub archives visible to `find_library()`
  (libccd stopped at "Could NOT find required library librt") did not work; see the final-run entry below.
- [Verified] libxml2 2.13.5 `testapi` crashes in library code, not test code: `xmlSAX2ResolveEntity()` warns
  "Can't resolve URI: %s" with a NULL `systemId` (backtrace `strlen <- vsnprintf <- xmlStrVASPrintf <- ...
  xmlWarnMsg`, SAX2.c). An application calling it the same way would crash on QNX too. libxml2's current
  master checks `systemId != NULL` first, so this is already fixed upstream; nothing to send. QNX's own
  libxml2 port patches the same line (`libxml2.patch` in qnx-ports/build-files).
- [Verified] nng `sockaddr_test` (7 of its 10 cases end in SIGSEGV): the test logger in
  `src/testing/util.c:207` prints `"%s: %s: %s"` with `msgid == NULL`, the same glibc-only `(null)` habit.
  The `printf-null` rule cannot place this fix: GCC compiled `nuts_logger()` as a tail call, so the
  backtrace jumps from `test_message_color_` to `nni_vlog` and never names the line that passes NULL. A limit
  of fixing from backtraces; a person (or the model, given the backtrace) has to find the caller.
- [Not investigated yet] libevent `main/fork`: after a forked child exits, the parent's event loop never
  sees its own `SIGUSR1`, and the test's alarm ends it. pcre2 test 8 (internal code sizes) ends in SIGSEGV
  inside recursive `compile_regex()` (core dump in `ports-2024/pcre2/logs/crashes.log`); deep recursion suggests
  the stack, but that is not confirmed.
- [Verified cause, environment] pcre2grep's "script callouts" test runs `/bin/echo`; our QEMU image has
  `echo` only as `/proc/boot/echo` (a toybox link), so the callout lines are missing from the output.
- [Verified cause, environment] zstd: `zstreamtest` sets `hashLog = 29` (a hash table of about 2 GiB) and
  gets "Allocation error : not enough memory" on our 2 GiB QEMU target; `fuzzer` reached about 7,000 of 30,000
  iterations before the runner's time cap (`ports-2024/zstd/logs/tests.log`). Neither is a porting problem; a larger target would tell more.
- Expected not to port, and reported as such: libgpiod (Linux GPIO character device) and can-utils (SocketCAN).

## 12 Nov 2026: the final 61-library run, and a check against QNX's own ports
- [Verified] The final run (`results/runs/campaign-7.log`, code `da9da0c` for the full pass) took 1 h 54 min.
  A DNS outage in WSL at 08:07 stopped 6 libraries at `git clone`. Those 6 were re-run into the same
  log (code `5fbe7c5`, then `865406c`; each section names its code), with sqlite (configure picked up the build host's editline headers, now
  `--disable-editline --disable-readline`), 4 `printf-null` ports and libccd. Result: 57 of 61 built;
  1332 of 1366 tests passed, in the 33 libraries whose suites ran at least one test. `campaign-6.log` is the earlier
  61-library pass, whose code changed during the run (rules were added between libraries).
- [Verified] Two patch-quality bugs, found by reading our own patches: rules rewrote CRLF files with LF (the
  tinyxml2 patch replaced all 2,743 lines of `xmltest.cpp` to change 4), and `printf-null` put its helper
  after the last `#include` even when that include sat in a non-Windows `#else` branch, which would break
  the patch on MSVC. Both are fixed and tested, and the 4 affected ports were re-run.
- [Verified] 21 of our libraries have a hand-made recipe in qnx-ports. In 6 of them, qnx-porter found the
  same QNX change or cause independently. In 3 (libxml2, libwebsockets, libuv), it found the same problem at
  the same line but did not fix it. 9 needed no source change on either side. 3 differ or cannot be
  compared. Table and caveats (versions and targets differ):
  [docs/related/qnx-ports-comparison.md](related/qnx-ports-comparison.md).
- [Verified] The unpatched c-ares resolves names on our target (`ahost`, `adig`), because the image has
  `/etc/resolv.conf`. QNX's fork adds a reader for QNX's own resolver configuration; that only matters on
  images without the file, and we did not test one.
- [Verified] libccd's "Could NOT find required library librt": the empty stub `librt.a` was there from
  round 1, but with `CMAKE_SYSROOT` set, CMake re-rooted its absolute path under the SDP and never looked
  at the real folder (`cmake --debug-find`). The toolchain now makes the stub folder's parent a find root
  and searches `/stubs` in it; libccd builds and passes 3 of 3. The other 60 libraries were not re-run
  with this toolchain change.
- [Verified] Rust gate for crate porting: the `x86_64-pc-qnx` target (tier 3) with nightly
  1.102.0, `-Zbuild-std` and `qcc` as linker. A hello world, plus 12 of 12 std checks (threads, channels,
  fs, time, TCP/UDP loopback, `process::Command`, env, unwinding), ran on the QNX 8.0 x86_64 target.

## 12–13 Nov 2026: aarch64 on QEMU, 61 libraries
- [Verified] QNX 8.0 aarch64 on QEMU `virt`, fully emulated: 57 of 61 built, the same 57 as x86_64.
  1314 of 1350 tests passed, in the 33 libraries whose suites ran at least one test
  (`results/runs/campaign-aarch64-2.log`; `campaign-aarch64-1.log` is the first attempt, which stopped).
- [Verified] Three aarch64-only build or crash differences, each now a rule with a test:
  - **Word size (cmocka):** `cmocka.h` guesses 64-bit only from glibc's `__WORDSIZE` or `__x86_64__`. On
    aarch64 it assumed 32 bits and redefined `uintptr_t` as `unsigned int`. Rule `wordsize-64` fixes it, and
    cmocka passes 46/46.
  - **Unsigned char (yaml-cpp):** plain `char` is unsigned on aarch64, so a test's `{-58}` in a `char` array
    is a narrowing error there. Rule `signed-char` adds `-fsigned-char`.
  - **strlen name (json-c):** QNX's aarch64 libc names its strlen frame `__generic_strlen`. The `printf-null`
    crash triage now recognises it, and json-c goes from 24/25 to 25/25 on aarch64 too.
- [Verified] Under host overload, ssh to the emulated target timed out ("Connection timed out during banner
  exchange"). Running the SBOM scan and builds beside it caused that. libjpeg-turbo, flac and nng lost tests
  that way. Re-run on a quiet host:
  - libjpeg-turbo 574/574 (564/574 under load);
  - nng 80/86;
  - flac 6/10; two of its tests hit the 300 s cap on the emulated CPU.

  Lesson: an emulated target needs the machine to itself.
- [Verified] Earlier in the run, the target stopped answering, and a DNS outage made 60 of 61 clones fail in
  seconds. Since then, the campaign retries clones when the network is down, restarts a target that stops
  answering (`--restart-target`), and continues with `--resume`. A sleeping laptop also pauses WSL and QEMU:
  12 hours were lost overnight before the sleep setting was changed.
- Differences from x86_64 that are not explained yet:
  - libsrtp 9/12 (8/12 on x86_64);
  - libjpeg-turbo registers 574 tests on aarch64 against 590 on x86_64;
  - nng 80/86 against 82/86.

## Still to do
1. Offer the two test fixes upstream (json-c, libconfig): `printf("%s", NULL)` in their tests is undefined C.
2. Runs with the language model on for the long tail (needs `QNX_PORTER_API_KEY` / `QNX_PORTER_MODEL`).
3. libcbor's tests (build cmocka for QNX first and point libcbor at it) and an MQTT broker for paho.mqtt.c.
4. Demo video shots, and the same campaign for aarch64 on QEMU.
