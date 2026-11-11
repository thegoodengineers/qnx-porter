# nng v1.9.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/nanomsg/nng.git at `v1.9.0` (`29aff2bacc9e`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 82/86 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 4.1 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-header-alias-posix-udp-c.patch) | header-alias | rule | kept | src/platform/posix/posix_udp.c | <sys/errno.h> is a glibc alias QNX 8.0 does not ship; POSIX's <errno.h> declares the same things, and QNX has it. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
