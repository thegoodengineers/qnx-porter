# jansson v2.14 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/akheron/jansson.git at `v2.14` (`684e18c927e8`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 209/213 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 6.9 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-link-libm.patch) | link-libm | rule | kept | qnx-toolchain.cmake | `__isinf` is in QNX's libm, not in libc: QNX's <math.h> implements isinf/isfinite/isnan as calls to __isinf etc. in libm, where glibc needs no library. Link with -lm. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
