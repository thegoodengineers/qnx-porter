# tinyxml2 11.0.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/leethomason/tinyxml2.git at `11.0.0` (`9148bdf719e9`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 1 round(s) |
| Library's own tests | 1/1 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 0.8 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-printf-null-xmltest-cpp.patch) | printf-null | rule | kept | xmltest.cpp | Crash on QNX: printf() at xmltest.cpp:54 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C leaves it undefined. Each %s argument of that call now goes through qnx_porter_str(), which prints "(null)" like glibc. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
