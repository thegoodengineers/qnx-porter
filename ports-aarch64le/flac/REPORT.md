# flac 1.5.0 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/xiph/flac.git at `1.5.0` (`1507800de4b7`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 6/10 passed on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 22.9 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-wcswidth-compat.patch) | wcswidth-compat | rule | kept | qnx-toolchain.cmake | QNX 8.0's libc has wcwidth() but no wcswidth(). POSIX defines wcswidth(s, n) as the sum of wcwidth() over the first n characters of s, or -1 if any is not printable; a small header (-included in every compile) implements exactly that on top of QNX's wcwidth(). |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
