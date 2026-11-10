"""Every change the agent makes becomes a numbered, reviewable patch file with its reason.

Source changes are git commits in the library checkout; build-flag changes are diffs of the generated
toolchain file. Nothing is changed without a patch on disk explaining it.
"""
import difflib
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


def git(src: Path, *args: str, input: str | None = None, check=True) -> str:
    r = subprocess.run(["git", "-C", str(src), *args], capture_output=True, text=True, input=input,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


@dataclass
class Patch:
    number: int
    rule: str
    source: str  # "rule" or "model"
    reason: str
    error: str
    files: list[str]
    path: str  # patch file, relative to the port folder
    kept: bool = True

    def to_dict(self):
        return asdict(self)


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


def header(n: int, rule: str, source: str, reason: str, error: str) -> str:
    return (f"Subject: [qnx-porter {n:04d}] {rule}\n"
            f"Source: {'deterministic rule' if source == 'rule' else 'language model, checked by rebuilding'}\n"
            f"Reason: {reason}\n"
            f"Error: {error.strip()}\n---\n")


def commit_source(src: Path, out: Path, n: int, rule: str, source: str, reason: str, error: str,
                  files: list[str]) -> Patch:
    git(src, "add", "--", *files)
    diff = git(src, "diff", "--cached")
    name = f"patches/{n:04d}-{slug(rule + ' ' + Path(files[0]).name)}.patch"
    (out / name).write_text(header(n, rule, source, reason, error) + diff, encoding="utf-8")
    git(src, "-c", "user.name=qnx-porter", "-c", "user.email=qnx-porter@localhost", "commit", "-q",
        "-m", f"qnx-porter {n:04d}: {rule}", "-m", reason)
    return Patch(n, rule, source, reason, error.strip(), files, name)


def record_flags(out: Path, n: int, rule: str, reason: str, error: str, name_in_diff: str, before: str,
                 after: str) -> Patch:
    diff = "".join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                        f"a/{name_in_diff}", f"b/{name_in_diff}"))
    name = f"patches/{n:04d}-{slug(rule)}.patch"
    (out / name).write_text(header(n, rule, "rule", reason, error) + diff, encoding="utf-8")
    return Patch(n, rule, "rule", reason, error.strip(), [name_in_diff], name)


def apply_diff(src: Path, diff: str) -> tuple[bool, str]:
    """Apply a unified diff from the model after `git apply --check`. Returns (ok, why not)."""
    if not diff.endswith("\n"):
        diff += "\n"
    r = subprocess.run(["git", "-C", str(src), "apply", "--check", "--recount", "-"], input=diff,
                       capture_output=True, text=True)
    if r.returncode != 0:
        return False, r.stderr.strip()
    git(src, "apply", "--recount", "-", input=diff)
    return True, ""


def changed_files(diff: str) -> list[str]:
    return sorted({m for m in re.findall(r"^\+\+\+ b/(\S+)", diff, re.M)})


def revert_last(src: Path) -> None:
    git(src, "reset", "-q", "--hard", "HEAD~1")


def export_series(src: Path, base: str, out: Path) -> str:
    """One combined diff of all kept source changes against the upstream tag."""
    diff = git(src, "diff", base, "HEAD")
    (out / "qnx.patch").write_text(diff, encoding="utf-8")
    return diff
