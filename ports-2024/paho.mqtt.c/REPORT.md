# paho.mqtt.c v1.3.14 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/eclipse/paho.mqtt.c.git at `v1.3.14` (`2150ba29d9df`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 3 round(s) |
| Library's own tests | not run |
| Patches kept | 3 (3 by rule, 0 by model) |
| Time | 0.4 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-bool-typedef-mqttpacket-h.patch) | bool-typedef | rule | kept | src/MQTTPacket.h | src/MQTTPacket.h defines its own `bool`, but on QNX 8.0 <sys/socket.h> already includes <stdbool.h> (via io-sock/types_fbsd.h), so `bool` is taken. The typedef is skipped when stdbool's bool is visible. Note: bool is then _Bool, not unsigned int, in those files. |
| [0002](patches/0002-link-libsocket.patch) | link-libsocket | rule | kept | qnx-toolchain.cmake | `recv` is in QNX's libsocket, not in libc as on Linux: link with -lsocket. |
| [0003](patches/0003-endian-netbyte.patch) | endian-netbyte | rule | kept | qnx-toolchain.cmake | `be32toh` comes from glibc's <endian.h>, which QNX 8.0 does not have. QNX has the same names as BSD macros in <net/netbyte.h>; a small header (-included in every compile) includes it and defines any name strict POSIX flags hid, from QNX's __NET_BE*/__NET_LE* helpers. |

Note: build only: the test suite needs an MQTT broker on the target

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
