from qnx_porter import advisor

# can-utils v2025.01 on x86_64: the build stopped here (ports/can-utils/report.json, blocked_on)
CAN_STOP = [{"kind": "missing_header", "error": "/w/src/./include/linux/can/netlink.h:22:10: fatal error: "
             "linux/types.h: No such file or directory", "hint": ""}]
# libwebsockets 5.1.0: an ordinary failure, not a Linux kernel interface
LWS_STOP = [{"kind": "error", "error": "/q/usr/include/ifaddrs.h:32:8: error: redefinition of 'struct ifaddrs'",
             "hint": ""}]


def tree(tmp_path, files):
    for rel, text in files.items():
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / rel).write_text(text)
    return tmp_path


def test_a_build_stopped_on_socketcan_is_advised_with_the_qnx_equivalent(tmp_path):
    src = tree(tmp_path, {"candump.c": "#include <stdio.h>\n#include <linux/can.h>\nint s = socket(PF_CAN, 3, 1);\n",
                          "lib.h": "#include <linux/can/raw.h>\n", "util.c": "int x;\n"})
    a = advisor.advise(CAN_STOP, src)
    assert a["stopped_on"] == "linux/types.h"
    [can] = a["interfaces"]
    assert can["interface"].startswith("SocketCAN") and can["files"] == 2 and can["first"] == "candump.c:2"
    assert "dev-can-" in can["qnx"] and can["docs"].startswith("https://www.qnx.com/developers/docs/8.0/")
    assert "needs a QNX equivalent" in advisor.render(a)


def test_gpio_and_epoll_are_each_named(tmp_path):
    src = tree(tmp_path, {"core.c": '#include <linux/gpio.h>\nconst char *p = "/dev/gpiochip0";\n',
                          "loop.c": "#include <sys/epoll.h>\n"})
    stop = [{"error": "core.c:1:10: fatal error: linux/gpio.h: No such file or directory"}]
    names = [u["interface"] for u in advisor.advise(stop, src)["interfaces"]]
    assert names[0].startswith("GPIO") and names[1].startswith("epoll") and len(names) == 2


def test_an_ordinary_failure_is_not_advised(tmp_path):
    src = tree(tmp_path, {"net.c": "#include <sys/epoll.h>\n"})  # an epoll path behind #ifdef, say
    assert advisor.advise(LWS_STOP, src) is None
    assert advisor.advise(CAN_STOP, tree(tmp_path / "plain", {"a.c": "int main(void) { return 0; }\n"})) is None
