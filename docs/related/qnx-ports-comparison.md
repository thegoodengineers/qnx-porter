# qnx-porter's automatic ports vs QNX's hand-made ports

QNX maintains hand-made port recipes for open-source libraries in the GitHub organisation
[qnx-ports](https://github.com/qnx-ports), mainly [`qnx-ports/build-files`](https://github.com/qnx-ports/build-files).
21 of the 61 libraries in our campaign have a recipe there. This page compares, library by library, what qnx-porter
did on its own with what QNX's engineers did by hand. It covers the changes each side needed and the test results
each side states. Our side is the x86_64 campaign of 12 Nov 2026 (`results/runs/`, `ports/<name>/`). QNX's side is
build-files commit `1964dba` plus the QNX commits in their forks; [`qnx-ports-survey.md`](qnx-ports-survey.md) has
every detail and says which lines come from the forks.

**Read this first: the two sides are not the same experiment.**
- **Versions differ** for 13 of the 21 libraries (table below). A change one side needed may simply not exist in
  the other side's version.
- **Targets differ.** QNX's READMEs report tests on a Raspberry Pi 4 (aarch64) and sometimes on x86_64 QEMU. Ours
  ran on x86_64 QEMU only (aarch64 on QEMU is a separate run).
- **Test coverage differs.** QNX's recipes mostly describe how to run tests and state few results. We ran each
  library's own registered test suite, but for some libraries that suite was empty or could not run on the target.

So "agreement" below means: the same QNX difference was found at the same place, independently. It does not
mean the two ports are interchangeable.

## Summary

Of the 21 libraries, qnx-porter built 19 for QNX 8.0 with no person involved. libwebsockets and libuv did not
build in this run, which used rules only, without the model step.

| outcome | libraries | count |
|---|---|---|
| the same QNX change or cause, found independently | libevent, mosquitto, googletest, tinyxml2, jansson, pugixml | 6 |
| the same problem at the same place, which QNX fixed and our run did not | libxml2, libwebsockets, libuv | 3 |
| no QNX source change needed on either side, and both build | zlib, libjpeg-turbo, expat, libyaml, libpng, lz4, zstd, pcre2, sqlite | 9 |
| different, or not comparable | c-ares, benchmark, cJSON | 3 |

Wherever both sides changed the same thing, the two changes have the same effect, though the mechanism can
differ (libevent: QNX's fork leaves `SA_RESTART` out on QNX, our rule defines it as 0). The difference is in
coverage: QNX's ports fix 3 problems that our run only reports. QNX's recipes also make
changes that only a test on the target would reveal, and for those libraries our run had no runnable tests.

## Library by library

| library | our version / QNX's | what QNX's port changes | what qnx-porter did | agreement |
|---|---|---|---|---|
| libevent | 2.1.12 / 2.1.12 | no `SA_RESTART` on QNX; link libsocket | rules `sa-restart` (defines it as 0) and `link-libsocket` | **same two changes** |
| mosquitto | 2.0.20 / 2.0.15 | link libsocket; SDP OpenSSL paths; no epoll; QNX test harness | rule `link-libsocket`; built with `WITH_TLS=OFF` | same libsocket change; TLS not compared |
| googletest | 1.15.2 / 1.13.0 | link libregex; `open(".", O_RDONLY \| O_DIRECTORY)` for death tests on 8.0; install dirs | rule `link-libregex`; the `O_DIRECTORY` fix found from the core dump of the 2 aborting tests ([report](../qnx-reports/fchdir-o-rdonly.md)), verified by hand, not applied by the campaign | **same two changes**; ours needed a person for the second |
| tinyxml2 | 10.0.0 / 10.0.0 | test prints `"(null)"` instead of passing NULL to `%s` (`xmltest.cpp`) | rule `printf-null`, from the crash backtrace, same call in `xmltest.cpp` | **same change** |
| libxml2 | 2.13.5 / 2.13.5 | pass `" "` instead of a NULL `systemId` to the `Can't resolve URI: %s` warning (`SAX2.c`); a second NULL guard in `parser.c` | `testapi` crashes; the backtrace ends in `xmlWarnMsg` (`SAX2.c:98`) formatting `Can't resolve URI: %s` with NULL. Found, not fixed: the printf is inside libxml2's generic error code, which the rule does not rewrite | **same problem found** at the same line; QNX fixed it, we report it |
| jansson | 2.14 / 2.14 | links QNX's `libmuslflt.a` so float conversion tests pass | 4 of 213 tests fail, all float parsing; traced to QNX's `strtod` ([report](../qnx-reports/strtod-rounding.md)) | **same cause**; QNX works around it, we report it |
| pugixml | 1.14 / default branch | links `libmuslflt.a` (same reason) | 1 test binary fails, on float round trips; same `strtod` cause | **same cause** |
| libwebsockets | 4.3.3 / 4.5.8 | `ETHER_ADDR_LEN`; endian and `TCPCTL_KEEP*` from `<sys/param.h>`; no pthread lib; NULL `%s` guard | build fails at `TCPCTL_KEEPCNT` in `private-lib-plat-unix.h`; no rule for it (the model step was off in this run) | **same place**; QNX fixed it, we did not |
| c-ares | 1.34.3 / 1.34.3 + 4 commits | reads the resolver configuration through QNX's own config (`init_by_qnx_conf`) | built with no change; its test suite is not built by default, so 0 tests ran. By hand on our target, our `ahost` and `adig` resolve `github.com` | **not the same**: our image has `/etc/resolv.conf`, so the change QNX made was not needed there; an image without it was not tried |
| benchmark | 1.9.1 / 1.8.3 | skips pthread affinity and the Threads link on QNX | built with no change; tests turned off in `campaign.yaml` | not comparable (versions; no tests on our side) |
| cJSON | 1.7.18 / 1.7.18 + 18 upstream commits | drops `-std=c89` on QNX; installs tests | built with no change; 19 of 19 tests pass | QNX's README says `file_test7` fails; on our x86_64 build it passes (re-run by hand: 15 of 15 cases in `parse_examples`). Their result is on aarch64 with a newer fork |
| libyaml | 0.2.5 / 0.2.5 | install directories only | no change; 2 of 2 pass | same: nothing QNX-specific in the source |
| zlib | 1.3.1 / 1.3.1 | none | no change; 2 of 2 pass | **same**: both pass with no change |
| expat | 2.6.4 / 2.6.4 | none | no change; `runtests` and `runtests_cxx` pass | same; QNX's README says "Tests are not avaliable", ours ran them |
| libjpeg-turbo | 3.0.4 / 3.1.0 | none | no change; 590 of 590 pass | **same**: all pass with no change |
| libpng | 1.6.44 / 1.6.46 | none | build-flag rule `qcc-sysroot` only; its 32 tests are CMake scripts and the target has no `cmake` | build agrees; QNX says all tests pass, ours could not run them |
| lz4 | 1.10.0 / default branch | none | no change; lz4's CMake build registers no tests | build agrees; no tests on either side |
| zstd | 1.5.6 / 1.5.6 | none | no change; 1 of 4 pass: `fuzzer` timed out, `zstreamtest` reports an allocation error, `playTests` failed under ksh; not investigated | build agrees; QNX states no test results |
| pcre2 | 10.44 / 10.45 | none | no change; 1 of 3 pass. RunTest skips the locale tests (no `locale` command on the target). Test 8 crashes with SIGSEGV deep in recursive `compile_regex`; the cause is not confirmed. `pcre2grep`'s callout test runs `/bin/echo`, which our image has only at `/proc/boot/echo` | build agrees; QNX says the locale tests fail, ours skipped them and found two other failures |
| sqlite | 3.47.2 / 3.50.0 | none | no source change; configured `--disable-tcl --disable-editline --disable-readline` (otherwise the build host's Tcl and editline headers are picked up); build only, its tests need Tcl on the target | build agrees (no source change on either side); QNX ran its fuzz tests (0 errors), we ran none |
| libuv | 1.49.2 / 1.51.0 | 4 commits: priority calls return `UV_ENOSYS`, `UV__POLLRDHUP 0`, no `_SC_IOV_MAX`, futimens/fdatasync, UDP, uptime | build stops in `uv_uptime()` (`src/unix/qnx.c:117`): QNX 8.0's `struct qtime_entry` has no `nsec` member; no rule for it (the model step was off) | **same place** (QNX's fork changes `uv_uptime`); QNX fixed it, we did not |

## What this says about qnx-porter

- **Where it agrees, it found the same QNX differences, on its own and from the error output.** libevent,
  mosquitto, googletest, tinyxml2, libxml2, jansson and pugixml. Every rule involved (`sa-restart`,
  `link-libsocket`, `link-libregex`, `printf-null`) was committed before the survey of QNX's recipes (git
  history), and each was written from an error our own campaign hit.
- **Finding is not fixing.** For libxml2, libwebsockets and googletest's death tests, qnx-porter found the place
  QNX changed but the campaign (rules only, no model step) did not change it. Those stay listed under "Still
  failing" in each port's `REPORT.md`.
- **Tests decide what it can see.** c-ares' resolver change and benchmark's affinity change are runtime
  behaviour that qnx-porter only catches if the library's own tests exercise it on the target. With 0 tests run,
  it cannot.
- **What it adds:** every change has a reason and a patch file, every number comes from a run on a QNX target,
  and the same command ports libraries QNX has not done yet: 40 of our 61 have no recipe in qnx-ports.
