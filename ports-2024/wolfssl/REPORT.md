# wolfssl v5.7.4-stable on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/wolfSSL/wolfssl.git at `v5.7.4-stable` (`bdd62314f00f`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 3 round(s) |
| Library's own tests | 1/1 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 2 (2 by rule, 0 by model) |
| Time | 1.9 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-no-werror.patch) | no-werror | rule | kept | qnx-toolchain.cmake | Warning -Wstringop-overflow= is promoted to an error by the project's -Werror. Keep it a warning (still printed in the build log) instead of editing the library's code; QNX's headers and qcc raise warnings a glibc build does not. |
| [0002](patches/0002-link-libsocket.patch) | link-libsocket | rule | kept | qnx-toolchain.cmake | `recv` is in QNX's libsocket, not in libc as on Linux: link with -lsocket. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
