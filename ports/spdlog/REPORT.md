# spdlog v1.17.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/gabime/spdlog.git at `v1.17.0` (`79524ddd08a4`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 1/1 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 4.0 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-qnx-source.patch) | qnx-source | rule | kept | qnx-toolchain.cmake | C++ sees only `struct stat`, not the POSIX function `stat()`: in strict -std=c++NN mode QNX's headers hide POSIX extensions (here sys/stat.h declares stat() only under __EXT_POSIX1_198808). -D_QNX_SOURCE exposes them, as _GNU_SOURCE does on glibc. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
