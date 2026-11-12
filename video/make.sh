#!/usr/bin/env bash
# Re-record the demo from scratch: real runs on the QNX 8.0 QEMU target, then render to MP4.
# Needs: SDP 8.0 sourced, qnx-porter installed, the target running (scripts/qemu_target.sh start),
# ffmpeg and Pillow (sudo apt install ffmpeg python3-pil).
# Output: video/out/demo.cast (the raw recording, `asciinema play`-able) and video/out/qnx-porter-demo.mp4.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -n "${QNX_HOST:-}" ] || source "${QNX_SDP:-$HOME/qnx800}/qnxsdp-env.sh" >/dev/null
scripts/qemu_target.sh status
python3 video/record.py
python3 video/render.py
