# video/: how the demo is made, and what must change for the new cut

`video/make.sh` re-records the demo from real runs. `record.py` runs every command in its `SCENES` list on the
build host against the QNX 8.0 QEMU target and saves `out/demo.cast` and `out/markers.json`. `render.py` replays
the recording together with the slides into `out/qnx-porter-demo.mp4`. It changes only the timing, and says on
screen how much wait it cut.

The committed `out/` files are the **older 10-library cut**. The new cut is the shot list in
[docs/VIDEO_SCRIPT.md](../docs/VIDEO_SCRIPT.md). What `make.sh` and its inputs need for that cut is listed below.
None of it is done yet, and `make.sh` has not been run for the new cut.

## Re-record (when the QNX target is free)
```bash
sudo apt install ffmpeg python3-pil        # once
scripts/qemu_target.sh start               # the x86_64 QNX 8.0 target
video/make.sh                              # records, then renders
```
The recording builds mbedtls and json-c and runs their own tests (130 and 25) on the QEMU target. Do not run it while a
campaign (for example the aarch64 one) is using the same machine.

## Scenes: existing, changed, new

| Shot | Scene in `record.py` `SCENES` | Status | Needs the QNX target | What must change |
|---|---|---|---|---|
| 1 | `("slide", "title")` | exists | no | `render.py` `SLIDES["title"]`: the one-line pitch from the script. |
| 2 | `("slide", "problem")` | exists, changed | no | Retitle it "Why a real-time OS needs this" and write the three lines from the script (no compiler on the target, the host cannot run QNX binaries, the same Linux-isms). `SLIDE_SECONDS["problem"]` goes from 13 to 11. |
| 3 | `("slide", "why-c")` | **new** | no | New entries in `SLIDES` and `SLIDE_SECONDS` (11 s) with the three lines from the script. zlib 2/2, libsodium 80/80 and sqlite come from `results/ports.csv`. Better to fill them from the CSV in `render.py`, as the results slide does, than to type them. |
| 4 | caption "1/4 A real QNX 8.0 target ..." with `scripts/qemu_target.sh status` and `qnx-porter doctor ...` | exists | **yes** (`status` runs `uname -a` over ssh) | Change only the caption numbering. If an aarch64 target is up, `QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh status` could be added to support "aarch64 on QEMU". This is optional; the line is narration only. |
| (old 2/4) | paho.mqtt.c port plus `head -24 .../patches/0002-*.patch` | **remove** | was yes | Shot 5 replaces it. The scene is also stale: in the current run, `0002` is `link-libsocket`, not the `bool-typedef` patch the old caption describes. |
| 5 | caption "mbedtls: 26 errors, one rule, 130 tests on QNX" | **new** | **yes** (130 tests run on the target) | Commands: `qnx-porter port https://github.com/Mbed-TLS/mbedtls.git --tag v3.6.2 --arg -DENABLE_PROGRAMS=OFF --target {TARGET} --no-model --out {DEMO}`, then `head -4 {DEMO}/mbedtls/patches/*-link-libsocket.patch \| cut -c1-138`. The `--arg` matches `campaign.yaml`; without it the run is not the one in `results/runs/campaign-7.log`. Use a glob on the rule name, not on the patch number. |
| 6 | caption "3/4 json-c ..." with the port, the `crashes.log` grep and `tail -4 tests.log` | exists, changed | **yes** (the tests and the core dump) | Caption renumbered. Drop `tail -4 .../tests.log`, because the port's own output already prints "after crash fixes: 25/25 tests passed". That saves one command's 6 s hold (`HOLD_CMD`). |
| 7 | caption "4/4 The campaign: 10 libraries not on oss.qnx.com ..." with `ports_csv.py` and the `cut ... \| column` table | exists, changed | no (reads `ports/*/report.json`) | The caption is stale: write "61 libraries ...". The table command must include the arch column (`cut -d, -f1,4,5,6,7,8`). Otherwise aarch64 rows, once they exist, are summed into the x86_64 slide. The 62-line table scrolls past on a 33-row screen. That is intended; the website shows it in full. |
| 7 | `("slide", "results")` | exists, **broken** | no | `results_slide()` looks for `tests ran for (\d+): (\d+)/(\d+) passed`, but `scripts/ports_csv.py` now prints `x86_64: 61 libraries, 57 built for QNX 8.0; tests ran for 33 (at least one test each): 1332/1366 passed`. As it stands, `render.py` stops with "results not found in the recording". Fixes: anchor on `x86_64: `, and allow the `(at least one test each)` part. Sum patches only over x86_64 rows. Add a "patches by model: 0" line, from the `patches_by_model` column. Add an aarch64 line that reads "aarch64 on QEMU: campaign running", or that arch's summary line if `ports_csv.py` printed one. |
| 8 | `("slide", "failures")` | exists, **stale** | no | It still says "The 5 tests that still fail (of 381)", from the 10-library run. Rewrite it from `README.md` "What the failures are": QNX libc differences with reproducers in `docs/qnx-reports/`, what the test image lacks, and the 4 that did not build. Give no per-test count. `SLIDE_SECONDS["failures"]` goes from 20 to 10. |
| 9 | caption "Checked against QNX's own hand-made ports" | **new** | no | Commands: `sed -n '/^## Summary/,/^## Library/p' docs/related/qnx-ports-comparison.md \| head -12`, then `ls recipes/build-files/ports \| wc -l`. Use the terminal, not a browser, so that no GitHub logo is on screen. |
| 10 | `("image", "shots/site-*.png")` and caption "Install" with `python3 -m pip index versions qnx-porter` | **new** | no (the pip command needs the internet) | A new scene type: show a still PNG for N seconds. `record.py` writes an `image` marker, and `render.py` scales the PNG to 1920x1080 and holds it. Screenshots of https://thegoodengineers.github.io/qnx-porter/ go in `video/shots/`: `site-overview.png`, `site-results.png`, `site-mbedtls.png` and `site-weekly.png`. Capture them at 1920x1080, page content only, with no browser toolbar, tabs or bookmarks. They are taken by hand, not by `make.sh`. `make.sh` should stop with a clear message if any of them is missing. |
| P1 | caption "Rust crates on QNX 8.0" with `column -s, -t results/crates.csv \| cut -c1-138` | **new, placeholder** | no (reads the committed CSV) | Include it only when `results/crates.csv` exists on the recorded commit; `record.py` checks for the file. It comes from the Rust crate PR (`scripts/run_crates.py`), which is not on main. |
| P2 | caption "The model step, where no rule applies" with `column -s, -t results/model_eval.csv` and `head -4` of one model patch | **new, placeholder** | no (reads committed files) | Include it only when `results/model_eval.csv` exists; `record.py` checks for the file. It comes from the model-step PR (`scripts/model_eval.py`), which is not on main. The patch shown must have `Source:` set to the model and status kept. |
| 11 | `("slide", "close")` | exists, changed | no | New text from the script: the repo, the website, `pip install qnx-porter`, "Every command in this video ran for real on QNX 8.0 in QEMU". The language-model lines move into the narration. `SLIDE_SECONDS["close"]` goes from 12 to 10. |

