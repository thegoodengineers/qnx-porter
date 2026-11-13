# libwebsockets v4.3.3 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/warmcat/libwebsockets.git at `v4.3.3` (`4415e84c0958`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 3 round(s) |
| Library's own tests | 0/0 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 2 (1 by rule, 1 by model) |
| Time | 8.7 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-no-werror.patch) | no-werror | rule | kept | qnx-toolchain.cmake | A warning that has no -W switch of its own (here: "BYTE_ORDER" redefined [-Werror]) is made an error by the project's -Werror. The only way to keep it a warning is -Wno-error; the warning is still printed in the build log. |
| [0002](patches/0002-model-fix-private-lib-plat-unix-h.patch) | model-fix | model | kept | lib/plat/unix/private-lib-plat-unix.h | QNX 8.0's io-sock <netinet/tcp.h>, already included at line 32, defines TCP_KEEPIDLE, TCP_KEEPINTVL and TCP_KEEPCNT as real socket options, so the old io-pkt TCPCTL_* fallback (which has no TCPCTL_KEEPCNT) is now applied only when those macros are missing. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
