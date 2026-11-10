# Chirag: lead, QNX SDP, first ports, final submission

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines.
The product's own optional model step ("a language model proposes a diff") is fine to describe.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Never report a number that `scripts/ports_csv.py` or a `report.json` did not produce.
Branch: `<name>/<task>`, pull request into `main`. Run `python3 -m pytest -q` before every push.
Deadline: Devpost **16 Dec 2026, 12:30 AM IST**. Code freeze **14 Dec, 9:00 PM IST**.

## 1. Install QNX SDP 8.0 and the QEMU target (by 12 Nov)
- Follow SETUP.md steps 1-4 in WSL Ubuntu 22.04 (already on your laptop). Only you can create the myQNX
  account and accept the licence; never paste the licence key or password anywhere.
- Done when: `qnx-porter doctor` prints only `ok` lines and `ssh root@172.31.1.11 uname -a` shows QNX 8.0.0.
- If a [To verify] item in docs/LEARNINGS.md is wrong, fix `qnx_porter/qnx.py` or `target.py`, add a test, log it.

## 2. First real port by the agent, checked by hand (by 14 Nov)
- `qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11 --no-model`
- Read every patch in `ports/json-c/patches/`. Is each one right? Write what you found in docs/LEARNINGS.md.
- Commit `ports/json-c/` (not `work/`; it is ignored).

## 3. Batch run and results (by 5 Dec)
- `qnx-porter batch candidates.json --target root@172.31.1.11`, then `python3 scripts/ports_csv.py`.
- Commit `ports/`, `results/ports.csv` and the README table it rewrites. CI fails if they disagree.

## 4. Submit (by 15 Dec, 9:00 PM IST)
- Fill docs/DEVPOST.md numbers from the script output; paste into the Devpost draft; category Developer
  Tooling & Host Tools; codelab URL in the bonus field; video link.
