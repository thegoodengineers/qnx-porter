"""The long tail: errors no rule handles go to a language model, which must answer with a small diff.

Configuration comes only from the environment (nothing provider-specific lives in this repository):
  QNX_PORTER_API_KEY      key for an OpenAI-compatible chat-completions endpoint
  QNX_PORTER_MODEL        model ID
  QNX_PORTER_BASE_URL     the endpoint's base URL (ending before /chat/completions)
  QNX_PORTER_TEMPERATURE  optional; sent only when set (some models reject sampling parameters)
  QNX_PORTER_MAX_TOKENS   optional; sent only when set
The model's diff is never trusted: it must pass `git apply --check`, and the agent keeps it only if the
rebuild clears the error it was meant to fix without adding new ones in the files it touched.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .errors import Diagnostic

SYSTEM = """You port C and C++ libraries to QNX Neutrino 8.0 (SDP 8.0, compiler qcc = GCC 12, POSIX libc).
Facts about QNX 8.0 that matter when porting from Linux:
- __QNX__ and __QNXNTO__ are defined. There is no __linux__.
- Sockets are in libsocket (-lsocket). pthread, rt and dl functions are in libc.
- No epoll, eventfd, signalfd, timerfd, prctl, sysinfo, sendfile, getrandom, <linux/*>, <byteswap.h>,
  <execinfo.h>. Use poll/select or ionotify(), pipe2(), timer_create, sysconf, pthread_setname_np,
  __builtin_bswap*, /dev/urandom. inotify exists but lives in libfsnotify. itoa() was removed: use snprintf().
- The socket API (io-sock) is ported from FreeBSD 14.3: prefer the FreeBSD branch of #ifdefs for networking.
- mmap's anonymous flag is documented as MAP_ANON. gettid() is in <process.h>.
- POSIX regex (regcomp/regexec) is in libregex (-lregex); isinf/isfinite/sqrt are in libm (-lm).
- SA_RESTART is not supported on QNX 8.0 (<signal.h> says so); code must cope with EINTR.
- QNX 8.0's struct qtime_entry has no nsec field: use clock_gettime(CLOCK_MONOTONIC) for uptime.
- In strict -std=c++NN or -std=c99 builds, QNX hides POSIX functions unless _QNX_SOURCE is defined.
- QNX 8.0 has no <endian.h>; htobe32 and friends are in <net/netbyte.h> (BSD extensions).
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
    return all(os.environ.get(k) for k in ("QNX_PORTER_API_KEY", "QNX_PORTER_MODEL", "QNX_PORTER_BASE_URL"))


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


def request_body(prompt: str, environ=None) -> dict:
    """The chat-completions request. Optional parameters are sent only when their env var is set."""
    env = os.environ if environ is None else environ
    body = {"model": env["QNX_PORTER_MODEL"],
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    if env.get("QNX_PORTER_TEMPERATURE", "").strip():
        body["temperature"] = float(env["QNX_PORTER_TEMPERATURE"])
    if env.get("QNX_PORTER_MAX_TOKENS", "").strip():
        body["max_tokens"] = int(env["QNX_PORTER_MAX_TOKENS"])
    return body


USAGE = {"calls": 0, "failed_calls": 0, "tokens_in": 0, "tokens_out": 0, "seconds": 0.0}  # per port, reset by agent


def ask(prompt: str, timeout: int = 300) -> dict:
    base = os.environ["QNX_PORTER_BASE_URL"].rstrip("/")
    req = urllib.request.Request(base + "/chat/completions", data=json.dumps(request_body(prompt)).encode(),
                                 method="POST", headers={"Content-Type": "application/json",
                                                         "Authorization": f"Bearer {os.environ['QNX_PORTER_API_KEY']}"})
    t0 = time.time()
    USAGE["calls"] += 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:  # report what the server said; never the request (it holds the key)
        USAGE["failed_calls"] += 1
        raise RuntimeError(f"model endpoint returned HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    finally:
        USAGE["seconds"] += time.time() - t0
    reply = data["choices"][0]["message"]["content"]
    usage = data.get("usage") or {}
    out = parse_reply(reply)
    out["tokens"] = {"in": usage.get("prompt_tokens", 0), "out": usage.get("completion_tokens", 0)}
    USAGE["tokens_in"] += out["tokens"]["in"]
    USAGE["tokens_out"] += out["tokens"]["out"]
    return out


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
