# cJSON v1.7.19 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/DaveGamble/cJSON.git at `v1.7.19` (`c859b25da029`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 1 round(s) |
| Library's own tests | 19/19 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 3.6 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-main-stack.patch) | main-stack | rule | kept | qnx-toolchain.cmake | Crash on QNX: cJSON_Duplicate_rec() calls itself until the stack runs out (the backtrace is cJSON_Duplicate_rec <- cJSON_Duplicate_rec <- ...). A QNX main thread gets about 464 KiB of stack unless the program is linked with qcc -N; a Linux one usually has 8 MiB. Every program is now linked with -N8M, which writes an 8 MiB stack size into its QNX ELF note. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
