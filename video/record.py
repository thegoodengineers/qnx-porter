"""Record the demo: run every command for real and save its output with timestamps.

Writes video/out/demo.cast (asciicast v2, playable with `asciinema play`) plus scene markers.
Nothing on screen is typed by hand: each command below runs on the build host against the QNX 8.0
QEMU target, and render.py only replays what this script captured.

Usage (from the repo root, SDP sourced, target started with scripts/qemu_target.sh start):
    python3 video/record.py
"""
import json
import os
import pty
import select
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video" / "out"
DEMO = Path("/tmp/qnx-porter-demo")  # fresh port folders for the recording
TARGET = os.environ.get("QNX_TARGET_SSH", "root@172.31.1.11")  # same as scripts/qemu_target.sh

# (caption, [commands]) or ("slide", name). Captions are shown above the terminal.
SCENES = [
    ("slide", "title"),
    ("slide", "problem"),
    ("1/4  A real QNX 8.0 target (QEMU image from mkqnximage) and the SDP 8.0 toolchain",
     ["scripts/qemu_target.sh status", "qnx-porter doctor | grep -v '^[[:space:]]' | cut -c1-120"]),
    ("2/4  paho.mqtt.c (MQTT client) does not build for QNX: four rule-based fixes, rebuilt each round",
     [f"qnx-porter port https://github.com/eclipse/paho.mqtt.c.git --tag v1.3.14 --no-model --out {DEMO}",
      f"head -24 {DEMO}/paho.mqtt.c/patches/0002-*.patch | cut -c1-138"]),
    ("3/4  json-c: built with qcc, its own 25 tests run ON the QNX target; a crash is traced from the core dump",
     [f"qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 "
      f"--target {TARGET} --no-model --out {DEMO}",
      f"grep -E '^(#[0-4] |Program)' {DEMO}/json-c/logs/crashes.log | awk '!seen[$1]++' | cut -c1-138",
      f"tail -4 {DEMO}/json-c/logs/tests.log"]),
    ("4/4  The campaign: 10 libraries not on oss.qnx.com, every number written by the scripts",
     ["python3 scripts/ports_csv.py | sed 's| -> .*||'",
      "cut -d, -f1,5,6,7,8 results/ports.csv | column -s, -t"]),
    ("slide", "results"),
    ("slide", "failures"),
    ("slide", "close"),
]


def run(cmd: str, events: list, t0: float) -> int:
    """Run cmd in a pseudo-terminal (so tools line-buffer like in a real terminal); record its output."""
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp("bash", ["bash", "-c", cmd])
    while True:
        r, _, _ = select.select([fd], [], [], 0.5)
        if r:
            try:
                data = os.read(fd, 4096)
            except OSError:
                data = b""
            if not data:
                break
            events.append([round(time.monotonic() - t0, 3), "o", data.decode("utf-8", "replace")])
    _, status = os.waitpid(pid, 0)
    return os.waitstatus_to_exitcode(status)


def main() -> int:
    if not shutil.which("qnx-porter") or not os.environ.get("QNX_HOST"):
        sys.exit("source ~/qnx800/qnxsdp-env.sh and install qnx-porter first (see SETUP.md)")
    shutil.rmtree(DEMO, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    t0 = time.monotonic()
    events, markers = [], []
    for caption, body in SCENES:
        if caption == "slide":
            markers.append({"t": round(time.monotonic() - t0, 3), "slide": body})
            continue
        markers.append({"t": round(time.monotonic() - t0, 3), "caption": caption})
        for cmd in body:
            markers.append({"t": round(time.monotonic() - t0, 3), "command": cmd})
            rc = run(cmd, events, t0)
            markers.append({"t": round(time.monotonic() - t0, 3), "done": cmd, "exit": rc})
            print(f"[{rc}] {cmd[:90]}", file=sys.stderr)
    header = {"version": 2, "width": 140, "height": 36, "timestamp": int(time.time()),
              "title": "qnx-porter demo", "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"}}
    with (OUT / "demo.cast").open("w", encoding="utf-8") as f:
        f.write(json.dumps(header) + "\n")
        for e in events:
            f.write(json.dumps(e) + "\n")
    (OUT / "markers.json").write_text(json.dumps(markers, indent=1), encoding="utf-8")
    print(f"recorded {len(events)} output chunks in {time.monotonic() - t0:.0f} s -> {OUT}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
