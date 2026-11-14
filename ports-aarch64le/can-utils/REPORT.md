# can-utils v2025.01 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/linux-can/can-utils.git at `v2025.01` (`01083a64ebf2`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **needs-qnx-equivalent** after 2 round(s) |
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
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/can/netlink.h:22:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/can.h:49:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/errqueue.h:5:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/./include/linux/can/gw.h:48:10: fatal error: linux/types.h: No such file or directory`  
  QNX note: <linux/types.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/slcand.c:27:10: fatal error: linux/serial.h: No such file or directory`  
  QNX note: <linux/serial.h> is a Linux kernel header and does not exist on QNX
- `/home/chirag/qnx-porter/ports-aarch64le/can-utils/work/src/slcan_attach.c:47:10: fatal error: linux/sockios.h: No such file or directory`  
  QNX note: <linux/sockios.h> is a Linux kernel header and does not exist on QNX

## Not portable as-is: needs a QNX equivalent
The build stopped on `<linux/types.h>`, a Linux kernel header. The sources use Linux-only kernel interfaces that QNX 8.0 provides differently, so no header shim makes this library work; the code that uses them needs a QNX back end.

| Linux interface | Files | QNX equivalent | |
|---|---|---|---|
| SocketCAN (AF_CAN, <linux/can.h>) | 41 (first: `asc2log.c:55`) | a QNX CAN driver (dev-can-<board>) used through devctl() CAN_DEVCTL_* commands (<sys/can_dcmd.h>) and the canctl utility | [QNX docs](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.devctl/topic/can.html) |
| netlink (AF_NETLINK, <linux/netlink.h>) | 4 (first: `cangw.c:48`) | routing sockets (PF_ROUTE, <net/route.h>) and sysctl on the io-sock network stack | [QNX docs](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/i/io-sock.html) |
| epoll (<sys/epoll.h>) | 5 (first: `candump.c:57`) | poll() or select(), or ionotify() to have a resource manager deliver a pulse or signal | [QNX docs](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/i/ionotify.html) |
