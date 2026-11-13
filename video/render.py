"""Render the recorded demo (video/out/demo.cast + markers.json), the slides and the site screenshots into
video/out/qnx-porter-demo.mp4.

Only timing is changed. Each scene has the length record.py gives it (the shot list in docs/VIDEO_SCRIPT.md):
pauses while a command runs are shortened, the hold after a command is shortened and the typing is sped up until
the scene fits, and the screen says how much wait was cut. Every character of terminal output is what record.py
captured. Every number on a slide or in the narration is read from the recording or from a result file in the
repository, never typed here.

The narration (NARRATION, one line per shot) is burned in as a caption bar. If video/voice.wav exists it is the
sound track; there is no music.

Usage: python3 video/render.py [--out DIR] [--stills]    (needs ffmpeg and Pillow)
  --out DIR   read markers.json and demo.cast from DIR and write the video there (default video/out)
  --stills    write one PNG per scene (its last frame) to DIR/stills/ instead of the video
"""
import argparse
import csv
import functools
import json
import math
import re
import subprocess
import sys
import wave
from pathlib import Path

VIDEO = Path(__file__).resolve().parent
ROOT = VIDEO.parent
W, H, FPS = 1920, 1080, 30
COLS, ROWS = 140, 28
CAP_H, PAD = 110, 40
NAR_SIZE, NAR_LINE, NAR_LINES = 28, 36, 3
NAR_TOP = H - NAR_LINES * NAR_LINE - 28   # the narration bar, at the bottom of every frame
# Terminal pacing: (typing speed in characters/s, longest pause kept while a command runs in s, hold after each
# command in s). A scene starts RELAXED and moves towards TIGHT only as far as it must to fit its length.
RELAXED = (30.0, 1.0, 6.0)
TIGHT = (200.0, 0.05, 1.0)
LIMIT, AIM = 170.0, (140.0, 160.0)   # fail at LIMIT (a margin under the 3:00 rule); warn outside AIM

BG, FG, DIM = (15, 20, 25), (214, 221, 230), (120, 132, 145)
ACCENT, GREEN, YELLOW, RED = (64, 156, 255), (98, 209, 129), (240, 200, 90), (240, 110, 100)
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

# One line per shot, spoken in our own voice and burned in as captions. {names} are filled by facts() from the
# recording and the result files; docs/VIDEO_SCRIPT.md gives the values on the current commit.
NARRATION = {
    "title": "qnx-porter ports open-source C and C++ libraries to QNX 8.0, and proves each port on QNX itself.",
    "problem": "A QNX target has no compiler, and the host can't run QNX binaries. Only tests on the target prove a port.",
    "why-c": "QNX is built for C and C++, and other languages wrap C libraries. Port the C layer, and the rest can follow.",
    "target": "A real QNX 8.0 target, x86_64 in QEMU, and the SDP 8.0 toolchain. {also_aarch64}",
    "mbedtls": "A real port: mbedtls. Round 1: {mb_errors} errors. QNX keeps inet_pton in libsocket, not libc, so a "
               "documented rule adds it. Round {mb_rounds} builds, and mbedtls's own tests run on QNX: {mb_passed} of "
               "{mb_total} pass. Each change is a patch with its rule, its reason and the exact error.",
    "json-c": "When a test crashes on QNX, qnx-porter copies the core dump back and reads the backtrace. json-c passes "
              "NULL to printf: glibc prints (null), QNX faults. A rule fixes the test, and json-c goes from "
              "{jc_before} to {jc_after} of {jc_total}.",
    "campaign": "The campaign: {lib} libraries. On x86_64, {built} built for QNX 8.0, and {ok} of {total} of their own "
                "tests passed on the target. {aarch64_built} {rules_phrase}",
    "failures": "Every failing test is listed by cause: QNX libc differences such as strtod rounding, with reproducers, "
                "and things our test image lacks.",
    "comparison": "{cmp_have} of our libraries also have a hand-made QNX port; in {cmp_same}, we found the same change "
                  "independently. For {recipes} CMake ports they lack, we generate recipes.",
    "crates": "The same tool ports Rust crates: {cr_built} of {cr_total} build for QNX 8.0.",
    "model": "Where no rule applied, the model step built {model_libs}, each diff proved by a rebuild.",
    "rt": "Real-time check: the latency of one call in {rt_libs} libraries on QNX in QEMU, idle, loaded and isolated.",
    "site": "Everything is on the website, generated from the same reports: every port, every rule, and a weekly "
            "check against upstream. Install with pip install qnx-porter.",
    "paper": "The method and every result are written up in a research paper.",
    "close": "Rules first; a language model only where no rule fits, kept only if the rebuild proves it. "
             "Every command here ran on QNX 8.0.",
}

