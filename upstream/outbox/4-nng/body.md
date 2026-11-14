fixes #ISSUE_NUMBER posix_udp.c includes the non-POSIX <sys/errno.h>

`src/platform/posix/posix_udp.c` includes `<sys/errno.h>`, which is not a POSIX header. glibc provides it as an alias, but other C libraries do not ship it, and the build stops there (seen with QNX 8.0). POSIX's `<errno.h>` declares everything the file uses, and the file already includes it a few lines below, so the `<sys/errno.h>` line can simply go.

Tested: on v1.9.0, replacing the include with `<errno.h>` let nng build for QNX 8.0 x86_64, and 82 of its 86 tests passed on the target. This branch, on current `main`, builds on Linux (Ubuntu 22.04, gcc 11.4, `-DNNG_TESTS=ON`); it has not been rebuilt for QNX on `main`.
