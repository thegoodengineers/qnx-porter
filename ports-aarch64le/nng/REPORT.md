# nng v2.1.0 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/nanomsg/nng.git at `v2.1.0` (`0912dcbd63f2`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 3/64 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 74.0 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-header-alias-posix-udp-c.patch) | header-alias | rule | kept | src/platform/posix/posix_udp.c | <sys/errno.h> is a glibc alias QNX 8.0 does not ship; POSIX's <errno.h> declares the same things, and QNX has it. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
