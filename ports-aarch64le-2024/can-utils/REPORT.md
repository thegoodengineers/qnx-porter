# can-utils v2023.03 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/linux-can/can-utils.git at `v2023.03` (`cfe41963f342`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **failed** after 1 round(s) |
| Library's own tests | not run |
| Patches kept | 0 (0 by rule, 0 by model) |
| Time | 0.0 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| - | - | - | - | - | no changes needed |

Note: Linux SocketCAN tools: expected not to port

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/mcp251xfd/mcp251xfd-dev-coredump.c:9:10: fatal error: endian.h: No such file or directory`  
  QNX note: QNX 8.0 has no <endian.h>: use <gulliver.h> (ENDIAN_LE32 etc.) or GCC's __BYTE_ORDER__
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/can/netlink.h:22:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/can.h:49:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/can/gw.h:48:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/slcan_attach.c:47:10: fatal error: linux/sockios.h: No such file or directory`  
  QNX note: <linux/sockios.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/slcand.c:27:10: fatal error: linux/serial.h: No such file or directory`  
  QNX note: <linux/serial.h> is a Linux kernel header and does not exist on QNX
