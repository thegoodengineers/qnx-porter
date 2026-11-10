# Ayush: rules from real errors, more build systems

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines.
The product's own optional model step ("a language model proposes a diff") is fine to describe.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Never report a number that `scripts/ports_csv.py` or a `report.json` did not produce.
Branch: `<name>/<task>`, pull request into `main`. Run `python3 -m pytest -q` before every push.
Deadline: Devpost **16 Dec 2026, 12:30 AM IST**. Code freeze **14 Dec, 9:00 PM IST**.

## 1. Grow the rules from the batch logs (after Chirag's first batch, by 30 Nov)
- Read `ports/*/logs/round-*.log` and `blocked_on` in each `report.json`. Which errors repeat across
  libraries and are always fixed the same way? Each one becomes a rule in `qnx_porter/fixes.py`, with a
  test in `tests/test_fixes_and_patches.py` that uses the real error line.
- Never add a rule that needs judgement; those stay with the model.
- Done when: re-running the batch has fewer model patches and no fewer passing tests.

## 2. aarch64 (by 8 Dec, only if a Raspberry Pi 5 with QNX 8.0 is available)
- `qnx-porter port ... --arch aarch64le --target root@<pi-ip>` on two libraries that passed on x86_64.
