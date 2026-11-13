# libwebsockets v5.1.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/warmcat/libwebsockets.git at `v5.1.0` (`5f39aa483715`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **failed** after 2 round(s) |
| Library's own tests | not run |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 2.6 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-sa-restart.patch) | sa-restart | rule | kept | qnx-toolchain.cmake | QNX 8.0's <signal.h> lists SA_RESTART as not supported yet. Defining it as 0 lets the code build; system calls interrupted by a signal then return EINTR instead of restarting, which the library's tests on QNX show it handles or not. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `/home/chirag/qnx800/target/qnx/usr/include/ifaddrs.h:32:8: error: redefinition of 'struct ifaddrs'`
- `/home/chirag/qnx800/target/qnx/usr/include/ifaddrs.h:64:12: error: conflicting types for 'getifaddrs'; have 'int(struct ifaddrs **)'`
- `/home/chirag/qnx800/target/qnx/usr/include/ifaddrs.h:65:13: error: conflicting types for 'freeifaddrs'; have 'void(struct ifaddrs *)'`
