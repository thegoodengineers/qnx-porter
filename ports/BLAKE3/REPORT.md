# BLAKE3 1.8.7 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/BLAKE3-team/BLAKE3.git at `1.8.7` (`f3149ec5bb54`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 1 round(s) |
| Library's own tests | 0/0 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 0 (0 by rule, 0 by model) |
| Time | 0.2 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| - | - | - | - | - | no changes needed |

Note: portable C: its CMake has SIMD flags only for compilers it knows, not qcc

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
