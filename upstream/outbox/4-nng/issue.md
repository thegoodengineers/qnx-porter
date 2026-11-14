**Describe the bug**
`src/platform/posix/posix_udp.c` includes `<sys/errno.h>` (line 14 on `main`). That is not a POSIX header: glibc ships it as an alias for `<errno.h>`, but other C libraries do not ship it, and the build stops at that include.

**Expected behavior**
nng builds with a C library that has only the POSIX `<errno.h>`.

**Actual Behavior**
Building nng 1.9.0 for QNX 8.0:
```
.../src/platform/posix/posix_udp.c:14:10: fatal error: sys/errno.h: No such file or directory
   14 | #include <sys/errno.h>
```

**To Reproduce**
Build nng with a C library that has no `<sys/errno.h>` (here QNX SDP 8.0, `qcc`).

** Environment Details **
 - NNG version: seen with v1.9.0; the include is still at `src/platform/posix/posix_udp.c:14` in `main` at caf6f9f0b220
 - Operating system and version: QNX SDP 8.0, cross-compiled for x86_64
 - Compiler and language used: QCC 12.2.0, C
 - Shared or static library: static

**Additional context**
On `main` the file already includes `<errno.h>` a few lines below (inside `#ifdef NNG_PLATFORM_POSIX`), so the fix is to delete the `<sys/errno.h>` line. I have a one-line PR ready.
