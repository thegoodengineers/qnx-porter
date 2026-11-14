# yaml-cpp 0.8.0 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/jbeder/yaml-cpp.git at `0.8.0` (`f7320141120f`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 3 round(s) |
| Library's own tests | 0/1 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 2 (2 by rule, 0 by model) |
| Time | 20.7 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-signed-char.patch) | signed-char | rule | kept | qnx-toolchain.cmake | Plain char is unsigned on aarch64 (the Arm ABI) and signed on x86_64; the code puts a negative constant in a char, which is fine on x86_64 and a narrowing error on aarch64. -fsigned-char keeps the x86_64 meaning the code was written for, without editing it. |
| [0002](patches/0002-link-libregex.patch) | link-libregex | rule | kept | qnx-toolchain.cmake | `regfree` (POSIX <regex.h>) is in QNX's libregex, not in libc as on Linux: link with -lregex. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
