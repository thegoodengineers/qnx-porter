# Abhijeet: model step and demo video

## Rule for everyone: never name the AI tools we used to build this
Do not name any AI assistant or chatbot used to build this project anywhere: commit messages, co-author lines,
code comments, README, docs, Devpost text, screenshots or the video. No `Co-Authored-By` lines.
The product's own optional model step ("a language model proposes a diff") is fine to describe.
Before you push: `git log --format=%B | grep -i co-authored` must print nothing.
Never report a number that `scripts/ports_csv.py` or a `report.json` did not produce.
Branch: `<name>/<task>`, pull request into `main`. Run `python3 -m pytest -q` before every push.
Deadline: Devpost **16 Dec 2026, 12:30 AM IST**. Code freeze **14 Dec, 9:00 PM IST**.

## 1. Turn the model step on and measure it (after Chirag's first batch, by 30 Nov)
- Set `QNX_PORTER_API_KEY`, `QNX_PORTER_MODEL` and `QNX_PORTER_BASE_URL` in your own
  shell only. Never commit them.
- Re-run the libraries that ended `failed` with rules only. For each model patch: is it right? Count
  kept / reverted / wrong-but-kept, and write the counts in your PR.
- Tighten `SYSTEM` in `qnx_porter/llm.py` if it guesses.

## 2. Demo video (record by 10 Dec, upload by 13 Dec)
- Script: docs/VIDEO_SCRIPT.md. Under 3:00, public on YouTube, no copyrighted music.
- Numbers on screen only from `results/ports.csv`. Keep the raw unedited port run as the source file.