STATIC_SLIDES = {
    "title": ("qnx-porter", [
        "Ports open-source C/C++ libraries to QNX 8.0 and proves each port with the library's own tests on QNX.",
        "",
        "The Good Engineers  ·  QNX Global Hackathon 2026  ·  Developer Tooling & Host Tools"]),
    "problem": ("Why a real-time OS needs this", [
        "A QNX target has no compiler: every library is cross-compiled on a host with qcc.",
        "The host cannot run QNX binaries: only tests on a QNX target prove a port.",
        "The same Linux-isms break library after library: missing headers, libsocket, Linux-only calls."]),
    "close": ("github.com/thegoodengineers/qnx-porter", [
        "Apache-2.0  ·  pip install qnx-porter  ·  thegoodengineers.github.io/qnx-porter",
        "",
        "Every command in this video ran for real on QNX 8.0 in QEMU; video/make.sh re-records it."]),
}

ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07]*\x07")
# The lines scripts/ports_csv.py prints, one per architecture, and the rows of the cut | column table after them.
SUMMARY = re.compile(r"^(\S+): (\d+) libraries, (\d+) built for QNX 8\.0; tests ran for (\d+)"
                     r"(?: \(at least one test each\))?: (\d+)/(\d+) passed", re.M)
TABLE_ROW = re.compile(r"^(\S+)\s+(\S+)\s+(\S+)\s+(?:\d+\s+\d+\s+)?(\d+)\s+(\d+)\s+(\d+)\s*$", re.M)
ARCH_PREFIX = {"x86_64": "", "aarch64le": "a_"}


def csv_rows(name: str) -> list[dict]:
    with (ROOT / "results" / name).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def campaign(text: str) -> dict:
    """Per architecture (x86_64 unprefixed, aarch64le as a_*): the summary line and the patch sums of its rows."""
    out = {}
    rows = TABLE_ROW.findall(text)
    for arch, lib, built, ran, ok, total in SUMMARY.findall(text):
        if arch not in ARCH_PREFIX:
            continue
        rs = [r for r in rows if r[1] == arch]
        if len(rs) != int(lib):
            raise SystemExit(f"the recorded table has {len(rs)} {arch} rows, but ports_csv.py says {lib} libraries")
        p = ARCH_PREFIX[arch]
        out.update({p + "lib": lib, p + "built": built, p + "ran": ran, p + "ok": ok, p + "total": total,
                    p + "patches": sum(int(r[3]) for r in rs), p + "by_rule": sum(int(r[4]) for r in rs),
                    p + "by_model": sum(int(r[5]) for r in rs)})
    return out


