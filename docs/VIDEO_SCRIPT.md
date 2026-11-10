# Demo video script (target 2:40, hard limit under 3:00)

Rules: show QNX running (the QEMU target's `uname -a` on screen). Every number on screen comes from
`results/ports.csv` or a report.json. No third-party music. Screen recordings at 1920x1080, terminal font 18 pt.

| # | Time | On screen | Narration (about 380 words in total) |
|---|---|---|---|
| 1 | 0:00-0:15 | oss.qnx.com package list, then a terminal with a red qcc error | "QNX 8.0 is free for developers now, but most open-source C libraries have never been built for it. Porting one means hours of the same fixes. We built a tool that does that part." |
| 2 | 0:15-0:25 | Title card: **qnx-porter**, one line under it | "qnx-porter: point it at a library, it builds it for QNX 8.0, fixes what breaks, and proves the port with the library's own tests." |
| 3 | 0:25-0:40 | Terminal: `ssh root@172.31.1.11 uname -a` showing QNX 8.0.0 x86_64; `qnx-porter doctor` all ok | "This is QNX 8.0 running in QEMU, built with QNX's mkqnximage. The SDP is installed and checked." |
| 4 | 0:40-1:20 | `qnx-porter port <library> --tag ... --target root@172.31.1.11` live (speed up waits 4x, say so on screen). Highlight the round lines and fix lines | "It detects the build system, writes a QNX toolchain file for qcc, and builds. Round one fails: a missing header that glibc includes implicitly and QNX does not. A rule adds it, and says why. Sockets live in libsocket on QNX, so it links that. Each fix is a patch file with its reason." |
| 5 | 1:20-1:45 | The model step: error no rule handles, the diff, the rebuild; a reverted patch in REPORT.md | "When no rule fits, an optional model proposes a diff. We never trust it: it must apply cleanly, and if the rebuild still fails on that error, the agent reverts it and says so." |
| 6 | 1:45-2:05 | Test phase: ctest output streaming, then `N/N tests passed` with the target's uname | "A build is not a port. The library's own tests run on the QNX target, each binary copied and executed over ssh." |
| 7 | 2:05-2:25 | `results/ports.csv` rendered as the README table | "Across [N] libraries that were not on QNX's ports site: [built] built, [passed] of [total] tests passed on QNX 8.0, [rule] fixes by rules, [model] by the model." (read the numbers from the CSV on the day) |
| 8 | 2:25-2:40 | REPORT.md of one port, then repo URL and the codelab | "Every change is reviewable, ready to offer upstream. The code, the ports and a step-by-step codelab are open source at github.com/thegoodengineers/qnx-porter." |

## Shots only a person can record
- The QNX Software Center with SDP 8.0 installed (no licence key visible).
- QEMU booting QNX 8.0 (`mkqnximage --run`) and the `uname -a` over ssh.
- One full `qnx-porter port` run on a real library, unedited, kept as the raw source file.

## Checklist before upload
- Under 3:00. Public on YouTube. Title: "qnx-porter: porting open-source C libraries to QNX 8.0, automatically".
- No logos or trademarks other than what appears in QNX's own tools; no copyrighted music.
- Numbers on screen match `results/ports.csv` at the commit in the description.
