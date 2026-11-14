# cmocka cmocka-2.0.2 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://gitlab.com/cmocka/cmocka.git at `cmocka-2.0.2` (`fefa2b8a0231`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 88/89 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 7.5 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-qnx-source.patch) | qnx-source | rule | kept | qnx-toolchain.cmake | `PATH_MAX` is in <limits.h>, which src/cmocka.c already includes, so a strict feature-test macro hid it. -D_QNX_SOURCE exposes POSIX and QNX extensions in QNX's headers, as _GNU_SOURCE does on glibc. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