def facts(texts: dict) -> dict:
    """Every number the slides and the narration use: from the recorded output of each shot, or a result file."""
    f = {}
    t = texts.get("mbedtls", "")
    if m := re.search(r"round 1: (\d+) error", t):
        f["mb_errors"] = m[1]
    if m := re.search(r"build OK after (\d+) round", t):
        f["mb_rounds"] = m[1]
    if m := re.findall(r"(\d+)/(\d+) tests passed", t):
        f["mb_passed"], f["mb_total"] = m[-1]
    t = texts.get("json-c", "")
    if m := re.search(r"^\s*(\d+)/(\d+) tests passed", t, re.M):
        f["jc_before"] = m[1]
    if m := re.search(r"after crash fixes: (\d+)/(\d+) tests passed", t):
        f["jc_after"], f["jc_total"] = m.groups()
    f.update(campaign(texts.get("campaign", "")))
    if "lib" in f:
        f["also_aarch64"] = ("The campaign also ran on aarch64 on QEMU." if "a_lib" in f
                             else "An aarch64 campaign on QEMU is running.")
        f["aarch64_built"] = (f"On aarch64 on QEMU, {f['a_built']} built." if "a_lib" in f
                              else "The aarch64 campaign on QEMU is still running.")
        f["rules_phrase"] = (f"All {f['patches']} patches came from rules." if f["by_rule"] == f["patches"]
                             else f"{f['by_rule']} of {f['patches']} patches came from rules.")
    t = texts.get("comparison", "")
    if m := re.search(r"Of the (\d+) libraries", t):
        f["cmp_have"] = m[1]
    if m := re.search(r"found independently[^|\n]*\|[^|\n]*\|\s*(\d+)\s*\|", t):
        f["cmp_same"] = m[1]
    if m := re.findall(r"^\s*(\d+)\s*$", t, re.M):
        f["recipes"] = m[-1]
    if m := re.search(r"\((\d+) libraries measured\)", texts.get("rt", "")):
        f["rt_libs"] = m[1]
    if (ROOT / "results" / "crates.csv").exists():
        rs = [r for r in csv_rows("crates.csv") if r["arch"] == "x86_64"]
        f["cr_built"], f["cr_total"] = sum(r["build_result"] == "built" for r in rs), len(rs)
    if (ROOT / "results" / "model_eval.csv").exists():
        libs = [r["library"] for r in csv_rows("model_eval.csv")
                if r["rules_model_build"] == "built" and r["rules_only_build"] != "built"]
        if libs:
            f["model_libs"] = " and ".join([", ".join(libs[:-1]), libs[-1]] if len(libs) > 1 else libs)
    return f


def narration(shot: str, f: dict) -> str:
    try:
        return NARRATION[shot].format_map(f)
    except KeyError as e:
        raise SystemExit(f"the narration of shot '{shot}' needs {e}, which neither the recording nor the result files gave")


def slide(name: str, f: dict) -> tuple[str, list[str]]:
    if name in STATIC_SLIDES:
        return STATIC_SLIDES[name]
    x86 = [r for r in csv_rows("ports.csv") if r["arch"] == "x86_64"]
    if name == "why-c":
        by = {r["library"]: r for r in x86}
        parts = []
        for lib in ("zlib", "libsodium", "sqlite"):
            r = by[lib]
            if r["build_result"] != "built":
                parts.append(f"{lib} did not build")
            elif r["tests_total"] not in ("", "0"):
                parts.append(f"{lib} {r['tests_passed']}/{r['tests_total']} tests pass")
            else:
                parts.append(f"{lib} built ({r['note'].removeprefix('build only: ')})")
        return ("Why C and C++", [
            "QNX itself is built for C and C++.",
            "Other languages wrap C libraries: Python's zlib module, PyNaCl on libsodium, Rust's rusqlite on SQLite.",
            "On QNX 8.0: " + ", ".join(parts) + "."])
    if name == "failures":
        failed = [r for r in x86 if r["build_result"] != "built"]
        linux = [r["library"] for r in failed if "expected not to port" in r["note"]]
        other = [r["library"] for r in failed if r["library"] not in linux]
        return ("What still fails, by cause", [
            "QNX C library differences, each with a reproducer in docs/qnx-reports/: strtod() rounding, "
            "strftime() %Ex, fchdir() needs O_DIRECTORY, qsort() with an inconsistent comparator.",
            "What our test image lacks: killall, internet access, Tcl, an MQTT broker.",
            f"{len(failed)} libraries did not build with rules only: {' and '.join(linux)} are Linux-only by design; "
            f"{' and '.join(other)} stop on errors no rule covers yet.",
            "",
            "Every failing test, by cause: README.md (What the failures are) and docs/LEARNINGS.md."])
    if name == "results":
        if "lib" not in f:
            raise SystemExit("results not found in the recording: no 'x86_64: ...' line from scripts/ports_csv.py")
        aarch = (f"aarch64 on QEMU: {f['a_built']} of {f['a_lib']} built; {f['a_ok']} of {f['a_total']} tests passed; "
                 f"{f['a_patches']} patches, {f['a_by_model']} by a language model." if "a_lib" in f
                 else "aarch64 on QEMU: campaign running.")
        return ("Results on QNX 8.0", [
            f"x86_64 in QEMU: {f['built']} of {f['lib']} libraries built for QNX 8.0 with qcc.",
            f"{f['ok']} of {f['total']} of their own tests passed on the QNX target "
            f"({f['ran']} libraries with at least one test).",
            f"{f['patches']} patches: {f['by_rule']} by deterministic rules, {f['by_model']} by a language model; "
            "each with its reason and the error it fixes.",
            aarch,
            "",
            "Numbers from scripts/ports_csv.py in this recording (results/ports.csv)."])
    raise SystemExit(f"no slide named {name}")


