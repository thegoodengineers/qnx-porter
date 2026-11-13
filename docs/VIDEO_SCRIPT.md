# Demo video: shot list

**Runtime:** 2:26 for the base cut. Each placeholder that is merged by recording time adds its time: Rust crates
+0:06, model step +0:07. With both, the cut is 2:39. Every version stays under the 3:00 limit.

Rules (Devpost, checked 8 Nov 2026):
- under 3 minutes;
- public on YouTube;
- shows the project working on the device it targets (QNX 8.0);
- no third-party trademarks or copyrighted music without permission.

What that means for this video:
- No music. The only sound is the narration below, recorded in our own voice. The same lines are burned in as
  captions.
- No logos of any kind, ours or anyone else's. Library and language names appear only as plain text, to say
  what was ported.
- We say "aarch64 on QEMU", never a board or hardware name. Every target in this video is QEMU.

How it is made: terminal shots are run for real by `video/make.sh` against the QNX 8.0 QEMU target. Waits are
shortened, and the screen says by how much. The website shots are screenshots of the live site. What
`make.sh` must change to produce this cut: [video/README.md](../video/README.md).

**Numbers rule.** Every number spoken or shown is listed in its shot's "Source" column. If a re-record or a
new campaign changes a number, the narration takes the new value from that file. Never round, and never use a
number that no file prints.

The narration runs at about 2.4 words a second. Long numbers count as two or three words.

## Shots

