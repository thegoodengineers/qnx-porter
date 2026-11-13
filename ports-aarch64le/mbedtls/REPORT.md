# mbedtls v3.6.2 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/Mbed-TLS/mbedtls.git at `v3.6.2` (`107ea89daaef`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 130/130 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 19.0 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-link-libsocket.patch) | link-libsocket | rule | kept | qnx-toolchain.cmake | `__inet_pton` is in QNX's libsocket, not in libc as on Linux: link with -lsocket. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
