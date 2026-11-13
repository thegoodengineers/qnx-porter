# Draft pull request for nng (not sent)

- **Upstream:** https://github.com/nanomsg/nng
- **Patch:** [`0001-posix_udp-include-errno.h-instead-of-sys-errno.h.patch`](0001-posix_udp-include-errno.h-instead-of-sys-errno.h.patch),
  made with `git format-patch` against tag `v1.9.0` (`29aff2bacc9e`, the tag in `campaign.yaml`). Source: the
  port's kept patch [`ports/nng/patches/0001-header-alias-posix-udp-c.patch`](../../../ports/nng/patches/0001-header-alias-posix-udp-c.patch).
  This one was not on the first list of candidates; `scripts/upstream.py` found it among the ports' kept patches.
- **Upstream today:** `main` at `caf6f9f0b220` (13 Nov 2026) still has `#include <sys/errno.h>` at
  `src/platform/posix/posix_udp.c:14`, and now also `#include <errno.h>` at line 20 (inside
  `#ifdef NNG_PLATFORM_POSIX`). So the patch does not apply to `main` as it is; there the same fix is to delete
  line 14. We have not built that variant.

## Why upstream would want it
Portability. `<sys/errno.h>` is not a POSIX header: glibc ships it as an alias, other C libraries do not ship it
at all, and the build stops at this include. POSIX's `<errno.h>` declares everything the file uses.

## Verification, from our logs
Without the patch, the QNX 8.0 build stopped here (`ports/nng/logs/round-01.log`):
```
.../src/platform/posix/posix_udp.c:14:10: fatal error: sys/errno.h: No such file or directory
   14 | #include <sys/errno.h>
```
With the patch, nng built and its tests ran on the QNX 8.0 x86_64 target (`ports/nng/logs/tests.log`):
```
82/86 tests passed on the QNX target
```
The four failures are `nng.core.sockaddr_test`, `nng.platform.udp_test`, `nng.httpclient` and `nng.ipc`.
`docs/LEARNINGS.md` traces `sockaddr_test` to the test logger's NULL `%s`, `udp_test` to a different error
code for two invalid addresses, and `httpclient` to needing the internet; `ipc` has not been investigated. The
patch does not claim anything about them: without it nothing builds, so there is no before-and-after.

**Not verified:** the delete-line variant on `main`, and a Linux build with the patch.

## PR title
```
posix_udp: include <errno.h> instead of <sys/errno.h>
```

## PR body
```
src/platform/posix/posix_udp.c includes <sys/errno.h>, which is not a POSIX header. glibc
provides it as an alias, but other C libraries do not ship it, and the build stops there
(seen with QNX 8.0). POSIX's <errno.h> declares everything the file uses, and main already
includes it a few lines below, so the <sys/errno.h> line can simply go.

Tested on v1.9.0 (replacing the include with <errno.h>): nng builds for QNX 8.0 x86_64 and
82 of its 86 tests pass on the target.
```
