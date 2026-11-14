# mosquitto v2.1.2 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/eclipse/mosquitto.git at `v2.1.2` (`99fa50f30e32`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 0/0 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 3 (3 by rule, 0 by model) |
| Time | 10.2 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-add-include-db-dump-c.patch) | add-include | rule | kept | apps/db_dump/db_dump.c | `ntohl` is a macro in QNX's <arpa/inet.h>, and neither libc nor libsocket exports it as a function. apps/db_dump/db_dump.c did not include the header, so the compiler took it for an undeclared function, and the link failed. |
| [0002](patches/0002-link-libm.patch) | link-libm | rule | kept | qnx-toolchain.cmake | `__isinf` is in QNX's libm, not in libc: QNX's <math.h> implements isinf/isfinite/isnan as calls to __isinf etc. in libm, where glibc needs no library. Link with -lm. |
| [0003](patches/0003-link-libsocket.patch) | link-libsocket | rule | kept | qnx-toolchain.cmake | `__inet_ntop` is in QNX's libsocket, not in libc as on Linux: link with -lsocket. |

Note: 2.1 needs cJSON (our QNX port of it) and, on QNX, TLS: without it 2.1 has random bytes only from Linux getrandom(); OpenSSL from the SDP. Its tests need CUnit and a Python broker harness

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
