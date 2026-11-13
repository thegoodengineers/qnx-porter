# libuv v1.49.2 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/libuv/libuv.git at `v1.49.2` (`e1095c7a4373`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **failed** after 1 round(s) |
| Library's own tests | not run |
| Patches kept | 0 (0 by rule, 0 by model) |
| Time | 0.3 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| - | - | - | - | - | no changes needed |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `/home/chirag/qnx-porter/ports/libuv/work/src/src/unix/qnx.c:117:19: error: 'struct qtime_entry' has no member named 'nsec'`
- `/home/chirag/qnx-porter/ports/libuv/work/src/src/unix/qnx.c:124:57: error: 'struct syspage_entry' has no member named 'new_cpuinfo'; did you mean 'cpuinfo'?`
