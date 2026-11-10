# Bhumika: codelab ($3,500 Best Codelab / Tutorial prize)

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines.
The product's own optional model step ("a language model proposes a diff") is fine to describe.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Never report a number that `scripts/ports_csv.py` or a `report.json` did not produce.
Branch: `<name>/<task>`, pull request into `main`. Run `python3 -m pytest -q` before every push.
Deadline: Devpost **16 Dec 2026, 12:30 AM IST**. Code freeze **14 Dec, 9:00 PM IST**.

## 1. Walk the codelab as a newcomer (once Chirag's SDP works, by 20 Nov)
- Follow docs/CODELAB.md exactly on a clean WSL or Ubuntu machine. Time each step.
- Every place you got stuck: fix the text, not your machine. Put real times in the step headings.
- Done when: a teammate who has never used QNX finishes it without asking anyone.

## 2. Screenshots for the codelab (by 25 Nov)
- `qnx-porter doctor`, a port run, REPORT.md, one patch file, the tests.log on QNX. Save in `docs/img/`
  (no licence key, no email address visible), and reference them in docs/CODELAB.md.

## 3. Publish it (by 1 Dec)
- Decide with Chirag: keep it in the repo, or also publish as a page (GitHub Pages from `docs/`). The
  Devpost bonus field needs one public URL.
