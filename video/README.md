# video/: how the demo is made

`video/make.sh` re-records the demo from real runs. `record.py` runs every command of its `scenes()` list on the
build host against the QNX 8.0 QEMU target and saves `out/demo.cast` and `out/markers.json`. `render.py` replays
the recording together with the slides and the site screenshots into `out/qnx-porter-demo.mp4`. It changes only
the timing, and says on screen how much wait it cut. The shot list, the narration and where every number comes
from: [docs/VIDEO_SCRIPT.md](../docs/VIDEO_SCRIPT.md).

**Status.** The pipeline for the new 2:38 cut is in place and tested without the QNX target (see "Tests"). It has
**not been recorded yet**: the committed `out/` files are still the older 10-library cut until `make.sh` runs.

## Re-record (when the QNX target is free)
```bash
sudo apt install ffmpeg python3-pil        # once
scripts/qemu_target.sh start               # the x86_64 QNX 8.0 target
video/make.sh                              # checks, records, then renders
```
`make.sh` first runs `record.py --check`, which stops with a message if a screenshot, ffmpeg or Pillow is
missing, so a long recording is never wasted. It then sources the SDP, checks the target and records. The
recording builds mbedtls and json-c and runs their own tests (148 and 28) on the QEMU target. Do not run it while
a campaign is using the same machine.

After recording, `render.py` prints, per scene, its length next to its target, then every narration line with
the numbers read from this recording and its words per second, then the total. Record `video/voice.wav` (our own
voice, no music) from those lines and run `python3 video/render.py` again to mux it in. Commit the new
`out/qnx-porter-demo.mp4`, `out/demo.cast` and `out/markers.json`.

## Scenes
Lengths are in `record.py` `scenes()`; the narration, slides and parsing are in `render.py`.

| Shot | Scene | Length | Needs the QNX target | Numbers read from |
|---|---|---|---|---|
| 1 | slide `title` | 7 s | no | none |
| 2 | slide `problem` ("Why a real-time OS needs this") | 9 s | no | none |
| 3 | slide `why-c` | 9 s | no | `results/ports.csv` (zlib, libsodium, sqlite) |
| 4 | `scripts/qemu_target.sh status`, `qnx-porter doctor` | 10 s | **yes** | the recording (aarch64 sentence from shot 7's output) |
| 5 | `qnx-porter port` mbedtls v4.2.0, then `head -4` of `*-link-libsocket.patch` | 22 s | **yes** | the recording |
| 6 | `qnx-porter port` json-c, then the `crashes.log` backtrace | 17 s | **yes** | the recording |
| 7 | `scripts/ports_csv.py`, the `cut -d, -f1,4,5,6,7,8,9,10 \| column` table; slide `results` | 9 s + 9 s | no | the recording |
| 8 | slide `failures` | 9 s | no | `results/ports.csv` (failed builds) |
| 9 | the Summary of `docs/related/qnx-ports-comparison.md`, `ls recipes/build-files/ports \| wc -l` | 11 s | no | the recording |
| 10 | `results/crates.csv` table, only if that file exists | 6 s | no | `results/crates.csv` |
| 11 | `results/model_eval.csv` table and `head -3` of the libuv model patch, only if that file exists | 7 s | no | `results/model_eval.csv` |
| 12 | the latency table of `docs/RT_RESULTS.md` | 7 s | no | the recording |
| 13 | images `shots/site-{overview,results,mbedtls,weekly}.png`, then `pip index versions qnx-porter` | 4 x 2 s + 3 s | no (pip needs the internet) | none spoken |
| 14 | image `shots/site-paper.png` | 5 s | no | none |
| 15 | slide `close` | 10 s | no | none |

mbedtls and json-c use the pins of `campaign.yaml` (mbedtls v4.2.0 with programs on, json-c 0.19), which match the
published results and `results/runs/campaign-8.log`.

## How `render.py` works
- **Numbers.** None is typed. `facts()` reads them from each shot's recorded output (for example `round 1: 26
  error(s)`, `x86_64: 61 libraries, 58 built ...; tests ran for 43 (at least one test each): 1563/1658 passed`)
  or from a result CSV. The results slide anchors on the `x86_64:` line, adds the `aarch64le:` line when
  `ports_csv.py` printed one (else "aarch64 on QEMU: campaign running"), and sums patches, patches by rule and
  patches by model over each arch's own table rows. It stops if a number is missing, or if the table's row count
  disagrees with the summary line.
- **Per-shot timing.** Each scene has a length. A terminal scene starts at relaxed pacing (typing 30 characters
  a second, pauses up to 1 s, 6 s hold after each command) and tightens towards 200 characters a second, 0.05 s
  pauses and a 1 s hold only as far as it must to fit; what is left is held on the last frame.
- **Length guard.** It fails if the total reaches 170 s and warns outside 140-160 s.
- **Placeholders by file presence.** Shots 10 and 11 go in only when `results/crates.csv` and
  `results/model_eval.csv` exist on the recorded commit. No flag.
- **Narration.** `NARRATION` has one line per shot. It is drawn as a caption bar at the bottom of every frame of
  that shot (at most three lines). If `video/voice.wav` exists it is muxed in (AAC, padded with silence to the
  video's length). There is never music.
- **Images.** An image scene shows a PNG, scaled to 1920x1080, for its length.

## Screenshots
`video/shots/site-overview.png`, `site-results.png`, `site-mbedtls.png`, `site-weekly.png` and `site-paper.png`
are 1920x1080 captures of the live site, page content only (no browser toolbar, tabs or bookmarks). They were
taken with headless Chrome, which renders only the page:
```bash
B=https://thegoodengineers.github.io/qnx-porter
for p in overview:index.html results:results.html mbedtls:ports/mbedtls-x86_64.html weekly:upstream.html paper:paper.html; do
  google-chrome --headless=new --hide-scrollbars --force-device-scale-factor=1 --window-size=1920,1080 \
    --virtual-time-budget=8000 --screenshot="video/shots/site-${p%%:*}.png" "$B/${p#*:}"
done
```
Retake them if the site changes before recording. By hand, a browser window with its page area at exactly
1920x1080 and a screenshot of that area only (no toolbar) is the same.

## Tests (no QNX target needed)
- `python3 -m pytest -q -p no:cacheprovider tests/test_video.py`: the results-slide parsing against the real
  `scripts/ports_csv.py` output (its own `summary()` and the CSV it writes), against the committed campaign (it
  must match the `README.md` headline), the narration filled from the committed logs, the placeholders, the
  fitting and the length guard.
- `python3 video/render.py --out DIR --stills` writes the last frame of each scene of a recording in `DIR` as
  a PNG, to check slides, captions and screenshots without encoding the video.
