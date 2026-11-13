"""Find each campaign library's newest stable upstream release tag; with --write, update campaign.yaml in place.

For a GitHub repo it asks `gh api repos/<o>/<r>/releases/latest` (GitHub leaves drafts and prereleases out of
that). If there is no such release, or its tag does not follow the same naming pattern as the current pin, it
falls back to `git ls-remote --tags`, keeps the tags that follow the pin's pattern, drops rc/alpha/beta/pre/dev
tags, and takes the highest version. A tag lower than the pin is never written. Only the `tag:` value on each
library's own line changes; comments, order and formatting are kept.

Usage: python3 scripts/latest_tags.py [--campaign FILE] [--only a,b] [--write]
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UNSTABLE = re.compile(r"(?i)(?:^|[^a-z])(?:rc|alpha|beta|pre|preview|dev)(?:[^a-z]|$)")
VERSION_RUN = re.compile(r"\d+(?:[._]\d+)*")


def pattern(pin: str) -> re.Pattern:
    """The pin's naming pattern: its literal text kept, each run of version numbers made free, with any count
    of components joined by that run's separator (so v2.14 also matches v2.14.1, R_2_6_4 matches R_2_7_1)."""
    out, pos = "", 0
    for m in VERSION_RUN.finditer(pin):
        sep = "_" if "_" in m.group() else r"\."
        out += re.escape(pin[pos:m.start()]) + rf"\d+(?:{sep}\d+)*"
        pos = m.end()
    return re.compile(out + re.escape(pin[pos:]) + "$")


def version(tag: str) -> tuple:
    return tuple(int(n) for n in re.findall(r"\d+", tag))


def newest(pin: str, tags: list[str]) -> str | None:
    """Highest tag with the pin's pattern that is not a prerelease, or None."""
    pat = pattern(pin)
    ok = [t for t in set(tags) if pat.match(t) and not UNSTABLE.search(t)]
    return max(ok, key=version, default=None)


def run(*cmd: str) -> str | None:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    return p.stdout if p.returncode == 0 else None


def remote_tags(url: str) -> list[str]:
    out = run("git", "ls-remote", "--tags", "--refs", url) or ""
    return [line.split("refs/tags/", 1)[1] for line in out.splitlines() if "refs/tags/" in line]


def lookup(url: str, pin: str) -> tuple[str, str, str, str]:
    """(tag, date or '', source, note for the human review). The note flags what the rules cannot decide: a
    latest release under another naming, a tag newer than the latest release, a suffixed tag such as v4.3.5b."""
    gh = re.match(r"https://github\.com/([^/]+/[^/]+?)(?:\.git)?$", url)
    tags = remote_tags(url)
    best = newest(pin, tags)
    odd = [t for t in tags if t.startswith(pin) and t != pin and not pattern(pin).match(t) and not UNSTABLE.search(t)]
    note = f"also tagged: {', '.join(sorted(odd))}" if odd else ""
    if gh and (rel := run("gh", "api", f"repos/{gh[1]}/releases/latest")):
        r = json.loads(rel)
        tag = r["tag_name"]
        if not pattern(pin).match(tag):
            note = f"latest release `{tag}` has another naming; {note}".rstrip("; ")
        elif not UNSTABLE.search(tag) and version(tag) >= version(pin):
            if best and version(best) > version(tag):
                note = f"newer tag than the latest release: `{best}`; {note}".rstrip("; ")
            return tag, (r.get("published_at") or "")[:10], "releases/latest", note
    if not best or version(best) <= version(pin):
        return pin, "", "kept", note
    date = ""
    if gh:
        date = (run("gh", "api", f"repos/{gh[1]}/commits/{best}", "--jq", ".commit.committer.date") or "")[:10]
    return best, date, "ls-remote", note


def libraries(text: str) -> list[dict]:
    """name, url, tag and the line index of `tag:` for each library, read line by line (block or flow style)."""
    libs, cur = [], {}
    for i, line in enumerate(text.splitlines()):
        for key in ("name", "url", "tag"):
            m = re.search(rf"\b{key}: ([^,\s}}#]+)", line)
            if m:
                cur[key] = m[1]
                if key == "tag":
                    libs.append({**cur, "line": i})
                    cur = {}
    return libs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--campaign", default=str(ROOT / "campaign.yaml"))
    ap.add_argument("--only", help="comma-separated library names")
    ap.add_argument("--write", action="store_true", help="update the tag: values in place")
    a = ap.parse_args()
    path = Path(a.campaign)
    text = path.read_bytes().decode("utf-8")  # keep the file's own line endings
    lines = text.splitlines(keepends=True)
    only = set(a.only.split(",")) if a.only else None
    print("| Library | Old tag | New tag | Released | Source | Note |\n|---|---|---|---|---|---|")
    for lib in libraries(text):
        if only and lib["name"] not in only:
            continue
        tag, date, src, note = lookup(lib["url"], lib["tag"])
        print(f"| {lib['name']} | `{lib['tag']}` | `{tag}` | {date} | {src} | {note} |", flush=True)
        if a.write and tag != lib["tag"]:
            n = lib["line"]
            lines[n] = re.sub(rf"\btag: {re.escape(lib['tag'])}(?=[,\s}}#]|$)", f"tag: {tag}", lines[n], count=1)
    if a.write:
        path.write_text("".join(lines), encoding="utf-8", newline="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
