# can-utils v2025.01 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/linux-can/can-utils.git at `v2025.01` (`01083a64ebf2`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **failed** after 2 round(s) |
| Library's own tests | not run |
| Patches kept | 2 (2 by rule, 0 by model) |
| Time | 0.1 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-endian-compat.patch) | endian-compat | rule | kept | qnx-toolchain.cmake | <endian.h> does not exist on QNX 8.0. QNX provides BSD byte-order conversion macros in <net/netbyte.h> (__NET_BE*/__NET_LE*); a generated compatibility <endian.h> header in the include search path maps glibc names and byte-order constants to QNX's definitions. |
| [0002](patches/0002-guard-linux-header-isobusfs-cmn-h.patch) | guard-linux-header | rule | kept | isobusfs/isobusfs_cmn.h | <endian.h> does not exist on QNX 8.0 and isobusfs/isobusfs_cmn.h uses nothing from it, so the include is kept for Linux and skipped on QNX. |

Note: Linux SocketCAN tools: expected not to port

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `/home/chirag/qnx-porter/ports/can-utils/work/src/./include/linux/can/netlink.h:22:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports/can-utils/work/src/./include/linux/can.h:49:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports/can-utils/work/src/./include/linux/errqueue.h:5:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports/can-utils/work/src/./include/linux/can/gw.h:48:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports/can-utils/work/src/slcan_attach.c:47:10: fatal error: linux/sockios.h: No such file or directory`  
  QNX note: <linux/sockios.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports/can-utils/work/src/slcand.c:27:10: fatal error: linux/serial.h: No such file or directory`  
  QNX note: <linux/serial.h> is a Linux kernel header and does not exist on QNX
