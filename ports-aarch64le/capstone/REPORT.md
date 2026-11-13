# capstone 5.0.3 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/capstone-engine/capstone.git at `5.0.3` (`5cca00533dad`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 1 round(s) |
| Library's own tests | 24/24 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 12.0 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-printf-null-test-iter-c.patch) | printf-null | rule | kept | tests/test_iter.c | Crash on QNX: printf() at tests/test_iter.c:330 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C leaves it undefined. Each %s argument of that call now goes through qnx_porter_str(), which prints "(null)" like glibc. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
