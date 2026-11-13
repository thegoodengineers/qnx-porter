# cmocka cmocka-1.1.7 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://gitlab.com/cmocka/cmocka.git at `cmocka-1.1.7` (`a01cc69ee953`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 46/46 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 2.6 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-wordsize-64.patch) | wordsize-64 | rule | kept | qnx-toolchain.cmake | The library guesses the word size from glibc's __WORDSIZE, else from __x86_64__, else assumes 32 bits (cmocka.h), and so redefines (u)intptr_t as a 32-bit type on aarch64. QNX 8.0's x86_64 and aarch64le targets are both LP64 and QNX's headers never define __WORDSIZE, so define it as 64. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
