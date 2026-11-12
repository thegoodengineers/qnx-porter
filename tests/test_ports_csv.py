import csv
import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location("ports_csv", Path(__file__).parents[1] / "scripts" / "ports_csv.py")
ports_csv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ports_csv)


def report(tmp_path, name, **kw):
    r = {"library": name, "version": "v1", "build_system": "cmake", "arch": "x86_64", "build_result": "built",
         "tests_passed": 3, "tests_total": 4, "tests_ran": True, "patches_kept": 2, "patches_by_rule": 2,
         "patches_by_model": 0, "rounds": 3, "minutes": 1.5, "target": "QNX localhost 8.0.0", "finished": "x"}
    r.update(kw)
    (tmp_path / name).mkdir()
    (tmp_path / name / "report.json").write_text(json.dumps(r))


def test_csv_comes_only_from_reports_and_skips_host_self_tests(tmp_path):
    report(tmp_path, "a")
    report(tmp_path, "b", build_result="failed", tests_ran=False, tests_passed=0, tests_total=0)
    report(tmp_path, "selftest", arch="host")
    rows = ports_csv.rows(tmp_path)
    assert [r["library"] for r in rows] == ["a", "b"]
    assert (rows[0]["tests_passed"], rows[0]["tests_total"], rows[0]["patches"]) == (3, 4, 2)
    assert rows[1]["tests_total"] == ""  # not run is not the same as 0 of 0
    with open(tmp_path / "x.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ports_csv.FIELDS)
        w.writeheader()
        w.writerows(rows)


def test_readme_table_shows_not_run_instead_of_zero(tmp_path):
    report(tmp_path, "a")
    report(tmp_path, "b", tests_ran=False)
    table = ports_csv.readme_table(ports_csv.rows(tmp_path))
    assert "| [a](ports/a/REPORT.md) | v1 | x86_64 | built | 3/4 | 2 (2 / 0) | 1.5 |" in table
    assert "| not run |" in table
