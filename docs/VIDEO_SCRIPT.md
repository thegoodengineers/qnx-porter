# Demo video: shot list

**Runtime:** 2:47 (167 s) with every shot, recorded 14 Nov 2026. Shots 7 (hang diagnosis, 11 s), 11 (Rust crates,
6 s) and 12 (model step, 7 s) go in only when their source is committed (`ports/nng/REPORT.md` with a "Hang on QNX"
section, `results/crates.csv`, `results/model_eval.csv`); all three are on main. `video/render.py` fails at 170 s
and warns outside 140-168 s.

Rules (Devpost, checked 8 Nov 2026):
- under 3 minutes;
- public on YouTube;
- shows the project working on the device it targets (QNX 8.0);
- no third-party trademarks or copyrighted music without permission.

What that means for this video:
- No music. The only sound is the narration below, recorded in our own voice as `video/voice.wav`. The same
  lines are burned in as captions, so the video also works without the voice.
- No logos of any kind, ours or anyone else's. Library and language names appear only as plain text, to say
  what was ported. The comparison with QNX's own ports is shown in the terminal, not on GitHub.
- We say "aarch64 on QEMU", never a board or hardware name. Every target in this video is QEMU.

How it is made: terminal shots are run for real by `video/make.sh` against the QNX 8.0 QEMU target. Waits are
shortened, and the screen says by how much. The website shots are screenshots of the live site in
`video/shots/`. How `make.sh` works: [video/README.md](../video/README.md).

**Numbers rule.** Every number spoken or shown is listed in its shot's "Source" column. `video/render.py` does
not type any of them: it reads them from the recording or from the result file named there, at render time, and
fills the captions and slides with them. The narration below shows the values on the current commit. If a
re-record changes a number, `render.py` prints the new narration lines; read those into `voice.wav`. Never
round, and never use a number that no file prints.

The narration runs at about 2.4 words a second. Long numbers count as two or three words. `render.py` prints the
words per second of each shot.

## Shots