| # | Time | On screen | Narration | Source of every number |
|---|---|---|---|---|
| 1 | 0:00-0:07 (7 s) | Title slide: "qnx-porter". One line: "Ports open-source C/C++ libraries to QNX 8.0 and proves each port with the library's own tests on QNX." Then "The Good Engineers · QNX Global Hackathon 2026 · Developer Tooling & Host Tools". | "qnx-porter ports open-source C and C++ libraries to QNX 8.0, and proves each port on QNX itself." | 8.0: the `target` column of `results/ports.csv` (`QNX qnx-porter 8.0.0 ...`) |
| 2 | 0:07-0:18 (11 s) | Slide "Why a real-time OS needs this", three lines: no compiler on the target; the host cannot run QNX binaries; the same Linux-isms break library after library. | "A QNX target has no compiler, and the build machine can't run QNX binaries. Every library is cross-compiled with qcc, and only tests on the target prove it." | none |
| 3 | 0:18-0:29 (11 s) | Slide "Why C and C++". Line 1: "QNX itself is built for C and C++." Line 2: "Other languages wrap C libraries: Python's zlib module, PyNaCl on libsodium, Rust's rusqlite on SQLite." Line 3: "On QNX 8.0: zlib 2/2 tests, libsodium 80/80; sqlite built." | "Why C and C++? QNX is built for C and C++, and other languages wrap C libraries. Port the C layer, and the rest can follow." | shown only: zlib 2/2, libsodium 80/80, sqlite built: `results/ports.csv` (rows zlib, libsodium, sqlite); the wrapper facts: `README.md` "Why C and C++" |
| 4 | 0:29-0:41 (12 s) | Terminal. `scripts/qemu_target.sh status` prints the QNX 8.0 `uname -a` from the QEMU target. `qnx-porter doctor` prints its ok lines (qcc, qcc targets, SDP complete, qcc builds hello). | "This is a real QNX 8.0 target, x86_64 in QEMU, and the SDP 8.0 toolchain, checked by qnx-porter doctor. An aarch64 campaign on QEMU is also running." | 8.0: the `uname` output on screen, and the `target` column of `results/ports.csv`; SDP 8.0: `README.md` "Results on QNX 8.0". Before recording, check the aarch64 line is still true. If aarch64 rows are in `results/ports.csv` by then, say "and an aarch64 campaign on QEMU" without "running", and give its numbers in shot 7. |
| 5 | 0:41-1:05 (24 s) | Terminal, the real port. `qnx-porter port https://github.com/Mbed-TLS/mbedtls.git --tag v3.6.2 --arg -DENABLE_PROGRAMS=OFF --target root@172.31.1.11 --no-model`. On screen: "round 1: 26 error(s); first: ... undefined reference to `__inet_pton'", then "fix 0001 [link-libsocket] ...", "build OK after 2 round(s)", "130/130 tests passed". Then `head -4` of the patch: Subject, "Source: deterministic rule", Reason, Error. | "Now a real port: mbedtls, straight from upstream. Round one: 26 errors. QNX keeps inet_pton in libsocket, not libc, so a documented rule adds it. Round two builds. Then mbedtls's own tests run on the QNX target: 130 of 130 pass. Every change is a patch file with its rule, its reason and the exact error." | 26 errors, 2 rounds, 130/130: `results/runs/campaign-7.log` (the `[5/61] mbedtls` block); 130/130 and 1 patch: `results/ports.csv` row mbedtls; the patch: `ports/mbedtls/patches/0001-link-libsocket.patch`. Read the numbers off the new recording; if they differ, say the recorded ones. |
| 6 | 1:05-1:24 (19 s) | Terminal, crash triage. `qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11 --no-model`: "24/25 tests passed", "fix 0001 [printf-null] Crash on QNX: printf() at tests/test_json_patch.c:31 ...", "after crash fixes: 25/25 tests passed". Then the backtrace from the QNX core dump (`#0 strlen` ... `#4 test_json_patch_op`) from `logs/crashes.log`. | "When a test crashes on QNX, qnx-porter copies the core dump back and reads it with the SDP's debugger. json-c's test passes NULL to printf's percent-s: glibc prints (null), QNX's libc faults. A rule fixes the test, and json-c goes from 24 to 25 of 25." | 24/25 and 25/25: `results/runs/campaign-5.log` (the json-c block); 25/25: `results/ports.csv` row json-c; backtrace: `ports/json-c/logs/crashes.log` |
| 7 | 1:24-1:41 (17 s) | Terminal: `python3 scripts/ports_csv.py` prints the summary line. Then the per-library table (library, build, tests passed, tests total, patches) scrolls past. Then the "Results on QNX 8.0" slide, with numbers parsed from that output. A last slide line reads "aarch64 on QEMU: campaign running", or its numbers if they are in `results/ports.csv`. | "The campaign: 61 libraries. 57 built for QNX 8.0, and 1332 of 1366 of their own tests passed on the target. All 25 patches came from rules; no language model was used." | 61, 57, 1332/1366: the last line of `results/runs/campaign-7.log`, the `README.md` headline, and the summary line `scripts/ports_csv.py` prints in this recording; 25 patches, 25 by rules: the `README.md` headline (sum of `patches` and `patches_by_rule` in `results/ports.csv`, x86_64 rows); "no language model": `README.md` "Results on QNX 8.0" ("Rules only, no language model") and the `patches_by_model` column (all 0) |
| 8 | 1:41-1:51 (10 s) | Slide "What still fails, by cause": QNX libc differences (`strtod()` rounding, `strftime()` `%Ex`, `fchdir()` needs `O_DIRECTORY`, `qsort()` with an inconsistent comparator), each with a reproducer in `docs/qnx-reports/`; what the test image lacks (`killall`, internet, Tcl, an MQTT broker); 4 libraries that did not build, 2 of them Linux-only by design. | "Every failing test is listed by cause: QNX libc differences such as strtod rounding, with reproducers, and things our test image lacks." | shown only: 4 did not build, 2 Linux-only: `README.md` "What the failures are" ("Did not build (4)": libgpiod, can-utils) and `results/ports.csv` (`build_result` = failed) |
| 9 | 1:51-2:03 (12 s) | Terminal (not the GitHub page, so that no third-party logo is on screen). The Summary table of `docs/related/qnx-ports-comparison.md`, printed with `sed`. Then `ls recipes/build-files/ports \| wc -l` prints 34. | "QNX maintains hand-made ports. 21 of our libraries have one; in 6, we found the same QNX change independently. For the 34 CMake ports they lack, we generate build-files recipes." | 21 and 6: `docs/related/qnx-ports-comparison.md` (opening paragraph; Summary table, first row); 34: `README.md` "Related work: QNX's own ports" and the 34 folders in `recipes/build-files/ports/` |
| 10 | 2:03-2:16 (13 s) | Screenshots of https://thegoodengineers.github.io/qnx-porter/: Overview, Results (the table), the mbedtls port page, Weekly check. Then a terminal: `python3 -m pip index versions qnx-porter` prints `qnx-porter (0.1.0)`. | "Everything is on the website, generated from the same reports: every port, every rule, a codelab, and a weekly check that re-ports each library at upstream HEAD. Install with pip install qnx-porter." | shown only: 0.1.0: `qnx_porter/__init__.py` (`__version__`) and PyPI's answer on screen; the website's numbers: `site/build.py` reads them from `ports/*/report.json` and `results/*.csv`. Do not say a weekly-check number: `results/head/history.csv` (branch `data/head-history`) has only one run so far. |
| P1 | +6 s, after shot 10. **Only if the Rust crate work is merged by recording time.** | Terminal: the crate results table (`results/crates.csv`: crate, build result, tests). | "The same tool now ports Rust crates: 21 of 22 build for QNX 8.0." | `results/crates.csv`, written by `scripts/run_crates.py` (Rust crate PR, not on main yet). Say 21 of 22 only if that file says so at recording. Otherwise give its own numbers, or cut the shot. |
| P2 | +7 s, after P1 (or after shot 10). **Only if the model step results are merged by recording time.** | Terminal: `results/model_eval.csv` (rules-only result next to rules+model result, patches kept and reverted). Then the head of one model patch, showing its source and reason. | "Where no rule applied, the model step built libuv and libwebsockets, each diff proved by a rebuild." | `results/model_eval.csv`, written by `scripts/model_eval.py` (model-step PR, not on main yet). Say it only if that file shows both libraries as built with the model step. Otherwise name only the ones it shows, or cut the shot. |
| 11 | 2:16-2:26 (10 s); 2:29-2:39 with P1 and P2 | Close slide: `github.com/thegoodengineers/qnx-porter`, "Apache-2.0 · pip install qnx-porter · thegoodengineers.github.io/qnx-porter", "Every command in this video ran for real on QNX 8.0 in QEMU; video/make.sh re-records it." | "Rules first. A language model only where no rule fits, and reverted unless the rebuild proves it. Every command here ran on QNX 8.0." | 8.0: as in shot 1; the revert rule: `README.md` "The model is optional and checked" |