class Screen:
    def __init__(self):
        self.lines = [""]
        self.col = 0

    def copy(self) -> "Screen":
        s = Screen()
        s.lines, s.col = list(self.lines), self.col
        return s

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


def load(out: Path) -> list[dict]:
    """The recorded scenes in order: each marker with a shot, and for terminal scenes its commands and output."""
    markers = json.loads((out / "markers.json").read_text(encoding="utf-8"))
    events = [json.loads(ln) for ln in (out / "demo.cast").read_text(encoding="utf-8").splitlines()[1:]]
    scenes, ei = [], 0
    for i, m in enumerate(markers):
        if "shot" in m:
            scenes.append({**m, "commands": []})
        elif "command" in m:
            end, evs = markers[i + 1]["t"], []
            while ei < len(events) and events[ei][0] <= end:
                evs.append((events[ei][0], events[ei][2]))
                ei += 1
            scenes[-1]["commands"].append({"cmd": m["command"], "t": m["t"], "end": end, "events": evs})
    return scenes


def shot_texts(scenes: list[dict]) -> dict:
    texts = {}
    for s in scenes:
        for c in s["commands"]:
            texts[s["shot"]] = texts.get(s["shot"], "") + ANSI.sub("", "".join(d for _, d in c["events"])).replace("\r", "")
    return texts


def pacing(f: float) -> tuple:
    """f = 0 is RELAXED, f = 1 is TIGHT."""
    return tuple(a + (b - a) * f for a, b in zip(RELAXED, TIGHT))


def typing_frames(cmd: str, cps: float) -> int:
    return max(1, math.ceil(len(cmd) * FPS / cps))


def gaps(c: dict) -> list[float]:
    ts = [c["t"]] + [t for t, _ in c["events"]]
    return [b - a for a, b in zip(ts, ts[1:])]


def terminal_length(cmds: list[dict], p: tuple) -> float:
    cps, gap, hold = p
    return sum(typing_frames(c["cmd"], cps) / FPS + sum(min(g, gap) for g in gaps(c)) + hold for c in cmds)


def fit(cmds: list[dict], seconds: float) -> tuple[tuple, float]:
    """The most relaxed pacing that fits the scene into seconds, and the pad added to the last hold to fill it."""
    if terminal_length(cmds, pacing(1.0)) > seconds:
        return pacing(1.0), 0.0  # cannot fit: the table printed by main() marks the scene as over
    lo, hi = 0.0, 1.0
    if terminal_length(cmds, pacing(0.0)) <= seconds:
        hi = 0.0
    for _ in range(40):
        if hi - lo < 1e-4:
            break
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if terminal_length(cmds, pacing(mid)) <= seconds else (mid, hi)
    p = pacing(hi)
    return p, max(0.0, seconds - terminal_length(cmds, p))


