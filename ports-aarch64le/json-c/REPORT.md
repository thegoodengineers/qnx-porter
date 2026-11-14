# json-c json-c-0.19-20260627 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/json-c/json-c.git at `json-c-0.19-20260627` (`aa716cd8d663`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 1 round(s) |
| Library's own tests | 28/28 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 5.1 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-printf-null-test-json-patch-c.patch) | printf-null | rule | kept | tests/test_json_patch.c | Crash on QNX: printf() at tests/test_json_patch.c:31 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C leaves it undefined. Each %s argument of that call now goes through qnx_porter_str(), which prints "(null)" like glibc. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
