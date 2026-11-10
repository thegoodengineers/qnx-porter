"""The long tail: errors no rule handles go to a language model, which must answer with a small diff.

Configuration comes only from the environment:
  QNX_PORTER_API_KEY   key for an OpenAI-compatible chat-completions endpoint
  QNX_PORTER_MODEL     model ID
  QNX_PORTER_BASE_URL  endpoint base (default https://api.openai.com/v1; any compatible server works)
The model's diff is never trusted: it must pass `git apply --check`, and the agent keeps it only if the
rebuild clears the error it was meant to fix without adding new ones.
"""
import json
import os
import re
import urllib.request
from pathlib import Path

from .errors import Diagnostic

SYSTEM = """You port C and C++ libraries to QNX Neutrino 8.0 (SDP 8.0, compiler qcc = GCC 12, POSIX libc).
Facts about QNX 8.0 that matter when porting from Linux:
- __QNX__ and __QNXNTO__ are defined. There is no __linux__.
- Sockets are in libsocket (-lsocket). pthread, rt and dl functions are in libc.
- No epoll, inotify, eventfd, signalfd, timerfd, prctl, sysinfo, sendfile, <linux/*>, <byteswap.h>, <execinfo.h>.
  Use poll/select, pipes, timer_create, sysconf, pthread_setname_np, __builtin_bswap*.
- -D_QNX_SOURCE exposes POSIX and QNX extensions, like _GNU_SOURCE on glibc.
- Endianness: <gulliver.h> or __BYTE_ORDER__ from the compiler.
Rules for your answer:
- Make the smallest change that fixes the error. Prefer adding an `#if defined(__QNX__)` branch over
  rewriting Linux code; never delete functionality for other platforms.
- Never silence an error by deleting the code that uses a feature, unless the feature is optional and you
  guard it with __QNX__.
- Answer with JSON only: {"reason": "<one sentence a reviewer can check>", "diff": "<unified diff, paths
  prefixed a/ and b/, relative to the library root>"}. If you cannot fix it safely, answer
  {"reason": "<why>", "diff": ""}."""


def configured() -> bool:
    return bool(os.environ.get("QNX_PORTER_API_KEY") and os.environ.get("QNX_PORTER_MODEL"))


def context(src: Path, d: Diagnostic, rel: str | None, hint: str, log_tail: str) -> str:
    parts = [f"Build error:\n{d.raw or d.message}"]
    if hint:
        parts.append(f"Known QNX difference: {hint}")
    if rel:
        lines = (src / rel).read_text(encoding="utf-8", errors="replace").splitlines()
        lo, hi = max(d.line - 40, 0), min(d.line + 25, len(lines))
        numbered = "\n".join(f"{i + 1:5d} {lines[i]}" for i in range(lo, hi))
        parts.append(f"File {rel}, lines {lo + 1}-{hi} (line numbers are not part of the file):\n{numbered}")
    parts.append(f"End of the build log:\n{log_tail[-3000:]}")
    return "\n\n".join(parts)


def ask(prompt: str, timeout: int = 120) -> dict:
    base = os.environ.get("QNX_PORTER_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    body = {"model": os.environ["QNX_PORTER_MODEL"], "temperature": 0,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": f"Bearer {os.environ['QNX_PORTER_API_KEY']}"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        reply = json.load(r)["choices"][0]["message"]["content"]
    return parse_reply(reply)


def parse_reply(text: str) -> dict:
    """The JSON object in the model's reply, tolerating a ``` fence around it."""
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"reason": "model gave no JSON", "diff": ""}
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"reason": "model gave invalid JSON", "diff": ""}
    return {"reason": str(obj.get("reason", "")).strip(), "diff": str(obj.get("diff", ""))}
