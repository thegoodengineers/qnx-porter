# libevent release-2.1.12-stable on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/libevent/libevent.git at `release-2.1.12-stable` (`5df3037d1055`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 3 round(s) |
| Library's own tests | 20/24 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 2 (2 by rule, 0 by model) |
| Time | 11.9 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-sa-restart.patch) | sa-restart | rule | kept | qnx-toolchain.cmake | QNX 8.0's <signal.h> lists SA_RESTART as not supported yet. Defining it as 0 lets the code build; system calls interrupted by a signal then return EINTR instead of restarting, which the library's tests on QNX show it handles or not. |
| [0002](patches/0002-link-libsocket.patch) | link-libsocket | rule | kept | qnx-toolchain.cmake | `setsockopt` is in QNX's libsocket, not in libc as on Linux: link with -lsocket. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
