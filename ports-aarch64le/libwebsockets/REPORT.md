# libwebsockets v4.3.3 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/warmcat/libwebsockets.git at `v4.3.3` (`4415e84c0958`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **failed** after 2 round(s) |
| Library's own tests | not run |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 0.8 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-no-werror.patch) | no-werror | rule | kept | qnx-toolchain.cmake | A warning that has no -W switch of its own (here: "BYTE_ORDER" redefined [-Werror]) is made an error by the project's -Werror. The only way to keep it a warning is -Wno-error; the warning is still printed in the build log. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `/home/chirag/qnx-porter/ports-aarch64le/libwebsockets/work/src/lib/plat/unix/./private-lib-plat-unix.h:141:24: error: 'TCPCTL_KEEPCNT' undeclared (first use in this function); did you mean 'TCPCTL_KEE`
