# libgpiod v2.3.2 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Upstream | https://github.com/brgl/libgpiod.git at `v2.3.2` (`3435867dd146`) |
| Build system | meson |
| Toolchain | QNX SDP 8.0, `qnx-cross.ini` in this folder |
| Build | **needs-qnx-equivalent** after 1 round(s) |
| Library's own tests | not run |
| Patches kept | 0 (0 by rule, 0 by model) |
| Time | 0.5 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| - | - | - | - | - | no changes needed |

Note: Linux GPIO character-device API: expected not to port

All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- `../src/lib/uapi/gpio.h:14:10: fatal error: linux/const.h: No such file or directory`  
  QNX note: <linux/const.h> is a Linux kernel header and does not exist on QNX

## Not portable as-is: needs a QNX equivalent
The build stopped on `<linux/const.h>`, a Linux kernel header. The sources use Linux-only kernel interfaces that QNX 8.0 provides differently, so no header shim makes this library work; the code that uses them needs a QNX back end.

| Linux interface | Files | QNX equivalent | |
|---|---|---|---|
| GPIO character device (<linux/gpio.h>, /dev/gpiochip) | 38 (first: `tools/gpiodetect.c:20`) | the board's GPIO resource manager from its BSP, or the QNX GPIO framework (added in SDP 8.0.5; not in the SDP 8.0 build these ports used) | [QNX docs](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.gpio_framework/topic/overview.html) |
