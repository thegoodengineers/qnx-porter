# fmt 11.0.2 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/fmtlib/fmt.git at `11.0.2` (`0c9fce2ffefe`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 17/20 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 6.9 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-link-libregex.patch) | link-libregex | rule | kept | qnx-toolchain.cmake | `regfree` (POSIX <regex.h>) is in QNX's libregex, not in libc as on Linux: link with -lregex. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
