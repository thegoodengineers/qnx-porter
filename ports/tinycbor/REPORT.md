# tinycbor v7.1 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/intel/tinycbor.git at `v7.1` (`da6421f2b5b9`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 1/1 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 2 (2 by rule, 0 by model) |
| Time | 0.3 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-qnx-source.patch) | qnx-source | rule | kept | qnx-toolchain.cmake | `strdup` is in <string.h>, which src/cbortojson.c already includes, so a strict feature-test macro hid it. -D_QNX_SOURCE exposes POSIX and QNX extensions in QNX's headers, as _GNU_SOURCE does on glibc. |
| [0002](patches/0002-no-werror.patch) | no-werror | rule | kept | qnx-toolchain.cmake | Warning -Wint-conversion is promoted to an error by the project's -Werror. Keep it a warning (still printed in the build log) instead of editing the library's code; QNX's headers and qcc raise warnings a glibc build does not. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
