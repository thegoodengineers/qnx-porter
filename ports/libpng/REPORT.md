# libpng v1.6.59 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/pnggroup/libpng.git at `v1.6.59` (`cd952f49f95b`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 0/0 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 0.6 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-qcc-sysroot.patch) | qcc-sysroot | rule | kept | qnx-toolchain.cmake | The project's own build script passes --sysroot to the compiler, which qcc does not accept. qcc already finds the SDP sysroot through QNX_TARGET, so the toolchain stops setting CMAKE_SYSROOT (libraries are still found through CMAKE_FIND_ROOT_PATH). |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
