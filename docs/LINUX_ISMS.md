# Linux-isms that break on QNX 8.0: the corpus behind the rules

Rows 14b-14f were found by running the campaign on a real QNX 8.0 target (11 Nov 2026), not from documentation.

Each row is a pattern Linux-first C code uses, what QNX 8.0 has instead, where that fact comes from, and
what qnx-porter does about it. Every row has a test in `tests/test_linux_isms.py` (runs in CI without QNX).
Rules that rewrite code are also compiled with the host compiler and `-D__QNX__` in CI.

**Sources** (QNX SDP 8.0 documentation, read 10 Nov 2026):
- [LIB] QNX OS C Library Reference, `qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/` (per function:
  header and "Library:" line)
- [SOCK] io-sock User's Guide, Networking APIs: "socket functions ported from FreeBSD" (FreeBSD 14.3 man pages)
- [MIG] Migrating to QNX OS 8.0: C and C++ applications; Toolchain ("GCC 12.x")

Labels: **rule** = deterministic change; **rule, proved** = applied alone and reverted if the rebuild still shows
the error; **hint** = no safe mechanical fix, the model (or a person) gets a QNX-specific hint.

| # | Linux-ism | On QNX 8.0 | Source | qnx-porter | Test |
|---|---|---|---|---|---|
| 1 | `#include <sys/epoll.h>` that the file never uses | no epoll | [LIB] no entry | rule `guard-linux-header`: wrap in `#ifndef __QNX__` | `test_unused_linux_only_header_is_guarded` |
| 2 | epoll actually used | use `poll()`/`select()`, or `ionotify()` | [LIB] ionotify: libc, `<unistd.h>` | hint | `test_used_epoll_is_left_for_the_model_with_a_qnx_hint` |
| 3 | `<sys/sendfile.h>`, `<sys/sysinfo.h>`, `<sys/eventfd.h>`, `<sys/timerfd.h>`, `<sys/signalfd.h>`, `<sys/random.h>`, `<execinfo.h>`, `<features.h>`, `<mcheck.h>` unused | not provided | [LIB] no entries | rule `guard-linux-header` | `test_every_listed_linux_header_is_guarded_when_unused` |
| 4 | `sendfile()` used | none: read()/write() loop | [LIB], [SOCK] not listed | hint | `test_sendfile_use_gets_a_hint_not_a_rewrite` |
| 5 | `<linux/*.h>` kernel headers | do not exist | - | hint | `test_linux_kernel_headers_get_a_hint` |
| 6 | `<byteswap.h>`, `bswap_16/32/64` | GCC 12 builtins | [MIG] Toolchain | rule `byteswap-builtins` | `test_byteswap_maps_to_gcc_builtins` |
| 7 | `prctl(PR_SET_NAME, name)` | `pthread_setname_np(pthread_t, const char *)`, libc, `<pthread.h>` | [LIB] pthread_setname_np | rule, proved `prctl-set-name` (only when every prctl call is PR_SET_NAME) | `test_prctl_set_name_becomes_pthread_setname_np`, `test_prctl_with_other_options_is_not_rewritten` |
| 8 | FreeBSD `pthread_set_name_np(tid, name)` | `pthread_setname_np(tid, name)` | [LIB] | rule `pthread-setname` | `test_freebsd_pthread_set_name_np_is_renamed` |
| 9 | macOS one-argument `pthread_setname_np(name)` | two arguments, thread first | [LIB] | rule `pthread-setname-args` (on GCC's "too few arguments") | `test_macos_one_argument_setname_gets_the_thread` |
| 10 | `#if __linux__ ... #elif __FreeBSD__ ... #else #error unsupported` | QNX matches no branch | [SOCK] FreeBSD-derived stack | rule, proved `qnx-platform-guard`: add `\|\| defined(__QNX__)` to the BSD, then Unix, then Linux branch | `test_unsupported_platform_error_lets_qnx_join_the_bsd_branch`, `test_ifdef_linux_only_chain`, `test_error_outside_an_os_chain_is_not_touched`, `test_a_rule_that_needs_proof_is_reverted_when_the_rebuild_disagrees` |
| 11 | `MAP_ANONYMOUS` | documented as `MAP_ANON` | [LIB] mmap | rule `map-anon`: `-DMAP_ANONYMOUS=MAP_ANON` | `test_map_anonymous_becomes_map_anon` |
| 12 | `send(..., MSG_NOSIGNAL)` not visible | FreeBSD stack: `SO_NOSIGPIPE` or ignore SIGPIPE | [SOCK] | rule `msg-nosignal` (`=0`) only if the library already ignores SIGPIPE; otherwise hint | `test_msg_nosignal_only_when_the_library_already_ignores_sigpipe` |
| 13 | `-ldl`, `-lrt`, `-lpthread` | dlopen, clock_gettime, timer_create, shm_open, mq_open, pthread_* are in libc | [LIB] "Library: libc" | rule `stub-lib`: empty archive, no build-file edit | `test_libraries_that_are_libc_on_qnx` |
| 14 | sockets in libc | `libsocket` | [MIG] Security ("libc, kernel, and libsocket functions") and the BSP buildfile listing `/lib/libsocket.so` | rule `link-libsocket` | `test_link_rules` |
| 14b | `isinf()`, `isfinite()`, `sqrt()` with no `-lm` | `__isinf`, `__isfinite`, math functions are in `libm`, not libc | `nm -D` on SDP 8.0 `libm.so` / `libc.so`; found porting yyjson | rule `link-libm` | `test_math_classification_macros_need_libm_on_qnx` |
| 14c | `inet_pton()` linked without libsocket | QNX's `<arpa/inet.h>` does `#define inet_pton __inet_pton`; `__inet_pton` is in libsocket | SDP 8.0 header and `nm -D libsocket.so`; found porting mbedtls | rule `link-libsocket` (matches the `__` names) | `test_inet_pton_is_renamed_by_qnx_headers_and_lives_in_libsocket` |
| 14d | `<sys/errno.h>`, `<sys/signal.h>`, `<sys/syslog.h>`, `<sys/unistd.h>`, `<sys/fcntl.h>`, `<sys/termios.h>`, `<sys/dirent.h>` | not shipped; the POSIX `<errno.h>` etc. are | SDP 8.0 `target/qnx/usr/include`; found porting nng | rule `header-alias` | `test_sys_header_aliases_qnx_does_not_ship` |
| 14e | a library's own `typedef unsigned int bool;` | QNX's `<sys/socket.h>` includes `<stdbool.h>` (via `io-sock/types_fbsd.h`) | SDP 8.0 headers; found porting paho.mqtt.c | rule, proved `bool-typedef` | `test_own_bool_typedef_after_qnx_sys_socket`, `test_a_proved_fix_that_lets_the_build_reach_the_linker_is_kept` |
| 14f | `<endian.h>`, `htobe32()`, `le64toh()` | no `<endian.h>`; both QNX targets are little-endian; `<gulliver.h>` | SDP 8.0 headers; found porting paho.mqtt.c | `guard-linux-header` when unused; rule `endian-builtins` (`__builtin_bswapNN`) when used | `test_unused_endian_h_is_guarded_and_used_gets_gulliver_hint`, `test_glibc_endian_functions_become_builtins_on_little_endian_qnx` |
| 15 | inotify in libc | in `libfsnotify` (QNX 8.0 moved it) | [MIG] C and C++ applications | rule `link-libfsnotify` | `test_inotify_links_libfsnotify` |
| 16 | header-defined globals (`int counter;` in a .h) | GCC 12 defaults to `-fno-common`: "multiple definition" | [MIG] Toolchain | rule `fcommon` | `test_gcc10_no_common_link_error_gets_fcommon`, `test_gcc10_common_symbols_are_fixed_with_real_linker_output` |
| 17 | `gettid()` | `<process.h>` | [LIB] gettid | rule `add-include` | `test_qnx_header_locations` |
| 18 | `dl_iterate_phdr()` | `<sys/link.h>` | [LIB] | rule `add-include` | `test_qnx_header_locations` |
| 19 | `getopt_long`, `memalign`, `strsep`, `pipe2` without their header | `<getopt.h>`, `<malloc.h>`, `<string.h>`, `<unistd.h>` | [LIB] | rule `add-include` | `test_qnx_header_locations` |
| 20 | `itoa()`, `ltoa()`, `utoa()` | removed from QNX 8.0 libc: use `snprintf()` | [MIG] | hint | `test_removed_itoa_gets_the_snprintf_hint` |
| 21 | POSIX/BSD function hidden by `-std=c99` | `-D_QNX_SOURCE` | [LIB] | rule `qnx-source` | `test_header_already_included_means_a_feature_macro_hid_it` |
| 22 | warnings promoted by `-Werror` | GCC 12 warns about more | [MIG] Toolchain | rule `no-werror` | `test_werror_and_no_repeats` |

## Not turned into rules, on purpose
- **epoll, sendfile, timerfd, signalfd, eventfd in use:** replacing them changes how the library behaves under
  load. A rule would compile and be wrong. They get a hint and go to the model or a person, and the report
  says so.
- **`MSG_NOSIGNAL` without SIGPIPE handling:** defining it as 0 would let a closed peer kill the process.
- **`SOCK_CLOEXEC` / `accept4`:** io-sock is ported from FreeBSD 14.3, which has them; we have not seen them
  missing on a real SDP yet, so there is a hint and no rule. Revisit after the first campaign.

## Adding a row
Find the fact in QNX's documentation, write the test with the exact error line from a real build log,
then the rule. See [CODELAB.md](CODELAB.md) step 6.
