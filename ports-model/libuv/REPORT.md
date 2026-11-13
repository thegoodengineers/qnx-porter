# libuv v1.49.2 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/libuv/libuv.git at `v1.49.2` (`e1095c7a4373`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 0/2 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (0 by rule, 1 by model) |
| Time | 6.3 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-model-fix-qnx-c.patch) | model-fix | model | kept | src/unix/qnx.c | QNX 8.0's struct qtime_entry has no nsec field, so uv_uptime now uses clock_gettime(CLOCK_MONOTONIC); syspage_entry in QNX 8.0 has no new_cpuinfo member, so the cpuinfo member the compiler suggests is used instead, matching the existing _SYSPAGE_ELEMENT_SIZE(_syspage_ptr, cpuinfo) call. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