**Commands that need the QNX target:** shots 4, 5 and 6 only:
- `scripts/qemu_target.sh status`;
- the `qnx-porter port ... --target` runs for mbedtls and json-c (built on the host, tested on the target, and
  json-c's core dump copied back).

Every other scene reads repository files, the network (`pip index`) or the screenshots.

## Changes across `render.py` and `make.sh`
1. **Narration.** The old cut is silent and has no captions. Add a `NARRATION` table, one line per shot, copied
   from the script. Draw it as a caption bar at the bottom of every frame of that shot. If `video/voice.wav`
   exists, mux it in: ffmpeg `-i voice.wav -c:a aac -shortest`. Never add music.
2. **Per-shot timing.** Today, a terminal scene lasts as long as its output plus typing (30 characters a
   second) plus 6 s of hold per command, so the length depends on the run. Give each scene in `SCENES` the
   length the script sets for it. `render.py` then shortens waits (a lower `MAX_GAP`), shortens the hold, and
   types faster until the scene fits. It also prints each scene's length next to its target.
3. **Length guard.** `render.py` must fail if the total reaches 170 s, which keeps a margin under the 3:00 rule.
   It must warn if the total is outside 140-160 s.
4. **Placeholders by file presence.** P1 and P2 go in only when their result CSV is committed. No flag is
   needed, and the script's runtime table says which total to expect.
5. **`make.sh`.** Check that `video/shots/site-*.png` exist before recording. Everything else stays: it sources
   the SDP, checks the target, then runs `record.py` and `render.py`.
6. **`.gitignore`.** Commit `video/shots/*.png` (it ignores only `out/*`), and keep committing the new
   `out/qnx-porter-demo.mp4`, `out/demo.cast` and `out/markers.json`.
