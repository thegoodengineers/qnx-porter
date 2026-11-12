"""Render the recorded demo (video/out/demo.cast + markers.json) and the slides into video/out/qnx-porter-demo.mp4.

Only timing is changed: pauses longer than MAX_GAP seconds while a command runs are shortened, and the
screen says so. Every character of terminal output is what record.py captured.

Usage: python3 video/render.py    (needs ffmpeg and Pillow)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / "out"
W, H, FPS = 1920, 1080, 30
COLS, ROWS = 140, 33
CAP_H, PAD = 110, 40
TYPE_CPS = 30      # typing speed for the command line
MAX_GAP = 1.0      # longest pause kept while a command runs (seconds)
HOLD_CMD = 6.0     # pause after each command finishes, to read it
SLIDE_SECONDS = {"title": 7, "problem": 13, "results": 12, "failures": 20, "close": 12}

BG, FG, DIM = (15, 20, 25), (214, 221, 230), (120, 132, 145)
ACCENT, GREEN, YELLOW, RED = (64, 156, 255), (98, 209, 129), (240, 200, 90), (240, 110, 100)
MONO = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MONO_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
SANS = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
SANS_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
F_TERM = ImageFont.truetype(MONO, 21)
F_TERM_B = ImageFont.truetype(MONO_B, 21)
F_CAP = ImageFont.truetype(SANS_B, 30)
F_NOTE = ImageFont.truetype(SANS, 22)

SLIDES = {
    "title": ("qnx-porter", [
        "Ports open-source C/C++ libraries to QNX 8.0,",
        "and proves each port by running the library's own tests on a QNX target.",
        "",
        "The Good Engineers  ·  QNX Global Hackathon 2026  ·  Developer Tooling & Host Tools"]),
    "problem": ("Why", [
        "QNX 8.0 is free for developers, but most open-source C libraries have never been built for it.",
        "Porting means the same fixes again and again: missing headers, libsocket, Linux-only calls.",
        "A port that only compiles proves little. The library's tests have to run on QNX.",
        "",
        "qnx-porter: rules first, every change a reviewable patch with its reason,",
        "and the tests run on a QNX 8.0 target."]),
    "failures": ("The 5 tests that still fail (of 381), stated plainly", [
        "libmodbus: its test script calls killall, which QNX does not have (QNX uses slay).",
        "nng httpclient and resolver: they need the internet; the QEMU target has none.",
        "nng udp_test: QNX returns a different error than Linux for two invalid addresses.",
        "nng sockaddr_test: failed in the campaign run, passed when re-run by hand.",
        "",
        "Not run: paho.mqtt.c (its tests need an MQTT broker) and libcbor (needs cmocka built for QNX).",
        "Details for each: docs/LEARNINGS.md and ports/<library>/logs/tests.log."]),
    "close": ("github.com/thegoodengineers/qnx-porter", [
        "Apache-2.0  ·  SETUP.md  ·  docs/CODELAB.md (step-by-step tutorial)",
        "Every number shown was printed by qnx-porter and scripts/ports_csv.py during this recording.",
        "",
        "Optional: a language model can propose a diff for errors no rule covers;",
        "it is kept only if the rebuild clears the error, and shown as reverted otherwise."]),
}

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")


class Screen:
    def __init__(self):
        self.lines = [""]
        self.col = 0

    def write(self, text: str):
        for ch in ANSI.sub("", text):
            if ch == "\n":
                self.lines.append("")
                self.col = 0
            elif ch == "\r":
                self.col = 0
            elif ch == "\t":
                self.write(" " * (8 - self.col % 8))
            elif ch >= " ":
                if self.col >= COLS:
                    self.lines.append("")
                    self.col = 0
                ln = self.lines[-1]
                self.lines[-1] = ln[:self.col].ljust(self.col) + ch + ln[self.col + 1:]
                self.col += 1
        self.lines = self.lines[-ROWS:]

    def clear(self):
        self.lines, self.col = [""], 0


def line_color(ln: str):
    if ln.startswith("$ "):
        return GREEN
    if re.search(r"\bfix \d{4}\b|^\s*fix |printf-null", ln):
        return YELLOW
    if re.search(r"tests passed|build OK|^PASS|^ok ", ln):
        return GREEN
    if re.search(r"error|FAIL|Memory fault|SIGSEGV|BAD", ln):
        return RED
    return FG


def draw_terminal(screen: Screen, caption: str, note: str) -> bytes:
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, CAP_H], fill=(22, 30, 40))
    d.rectangle([0, CAP_H - 4, W, CAP_H], fill=ACCENT)
    d.text((PAD, 36), caption, font=F_CAP, fill=(240, 244, 248))
    y = CAP_H + 24
    for ln in screen.lines:
        d.text((PAD, y), ln, font=F_TERM_B if ln.startswith("$ ") else F_TERM, fill=line_color(ln))
        y += 27
    if note:
        d.text((W - PAD - d.textlength(note, font=F_NOTE), H - 40), note, font=F_NOTE, fill=DIM)
    return img.tobytes()


def draw_slide(name: str) -> bytes:
    title, body = SLIDES[name]
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    big = name in ("title", "close")
    ft = ImageFont.truetype(SANS_B, 96 if name == "title" else 56)
    fb = ImageFont.truetype(SANS, 36 if big else 34)
    y = 300 if big else 190
    d.rectangle([PAD * 3, y - 40, PAD * 3 + 120, y - 32], fill=ACCENT)
    d.text((PAD * 3, y), title, font=ft, fill=(245, 248, 252))
    y += 150 if name == "title" else 110
    for ln in body:
        d.text((PAD * 3, y), ln, font=fb, fill=FG if ln else FG)
        y += 58
    return img.tobytes()


def results_slide(text: str) -> None:
    """The summary slide, with numbers taken from the recorded ports_csv.py output (never typed in)."""
    m = re.search(r"(\d+) libraries, (\d+) built for QNX 8\.0; tests ran for (\d+): (\d+)/(\d+) passed", text)
    rows = re.findall(r"^(\S+)\s+built\s+(\d*)\s+(\d*)\s+(\d+)\s*$", text, re.M)
    if not m or not rows:
        raise SystemExit("results not found in the recording")
    lib, built, ran, ok, total = m.groups()
    patches = sum(int(r[3]) for r in rows)
    SLIDES["results"] = ("Results on QNX 8.0", [
        f"{built} of {lib} libraries built for QNX 8.0 with qcc.",
        f"{ok} of {total} of their own tests passed on the QNX 8.0 target ({ran} libraries with tests).",
        f"{patches} patches in total, all by deterministic rules, each with its reason and the error it fixes.",
        "",
        "Numbers from scripts/ports_csv.py in this recording (results/ports.csv)."])


def build_timeline():
    """[(seconds_on_screen, frame_function)] from the markers and the cast."""
    markers = json.loads((OUT / "markers.json").read_text(encoding="utf-8"))
    events = [json.loads(ln) for ln in (OUT / "demo.cast").read_text(encoding="utf-8").splitlines()[1:]]
    results_slide("".join(e[2] for e in events).replace("\r", ""))
    screen, caption, steps = Screen(), "", []
    ei = 0
    for i, m in enumerate(markers):
        if "slide" in m:
            frame = draw_slide(m["slide"])
            steps.append((SLIDE_SECONDS[m["slide"]], lambda f=frame: f))
        elif "caption" in m:
            caption = m["caption"]
            screen.clear()
        elif "command" in m:
            cmd, typed = m["command"], "$ "
            screen.write("\n" if screen.lines != [""] else "")
            for k in range(0, len(cmd) + 1, max(1, TYPE_CPS // FPS)):
                s2 = Screen()
                s2.lines, s2.col = list(screen.lines), screen.col
                s2.write(typed + cmd[:k])
                frame = draw_terminal(s2, caption, "")
                steps.append((1 / FPS, lambda f=frame: f))
            screen.write(typed + cmd + "\n")
            end = markers[i + 1]["t"]
            last_t, shortened = m["t"], 0.0
            while ei < len(events) and events[ei][0] <= end:
                t, _, data = events[ei]
                gap = t - last_t
                shortened += max(0.0, gap - MAX_GAP)
                note = f"waits shortened: {shortened:.0f} s of real time skipped so far" if shortened > 1 else ""
                frame = draw_terminal(screen, caption, note)
                steps.append((min(gap, MAX_GAP), lambda f=frame: f))
                screen.write(data)
                last_t = t
                ei += 1
            note = f"real run time of this command: {end - m['t']:.0f} s" if end - m["t"] > 5 else ""
            frame = draw_terminal(screen, caption, note)
            steps.append((HOLD_CMD, lambda f=frame: f))
    return steps


def main() -> int:
    steps = build_timeline()
    total = sum(s for s, _ in steps)
    print(f"timeline: {total:.1f} s", file=sys.stderr)
    out = OUT / "qnx-porter-demo.mp4"
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                           "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)],
                          stdin=subprocess.PIPE)
    acc = 0.0
    for seconds, frame in steps:
        acc += seconds * FPS
        n = int(acc)
        acc -= n
        if n:
            data = frame()
            for _ in range(n):
                ff.stdin.write(data)
    ff.stdin.close()
    ff.wait()
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)
    return ff.returncode


if __name__ == "__main__":
    sys.exit(main())
