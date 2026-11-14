"""Record the demo: run every command for real and save its output with timestamps.

Writes video/out/demo.cast (asciicast v2, playable with `asciinema play`) plus scene markers.
Nothing on screen is typed by hand: each command below runs on the build host against the QNX 8.0
QEMU target, and render.py only replays what this script captured.

Usage (from the repo root, SDP sourced, target started with scripts/qemu_target.sh start):
    python3 video/record.py            # record
    python3 video/record.py --check    # only check the screenshots and the render tools (make.sh runs this first)
"""
import importlib.util
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEO = ROOT / "video"
OUT = VIDEO / "out"
DEMO = Path("/tmp/qnx-porter-demo")  # fresh port folders for the recording
TARGET = os.environ.get("QNX_TARGET_SSH", "root@172.31.1.11")  # same as scripts/qemu_target.sh
SITE_SHOTS = ["overview", "results", "weekly"]  # video/shots/site-<name>.png, taken by hand


def scenes(root: Path = ROOT) -> list:
    """The shot list of docs/VIDEO_SCRIPT.md, as (shot, seconds, kind, body).

    kind is "slide" (body: a slide in render.py), "image" (body: a PNG under video/), or else the caption shown
    above the terminal (body: the commands, run for real). seconds is the scene's length in the video; render.py
    fits each scene to it. The narration is per shot (render.py NARRATION). The Rust crate and model-step shots
    go in only when their result CSV is committed.
    """
    crates = (root / "results" / "crates.csv").exists()
    model = (root / "results" / "model_eval.csv").exists()
    nng = root / "ports" / "nng" / "REPORT.md"
    hang = nng.exists() and "## Hang on QNX" in nng.read_text(encoding="utf-8")
    return [
        ("title", 7, "slide", "title"),
        ("problem", 9, "slide", "problem"),
        ("why-c", 9, "slide", "why-c"),
        ("target", 10, "A real QNX 8.0 target (QEMU image from mkqnximage) and the SDP 8.0 toolchain",
         ["scripts/qemu_target.sh status", "qnx-porter doctor | grep -v '^[[:space:]]' | cut -c1-120"]),
        # The pins of campaign.yaml (mbedtls v4.2.0 with programs on), the run in results/runs/campaign-8.log.
        ("mbedtls", 22, "mbedtls, straight from upstream: the build fails on QNX, a rule fixes it, its own tests run on QNX",
         [f"qnx-porter port https://github.com/Mbed-TLS/mbedtls.git --tag v4.2.0 "
          f"--target {TARGET} --no-model --out {DEMO}",
          f"head -4 {DEMO}/mbedtls/patches/*-link-libsocket.patch | cut -c1-138"]),
        ("json-c", 17, "json-c: built with qcc, its own tests run on the QNX target; a crash is traced from the core dump",
         [f"qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.19-20260627 "
          f"--target {TARGET} --no-model --out {DEMO}",
          f"grep -E '^(#[0-4] |Program)' {DEMO}/json-c/logs/crashes.log | awk '!seen[$1]++' | cut -c1-138"]),
        # The hang snapshot of a real nng run (qnx_porter/hang.py), and the fix sent upstream (upstream/outbox/).
        *([("hang", 11, "A hung test on QNX: pidin and a kernel trace, taken before it is killed",
            ["awk '/^## Hang on QNX/{f=1} f' ports/nng/REPORT.md | grep -v '^```' | head -12 | cut -c1-138",
             "grep -o 'https://github.com/nanomsg/nng/pull/[0-9]*' upstream/outbox/README.md | head -1"])] if hang else []),
        ("campaign", 9, "The campaign: every library, every number written by scripts/ports_csv.py",
         ["python3 scripts/ports_csv.py | grep -v '^->'",
          "cut -d, -f1,4,5,6,7,8,9,10 results/ports.csv | column -s, -t"]),
        ("campaign", 9, "slide", "results"),
        ("failures", 9, "slide", "failures"),
        ("comparison", 11, "Checked against QNX's own hand-made ports",
         ["sed -n '/^## Summary/,/^## Library/p' docs/related/qnx-ports-comparison.md | head -12 | cut -c1-138",
          "ls recipes/build-files/ports | wc -l"]),
        *([("crates", 6, "Rust crates on QNX 8.0: each crate's own tests, run on the target",
            ["cut -d, -f1,2,3,5,6,7 results/crates.csv | column -s, -t"])] if crates else []),
        *([("model", 7, "The model step, where no rule applies: kept only if the rebuild proves it",
            ["cut -d, -f1-7 results/model_eval.csv | column -s, -t",
             "head -3 ports-model/libuv/patches/*-model-fix-*.patch | cut -c1-138"])] if model else []),
        ("rt", 7, "Real-time check: latency of one call on QNX 8.0 in QEMU (compares libraries; not a hardware figure)",
         ["sed -n '/^## Latency/,/^## What/p' docs/RT_RESULTS.md | grep -E '^(## |[|] )' | cut -c1-138"]),
        *[("site", 2, "image", f"shots/site-{n}.png") for n in SITE_SHOTS],
        ("site", 3, "Install", ["python3 -m pip index versions qnx-porter 2>/dev/null"]),
        ("paper", 5, "image", "shots/site-paper.png"),
        ("close", 10, "slide", "close"),
    ]


def check() -> None:
    """Fail before a long recording, not after it: the screenshots and what render.py needs."""
    missing = [b for _, _, kind, b in scenes() if kind == "image" and not (VIDEO / b).exists()]
    if missing:
        sys.exit("missing screenshots: " + ", ".join(f"video/{m}" for m in missing)
                 + "\ncapture them as described in video/README.md (Screenshots), then run video/make.sh again")
    if not shutil.which("ffmpeg") or importlib.util.find_spec("PIL") is None:
        sys.exit("render.py needs ffmpeg and Pillow: sudo apt install ffmpeg python3-pil")


def run(cmd: str, events: list, t0: float) -> int:
    """Run cmd in a pseudo-terminal (so tools line-buffer like in a real terminal); record its output."""
    import pty
    import select
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
    check()
    if "--check" in sys.argv:
        print("video: screenshots, ffmpeg and Pillow present", file=sys.stderr)
        return 0
    if not shutil.which("qnx-porter") or not os.environ.get("QNX_HOST"):
        sys.exit("source ~/qnx800/qnxsdp-env.sh and install qnx-porter first (see SETUP.md)")
    shutil.rmtree(DEMO, ignore_errors=True)
    OUT.mkdir(parents=True, exist_ok=True)
    os.chdir(ROOT)
    t0 = time.monotonic()
    events, markers = [], []
    for shot, seconds, kind, body in scenes():
        mark = {"t": round(time.monotonic() - t0, 3), "shot": shot, "seconds": seconds}
        if kind in ("slide", "image"):
            markers.append({**mark, kind: body})
            continue
        markers.append({**mark, "caption": kind})
        for cmd in body:
            markers.append({"t": round(time.monotonic() - t0, 3), "command": cmd})
            rc = run(cmd, events, t0)
            markers.append({"t": round(time.monotonic() - t0, 3), "done": cmd, "exit": rc})
            print(f"[{rc}] {cmd[:90]}", file=sys.stderr)
    header = {"version": 2, "width": 140, "height": 28, "timestamp": int(time.time()),
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