| # | Time | On screen | Narration | Source of every number |
|---|---|---|---|---|
| 1 | 0:00-0:07 (7 s) | Title slide: "qnx-porter". One line: "Ports open-source C/C++ libraries to QNX 8.0 and proves each port with the library's own tests on QNX." Then "The Good Engineers · QNX Global Hackathon 2026 · Developer Tooling & Host Tools". | "qnx-porter ports open-source C and C++ libraries to QNX 8.0, and proves each port on QNX itself." | 8.0: the `target` column of `results/ports.csv` (`QNX qnx-porter 8.0.0 ...`) |
| 2 | 0:07-0:16 (9 s) | Slide "Why a real-time OS needs this", three lines: no compiler on the target; the host cannot run QNX binaries; the same Linux-isms break library after library. | "A QNX target has no compiler, and the host can't run QNX binaries. Only tests on the target prove a port." | none |
| 3 | 0:16-0:25 (9 s) | Slide "Why C and C++". Line 1: "QNX itself is built for C and C++." Line 2: "Other languages wrap C libraries: Python's zlib module, PyNaCl on libsodium, Rust's rusqlite on SQLite." Line 3, filled from `results/ports.csv`: "On QNX 8.0: zlib 2/2 tests pass, libsodium 80/80 tests pass, sqlite built (its test suite needs Tcl on the target)." | "QNX is built for C and C++, and other languages wrap C libraries. Port the C layer, and the rest can follow." | shown only: zlib 2/2, libsodium 80/80, sqlite built: `results/ports.csv` (x86_64 rows zlib, libsodium, sqlite), read by `render.py`; the wrapper facts: `README.md` "Why C and C++" |
| 4 | 0:25-0:35 (10 s) | Terminal. `scripts/qemu_target.sh status` prints the QNX 8.0 `uname -a` from the QEMU target. `qnx-porter doctor` prints its ok lines (qcc, qcc targets, SDP complete, qcc builds hello). | "A real QNX 8.0 target, x86_64 in QEMU, and the SDP 8.0 toolchain. The campaign also ran on aarch64 on QEMU." | 8.0: the `uname` output on screen, and the `target` column of `results/ports.csv`; SDP 8.0: `README.md` "Results on QNX 8.0"; the aarch64 sentence: the `aarch64le:` line `scripts/ports_csv.py` prints in shot 7 (without it, `render.py` says "An aarch64 campaign on QEMU is running.") |
| 5 | 0:35-0:57 (22 s) | Terminal, the real port, at the pin of `campaign.yaml`: `qnx-porter port https://github.com/Mbed-TLS/mbedtls.git --tag v4.2.0 --target root@172.31.1.11 --no-model --out /tmp/qnx-porter-demo`. On screen: "round 1: 26 error(s); first: ... undefined reference to `__inet_pton`", then "fix 0001 [link-libsocket] ...", "build OK after 2 round(s)", "148/148 tests passed". Then `head -4` of the patch: Subject, "Source: deterministic rule", Reason, Error. | "A real port: mbedtls. Round 1: 26 errors. QNX keeps inet_pton in libsocket, not libc, so a documented rule adds it. Round 2 builds, and mbedtls's own tests run on QNX: 148 of 148 pass. Each change is a patch with its rule, its reason and the exact error." | 26, 2, 148 of 148: read by `render.py` from this shot's recorded output (`round 1: N error`, `build OK after N round`, `N/N tests passed`); the campaign run of the same pin: `results/runs/campaign-8.log` and `results/ports.csv` row mbedtls; the patch: `ports/mbedtls/patches/`. The port is written under `/tmp`, the case fixed in #59 (`results/runs/mbedtls-tmp-path.log`). |
| 6 | 0:57-1:14 (17 s) | Terminal, crash triage. `qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.19-20260627 --target root@172.31.1.11 --no-model --out /tmp/qnx-porter-demo`: "27/28 tests passed", "fix 0001 [printf-null] Crash on QNX: printf() ...", "after crash fixes: 28/28 tests passed". Then the backtrace from the QNX core dump (`#0 strlen` ... `#4`) from `logs/crashes.log`. | "When a test crashes on QNX, qnx-porter copies the core dump back and reads the backtrace. json-c passes NULL to printf: glibc prints (null), QNX faults. A rule fixes the test, and json-c goes from 27 to 28 of 28." | 27, 28 of 28: read by `render.py` from this shot's recorded output (`N/N tests passed`, `after crash fixes: N/N tests passed`); the campaign run: `results/ports.csv` row json-c; backtrace: `ports/json-c/logs/crashes.log` |
| 7 | 1:14-1:25 (11 s). **Only if `ports/nng/REPORT.md` has a "Hang on QNX" section** (it has). | Terminal: the first "Hang on QNX" section of `ports/nng/REPORT.md`: `pidin` of `nng.core.aio_test` (main thread `CONDVAR`, thread 2 `RUNNING` in `msg_sendv`), "killed on the target after 60 s", then the kernel-trace line (thread 2: 93655 runs, 185539 kernel calls, `MSG_SENDV` first). Then the nng pull request URL from `upstream/outbox/README.md`. | "When a test hangs, pidin and a kernel trace show why: in nng, one thread spins, as QNX sends no POLLHUP. We sent nng the fix." | none spoken; on screen: `ports/nng/REPORT.md` (the committed run, `docs/ON_TARGET_DIAGNOSIS.md`); the PR: `upstream/outbox/README.md` (open, under review) |
| 8 | 1:25-1:43 (18 s: 9 s terminal, 9 s slide) | Terminal: `python3 scripts/ports_csv.py` prints one summary line per arch. Then the per-library table (library, arch, build, tests passed, tests total, patches, by rule, by model) scrolls past. Then the "Results on QNX 8.0" slide, with numbers parsed from that output: x86_64 built, tests, patches by rule and by model; then "aarch64 on QEMU: 58 of 61 built; 1546 of 1642 tests passed; 32 patches, 0 by a language model." | "The campaign: 61 libraries. On x86_64, 58 built for QNX 8.0, and 1563 of 1658 of their own tests passed on the target. On aarch64 on QEMU, 58 built. All 31 patches came from rules." | 61, 58, 1563/1658, and the aarch64 numbers: the `x86_64:` and `aarch64le:` lines `scripts/ports_csv.py` prints in this recording (also the `README.md` headline); 31 patches, 31 by rules, 0 by the model: the sums of the `patches`, `patches_by_rule` and `patches_by_model` columns over the x86_64 rows of the recorded table (`results/ports.csv`). `render.py` stops if the table's row count disagrees with the summary line. |
| 9 | 1:43-1:52 (9 s) | Slide "What still fails, by cause": QNX libc differences (`strtod()` rounding, `strftime()` `%Ex`, `fchdir()` needs `O_DIRECTORY`, `qsort()` with an inconsistent comparator), each with a reproducer in `docs/qnx-reports/`; what the test image lacks (`killall`, internet, Tcl, an MQTT broker); "Did not build with rules only: libwebsockets (errors no rule covers yet). Need a QNX equivalent: can-utils and libgpiod use Linux-only kernel interfaces; the porting advisor names QNX's equivalent for each." | "Every failing test is listed by cause: QNX libc differences such as strtod rounding, with reproducers, and things our test image lacks." | shown only: the names: `results/ports.csv` (x86_64 rows with `build_result` failed or needs-qnx-equivalent), read by `render.py`; the causes: `README.md` "What the failures are" |
| 10 | 1:52-2:03 (11 s) | Terminal (not the GitHub page, so that no third-party logo is on screen). The Summary of `docs/related/qnx-ports-comparison.md`, printed with `sed`. Then `ls recipes/build-files/ports \| wc -l` prints 34. | "21 of our libraries also have a hand-made QNX port; in 6, we found the same change independently. For 34 CMake ports they lack, we generate recipes." | 21, 6 and 34: read by `render.py` from this shot's recorded output ("Of the 21 libraries", the "found independently" row's count, the `wc -l` output); the files: `docs/related/qnx-ports-comparison.md` and the 34 folders in `recipes/build-files/ports/` |
| 11 | 2:03-2:09 (6 s). **Only if `results/crates.csv` is committed** (it is). | Terminal: `cut -d, -f1,2,3,5,6,7 results/crates.csv \| column -s, -t`: crate, version, arch, build result, tests passed, tests total. | "The same tool ports Rust crates: 21 of 22 build for QNX 8.0." | 21 of 22: the x86_64 rows of `results/crates.csv` (`build_result` = built), read by `render.py`; written by `scripts/run_crates.py`. `README.md` "Rust crates on QNX 8.0" gives the same for x86_64 and aarch64 on QEMU. |
| 12 | 2:09-2:16 (7 s). **Only if `results/model_eval.csv` is committed** (it is). | Terminal: `cut -d, -f1-7 results/model_eval.csv \| column -s, -t` (rules-only build and tests next to rules+model build and tests, model patches kept and reverted). Then `head -3` of `ports-model/libuv/patches/0001-model-fix-qnx-c.patch`: Subject, "Source: language model, checked by rebuilding", Reason. | "Where no rule applied, the model step built libuv and libwebsockets, each diff proved by a rebuild." | libuv and libwebsockets: the rows of `results/model_eval.csv` with `rules_only_build` = failed and `rules_model_build` = built, read by `render.py`; written by `scripts/model_eval.py`; the patch: `ports-model/libuv/patches/` (kept). The table on screen also shows libuv's tests (0/2); the narration claims only the build. |
| 13 | 2:16-2:23 (7 s) | Terminal: the latency table of `docs/RT_RESULTS.md` (p99 idle, loaded, loaded and isolated with runmask, per library), printed with `sed`. Caption: "... on QNX 8.0 in QEMU (compares libraries; not a hardware figure)". | "Real-time check: the latency of one call in 14 libraries on QNX in QEMU, idle, loaded and isolated." | 14: read by `render.py` from the recorded heading "(14 libraries measured)" of `docs/RT_RESULTS.md`, written by `scripts/rt_md.py` from `results/rt.csv`. No latency value is spoken: they are QEMU timings (see "Read this first" in that file). |
| 14 | 2:23-2:32 (9 s: three screenshots of 2 s, then 3 s of terminal) | Screenshots of https://thegoodengineers.github.io/qnx-porter/: Overview (`site-overview.png`), Results (`site-results.png`), Weekly check (`site-weekly.png`). Then a terminal, caption "Install": `python3 -m pip index versions qnx-porter`. | "Everything is on the website, generated from the same reports, with a weekly check against upstream. Install with pip install qnx-porter." | shown only: the version PyPI answers on screen; the website's numbers: `site/build.py` reads them from `ports/*/report.json` and `results/*.csv`. Do not say a weekly-check number. |
| 15 | 2:32-2:37 (5 s) | Screenshot of the paper page, https://thegoodengineers.github.io/qnx-porter/paper.html (`site-paper.png`): its title and abstract. | "The method and every result are written up in a research paper." | none spoken; the paper's numbers are generated from the result files (`paper/build.py`) |
| 16 | 2:37-2:47 (10 s) | Close slide: `github.com/thegoodengineers/qnx-porter`, "Apache-2.0 · pip install qnx-porter · thegoodengineers.github.io/qnx-porter", "Every command in this video ran for real on QNX 8.0 in QEMU; video/make.sh re-records it." | "Rules first; a language model only where no rule fits, kept only if the rebuild proves it. Every command here ran on QNX 8.0." | 8.0: as in shot 1; the keep-or-revert rule: `README.md` "The model is optional and checked" |