def check_length(total: float) -> None:
    if total >= LIMIT:
        raise SystemExit(f"the video would be {total:.1f} s; it must stay under {LIMIT:.0f} s (the 3:00 rule, with margin)")
    if not AIM[0] <= total <= AIM[1]:
        print(f"warning: the video is {total:.1f} s, outside the {AIM[0]:.0f}-{AIM[1]:.0f} s aim", file=sys.stderr)


# --- drawing (Pillow is imported only here, so the parsing and timing above can be tested without it) ---

@functools.lru_cache(None)
def font(name: str, size: int):
    from PIL import ImageFont
    return ImageFont.truetype(FONT_DIR + name + ".ttf", size)


def wrap(text: str, fnt, width: int) -> list[str]:
    lines = [""]
    for word in text.split(" "):
        cand = (lines[-1] + " " + word).strip()
        if fnt.getlength(cand) <= width or not lines[-1]:
            lines[-1] = cand
        else:
            lines.append(word)
    return lines


def caption_bar(img, text: str):
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    fnt = font("DejaVuSans", NAR_SIZE)
    lines = wrap(text, fnt, W - 2 * PAD)
    if len(lines) > NAR_LINES:
        raise SystemExit(f"narration too long for {NAR_LINES} caption lines: {text}")
    d.rectangle([0, NAR_TOP, W, H], fill=(8, 11, 15))
    d.rectangle([0, NAR_TOP, W, NAR_TOP + 3], fill=ACCENT)
    y = NAR_TOP + 16
    for ln in lines:
        d.text((PAD, y), ln, font=fnt, fill=(240, 244, 248))
        y += NAR_LINE
    return img.tobytes()


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


def draw_terminal(lines: list[str], caption: str, note: str, nar: str) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, CAP_H], fill=(22, 30, 40))
    d.rectangle([0, CAP_H - 4, W, CAP_H], fill=ACCENT)
    d.text((PAD, 36), caption, font=font("DejaVuSans-Bold", 30), fill=(240, 244, 248))
    y = CAP_H + 24
    for ln in lines:
        bold = "DejaVuSansMono-Bold" if ln.startswith("$ ") else "DejaVuSansMono"
        d.text((PAD, y), ln, font=font(bold, 21), fill=line_color(ln))
        y += 27
    if note:
        fn = font("DejaVuSans", 22)
        d.text((W - PAD - d.textlength(note, font=fn), NAR_TOP - 36), note, font=fn, fill=DIM)
    return caption_bar(img, nar)


def draw_slide(title: str, body: list[str], big: bool, nar: str) -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    fb = font("DejaVuSans", 36 if big else 34)
    y = 260 if big else 170
    d.rectangle([PAD * 3, y - 40, PAD * 3 + 120, y - 32], fill=ACCENT)
    d.text((PAD * 3, y), title, font=font("DejaVuSans-Bold", 96 if title == "qnx-porter" else 56), fill=(245, 248, 252))
    y += 150 if title == "qnx-porter" else 110
    for para in body:
        for ln in wrap(para, fb, W - PAD * 6) if para else [""]:
            d.text((PAD * 3, y), ln, font=fb, fill=FG)
            y += 50
        y += 14
    return caption_bar(img, nar)


def draw_image(path: Path, nar: str) -> bytes:
    from PIL import Image
    img = Image.open(path).convert("RGB")
    if img.size != (W, H):
        img = img.resize((W, H), Image.LANCZOS)
    return caption_bar(img, nar)


# --- the timeline ---

