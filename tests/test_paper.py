"""The paper regenerates from the result files: every \\N{key} it uses is defined, and paper.md renders cleanly."""
import csv
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paper_build", ROOT / "paper" / "build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def test_every_number_the_paper_uses_is_defined_and_the_markdown_renders():
    n = build.collect()
    tex = (ROOT / "paper" / "qnx-porter.tex").read_text(encoding="utf-8")
    used = set(re.findall(r"\\N\{([^}]+)\}", re.sub(r"(?<!\\)%[^\n]*", "", tex)))
    assert used and not used - set(n)
    md = build.Md(n, tex).render()
    assert "\\N{" not in md and "## 4 Evaluation" in md


def test_headline_numbers_are_the_csv_sums():
    n = build.collect()
    rows = [r for r in csv.DictReader((ROOT / "results" / "ports.csv").open(encoding="utf-8"))
            if r["arch"] == "x86_64" and r["tests_total"] not in ("", "0")]
    assert n["x-tests-passed"] == sum(int(r["tests_passed"]) for r in rows)
    assert n["x-tested-libs"] == len(rows)