Totals: 7+9+9+10+22+17+11+18+9+11+6+7+7+9+5+10 = 167 s (2:47). The lengths live in `video/record.py`
(`scenes()`), and `video/render.py` fits each scene to its length and prints the table.

## Judging criteria, where each is shown
- **Technological implementation:** shots 4-8 and 13. A real QNX 8.0 target, the qcc toolchain, rule patches,
  the tests run on the target, core-dump triage, hang diagnosis with `pidin` and `tracelogger`, and latency
  measured on QNX.
- **Design (a complete product):** shots 10, 14-16. Recipes in QNX's own layout, the website, the pip package,
  the weekly upstream check and the paper.
- **Potential impact:** shots 2-3, 7 and 11. Why an RTOS needs this, why the C layer matters, a fix sent
  upstream, and the same tool on Rust crates.
- **Innovation and AI creativity:** shots 5-7 (evidence-driven rules, crash triage from a core dump, hang diagnosis
  from a kernel trace), 12 (the model step, kept only when the rebuild proves it) and 16.

## Before recording
- `git log -1` on main. Shots 7, 11 and 12 go in by themselves when their sources are committed.
- Check that `video/shots/site-*.png` show the current site (see [video/README.md](../video/README.md)).
- Re-record the terminal shots on the QNX target with `video/make.sh`. `render.py` then prints each scene's
  length and every narration line with the numbers from that recording. Record `voice.wav` from those lines.

## For the upload
- Title: "qnx-porter: porting open-source C/C++ libraries to QNX 8.0, proved on a QNX target".
- Description: the repo URL, the website URL, and that every command in the video ran for real against QNX 8.0
  in QEMU (`video/make.sh`).
- Check that the video is under 3:00, has no music, shows no logos, and is **public** before pasting the link
  into Devpost.