def build_timeline(scenes: list[dict], f: dict):
    """[(seconds, frame function)] for the whole video, and [(scene label, target, actual, last step index)]."""
    steps, table = [], []
    for s in scenes:
        nar, start = narration(s["shot"], f), len(steps)
        if "slide" in s:
            title, body = slide(s["slide"], f)
            steps.append((s["seconds"], lambda t=title, b=body, big=s["slide"] in ("title", "close"), n=nar:
                          draw_slide(t, b, big, n)))
            label = s["slide"]
        elif "image" in s:
            steps.append((s["seconds"], lambda p=VIDEO / s["image"], n=nar: draw_image(p, n)))
            label = Path(s["image"]).stem
        else:
            (cps, gap, hold), pad = fit(s["commands"], s["seconds"])
            screen, caption, label = Screen(), s["caption"], s["shot"]
            for k, c in enumerate(s["commands"]):
                if screen.lines != [""]:
                    screen.write("\n")
                n = typing_frames(c["cmd"], cps)
                for j in range(1, n + 1):
                    s2 = screen.copy()
                    s2.write("$ " + c["cmd"][:round(len(c["cmd"]) * j / n)])
                    steps.append((1 / FPS, lambda ln=s2.lines, cp=caption, n_=nar: draw_terminal(ln, cp, "", n_)))
                screen.write("$ " + c["cmd"] + "\n")
                last, skipped = c["t"], 0.0
                for t, data in c["events"]:
                    skipped += max(0.0, t - last - gap)
                    note = f"waits shortened: {skipped:.0f} s of real time skipped so far" if skipped > 1 else ""
                    steps.append((min(t - last, gap), lambda ln=list(screen.lines), cp=caption, no=note, n_=nar:
                                  draw_terminal(ln, cp, no, n_)))
                    screen.write(data)
                    last = t
                real = c["end"] - c["t"]
                note = f"real run time of this command: {real:.0f} s" if real > 5 else ""
                steps.append((hold + (pad if k == len(s["commands"]) - 1 else 0.0),
                              lambda ln=list(screen.lines), cp=caption, no=note, n_=nar: draw_terminal(ln, cp, no, n_)))
        table.append((label, s["shot"], s["seconds"], sum(d for d, _ in steps[start:]), len(steps) - 1))
    return steps, table


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=VIDEO / "out")
    ap.add_argument("--stills", action="store_true")
    a = ap.parse_args()
    scenes = load(a.out)
    f = facts(shot_texts(scenes))
    steps, table = build_timeline(scenes, f)
    total = sum(d for d, _ in steps)
    for label, shot, target, actual, _ in table:
        print(f"{label:<16} {shot:<11} target {target:5.1f} s   actual {actual:5.1f} s"
              f"{'   OVER' if actual > target + 0.05 else ''}", file=sys.stderr)
    for shot in dict.fromkeys(s["shot"] for s in scenes):
        secs = sum(t[2] for t in table if t[1] == shot)
        text = narration(shot, f)
        words = len(text.split())
        print(f"narration {shot:<11} {words:3d} words in {secs:4.1f} s ({words / secs:.1f} words/s): {text}",
              file=sys.stderr)
    print(f"total: {total:.1f} s ({int(total // 60)}:{total % 60:04.1f})", file=sys.stderr)
    check_length(total)
    if a.stills:
        from PIL import Image
        (a.out / "stills").mkdir(exist_ok=True)
        for i, (label, *_, last) in enumerate(table):
            Image.frombytes("RGB", (W, H), steps[last][1]()).save(a.out / "stills" / f"{i + 1:02d}-{label}.png")
        print(f"wrote {len(table)} stills to {a.out / 'stills'}", file=sys.stderr)
        return 0
    out = a.out / "qnx-porter-demo.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-"]
    voice = VIDEO / "voice.wav"
    if voice.exists():
        with wave.open(str(voice)) as w:
            vs = w.getnframes() / w.getframerate()
        print(f"voice.wav: {vs:.1f} s" + ("; longer than the video, its end is cut" if vs > total else ""), file=sys.stderr)
        cmd += ["-i", str(voice), "-c:a", "aac", "-af", "apad", "-shortest"]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "22", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(out)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
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
