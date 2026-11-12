# Demo video

The video is generated, not edited by hand: `video/make.sh` runs every command for real on the build host
against the QNX 8.0 QEMU target (`video/record.py`, saved as `video/out/demo.cast`, playable with
`asciinema play`) and renders it with the slides into `video/out/qnx-porter-demo.mp4` (`video/render.py`).
The only change to the recording is timing: pauses over 1 s while a command runs are shortened, and the
screen says how much real time was skipped. The results slide takes its numbers from the recorded
`scripts/ports_csv.py` output.

Rules (Devpost, checked 8 Nov 2026): under 3 minutes, public on YouTube, shows the project working on the
device it targets, no third-party trademarks or copyrighted music. The video has no audio.

## Sections
| # | Section | What is on screen |
|---|---|---|
| 1 | Title | qnx-porter, one-line pitch, team and category |
| 2 | Why | the porting problem and the approach |
| 3 | 1/4 Target and toolchain | `scripts/qemu_target.sh status` (QNX 8.0 `uname` from the QEMU target), `qnx-porter doctor` (SDP 8.0, qcc, compile check) |
| 4 | 2/4 paho.mqtt.c | live port: four rounds, four rule fixes (`stub-lib`, `bool-typedef`, `link-libsocket`, `endian-netbyte`), build OK; then the `bool-typedef` patch file with its reason and diff |
| 5 | 3/4 json-c | live port with tests on the QNX target: 24/25, crash triage, `printf-null` fix, 25/25; the backtrace from the QNX core dump; the end of `tests.log` |
| 6 | 4/4 Campaign | `scripts/ports_csv.py` summary line and the per-library table from `results/ports.csv` |
| 7 | Results | built / tests passed / patches, parsed from section 6's output |
| 8 | Open failures | the 5 failing tests and the 2 libraries whose tests were not run, with causes |
| 9 | Close | repo URL, licence, setup and codelab, the optional language-model step described generically |

## Re-record
```bash
sudo apt install ffmpeg python3-pil        # once
scripts/qemu_target.sh start               # the QNX 8.0 target
video/make.sh                              # about 8 minutes: 1.5 recording, the rest rendering
```

## For the upload
- Title: "qnx-porter: porting open-source C libraries to QNX 8.0, proved on a QNX target".
- Description: the repo URL, and that every command in the video ran for real (`video/make.sh`).
- Check the length is under 3:00 and the video is public before pasting the link into Devpost.
