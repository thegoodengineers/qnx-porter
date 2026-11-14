"""Porting advisor: when a build stops on a Linux kernel interface that QNX 8.0 does not have, say which interfaces
the library uses and what QNX offers instead, rather than reporting a bare failure.

The trigger is the build itself: the advisor speaks only when the build stopped on a missing Linux kernel header
(<linux/...>, <sys/epoll.h>, ...). It then scans the library's C/C++ sources for the Linux-only interfaces in
LINUX_ONLY. A library that merely has an epoll path behind #ifdef __linux__ builds, and is never advised.
QNX equivalents are from the QNX SDP 8.0 documentation (links below); the headers they name were checked in
SDP 8.0 build 141 (<sys/can_dcmd.h>, <hw/libcan.h>, <hw/i2c.h>, <hw/io-spi.h>, <net/route.h>; ionotify() in libc).
"""
import re
from pathlib import Path

DOCS = "https://www.qnx.com/developers/docs/8.0/"
NEEDS = "needs-qnx-equivalent"  # build_result for a library stopped by a Linux-only kernel interface
SOURCES = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh"}

# (interface, pattern in the source, QNX equivalent, QNX docs)
LINUX_ONLY = [
    ("SocketCAN (AF_CAN, <linux/can.h>)", r"#\s*include\s*[<\"]linux/can(?:/[\w.]+)?\.h|\b[AP]F_CAN\b",
     "a QNX CAN driver (dev-can-<board>) used through devctl() CAN_DEVCTL_* commands (<sys/can_dcmd.h>) "
     "and the canctl utility", DOCS + "com.qnx.doc.neutrino.devctl/topic/can.html"),
    ("GPIO character device (<linux/gpio.h>, /dev/gpiochip)", r"#\s*include\s*[<\"]linux/gpio\.h|/dev/gpiochip",
     "the board's GPIO resource manager from its BSP, or the QNX GPIO framework (added in SDP 8.0.5; not in "
     "the SDP 8.0 build these ports used)", DOCS + "com.qnx.doc.gpio_framework/topic/overview.html"),
    ("netlink (AF_NETLINK, <linux/netlink.h>)", r"#\s*include\s*[<\"]linux/(?:rt)?netlink\.h|\bAF_NETLINK\b",
     "routing sockets (PF_ROUTE, <net/route.h>) and sysctl on the io-sock network stack",
     DOCS + "com.qnx.doc.neutrino.utilities/topic/i/io-sock.html"),
    ("I2C character device (<linux/i2c-dev.h>)", r"#\s*include\s*[<\"]linux/i2c(?:-dev)?\.h",
     "the QNX I2C framework: an i2c-* resource manager driven with devctl() DCMD_I2C_* from <hw/i2c.h>",
     DOCS + "com.qnx.doc.neutrino.custom_bsp/topic/i2c/i2c_framework.html"),
    ("spidev (<linux/spi/spidev.h>)", r"#\s*include\s*[<\"]linux/spi/spidev\.h",
     "the QNX SPI framework (io-spi, <hw/io-spi.h>)", DOCS + "com.qnx.doc.neutrino.spi_framework/topic/about.html"),
    ("epoll (<sys/epoll.h>)", r"#\s*include\s*<sys/epoll\.h>",
     "poll() or select(), or ionotify() to have a resource manager deliver a pulse or signal",
     DOCS + "com.qnx.doc.neutrino.lib_ref/topic/i/ionotify.html"),
    ("signalfd (<sys/signalfd.h>)", r"#\s*include\s*<sys/signalfd\.h>",
     "sigwaitinfo() in a dedicated thread, or a SIGEV_PULSE event received with MsgReceive()",
     DOCS + "com.qnx.doc.neutrino.lib_ref/topic/s/sigwaitinfo.html"),
    ("eventfd (<sys/eventfd.h>)", r"#\s*include\s*<sys/eventfd\.h>",
     "a pipe(), or MsgSendPulse() to a channel", DOCS + "com.qnx.doc.neutrino.lib_ref/topic/m/msgsendpulse.html"),
    ("timerfd (<sys/timerfd.h>)", r"#\s*include\s*<sys/timerfd\.h>",
     "timer_create() with a SIGEV_PULSE event", DOCS + "com.qnx.doc.neutrino.lib_ref/topic/t/timer_create.html"),
]
KERNEL_HEADER = re.compile(r"fatal error: ((?:linux|asm)/[\w./-]+|sys/(?:epoll|signalfd|eventfd|timerfd)\.h): "
                           r"No such file")


def stopped_on(blocked: list[dict]) -> str | None:
    """The Linux kernel header the build stopped on, if it stopped on one."""
    return next((m[1] for b in blocked if (m := KERNEL_HEADER.search(b.get("error", "")))), None)


def scan(src: Path) -> list[dict]:
    """Each Linux-only interface the sources use: how many files, and the first place (path:line)."""
    found = {}
    aux = re.compile(r"(^|/)(examples?|tests?|bindings|contrib|docs?)/")  # cite the library's own code first
    for f in sorted(src.rglob("*"), key=lambda p: (bool(aux.search(p.relative_to(src).as_posix())), p)):
        if f.suffix not in SOURCES or not f.is_file() or ".git" in f.parts:
            continue
        lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        for name, pat, qnx, docs in LINUX_ONLY:
            hit = next((i for i, ln in enumerate(lines, 1) if re.search(pat, ln)), None)
            if hit:
                e = found.setdefault(name, {"interface": name, "files": 0, "first": f"{f.relative_to(src).as_posix()}:{hit}",
                                            "qnx": qnx, "docs": docs})
                e["files"] += 1
    return [found[n] for n, *_ in LINUX_ONLY if n in found]


def advise(blocked: list[dict], src: Path) -> dict | None:
    """{stopped_on, interfaces} when the build stopped on a Linux kernel header and the sources use a Linux-only
    interface; None otherwise (an ordinary build failure)."""
    header = stopped_on(blocked)
    uses = scan(src) if header else []
    return {"stopped_on": header, "interfaces": uses} if uses else None


def render(a: dict) -> str:
    rows = "\n".join(f"| {u['interface']} | {u['files']} (first: `{u['first']}`) | {u['qnx']} | [QNX docs]({u['docs']}) |"
                     for u in a["interfaces"])
    return (f"## Not portable as-is: needs a QNX equivalent\n"
            f"The build stopped on `<{a['stopped_on']}>`, a Linux kernel header. The sources use Linux-only "
            f"kernel interfaces that QNX 8.0 provides differently, so no header shim makes this library work; "
            f"the code that uses them needs a QNX back end.\n\n"
            f"| Linux interface | Files | QNX equivalent | |\n|---|---|---|---|\n{rows}\n")