Totals: the base cut is 7+11+11+12+24+19+17+10+12+13+10 = 146 s (2:26). With P1 it is 152 s (2:32). With P2 only
it is 153 s (2:33). With both it is 159 s (2:39).

## Judging criteria, where each is shown
- **Technological implementation:** shots 4-7. A real QNX 8.0 target, the qcc toolchain, rule patches,
  the tests run on the target and core-dump triage.
- **Design (a complete product):** shots 9-10 and 11. Recipes in QNX's own layout, the website, the pip
  package and the weekly upstream check.
- **Potential impact:** shots 2-3. Why an RTOS needs this, and why the C layer matters.
- **Innovation and AI creativity:** shots 5-6 (evidence-driven rules, crash triage from a core dump), P2 if
  merged, and shot 11 (the model step is checked and reverted unless it proves itself).

## Before recording
- `git log -1` on main: P1 and P2 go in only if their PRs are merged. Otherwise cut them. The base cut is 2:26.
- Re-read every number in the narration against its Source file on that commit.
- Re-record the terminal shots on the QNX target (see [video/README.md](../video/README.md)), then read
  shots 5-7's numbers off the new recording.

## For the upload
- Title: "qnx-porter: porting open-source C/C++ libraries to QNX 8.0, proved on a QNX target".
- Description: the repo URL, the website URL, and that every command in the video ran for real against QNX 8.0
  in QEMU (`video/make.sh`).
- Check that the video is under 3:00, has no music, shows no logos, and is **public** before pasting the link
  into Devpost.
