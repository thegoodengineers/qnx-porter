"""video/render.py and video/record.py without the QNX target: parsing, narration, timing and the length guard."""
import csv
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


render = load("render", "video/render.py")
record = load("record", "video/record.py")
ports_csv = load("ports_csv", "scripts/ports_csv.py")
TABLE_FIELDS = ["library", "arch", "build_result", "tests_passed", "tests_total", "patches", "patches_by_rule",
                "patches_by_model"]  # cut -d, -f1,4,5,6,7,8,9,10 in record.py


def column(rows: list[list[str]]) -> str:
    """What `column -s, -t` prints: cells padded to the column width, two spaces apart, empty cells kept."""
    widths = [max(len(r[i]) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(c.ljust(w) for c, w in zip(r, widths)).rstrip() for r in rows)


def campaign_output(data: list[dict]) -> str:
    """The campaign shot as recorded: ports_csv.py's own summary lines, then the table of the CSV it wrote."""
    table = [TABLE_FIELDS] + [[str(r[k]) for k in TABLE_FIELDS] for r in data]
    return ports_csv.summary(data) + "\n" + column(table) + "\n"


def report(d: Path, name, **kw):
    r = {"library": name, "version": "v1", "build_system": "cmake", "arch": "x86_64", "build_result": "built",
         "tests_passed": 3, "tests_total": 4, "tests_ran": True, "patches_kept": 2, "patches_by_rule": 2,
         "patches_by_model": 0, "rounds": 1, "minutes": 1.0, "target": "QNX localhost 8.0.0", "finished": "x"}
    r.update(kw)
    (d / name).mkdir(parents=True)
    (d / name / "report.json").write_text(json.dumps(r))


def test_results_slide_reads_the_real_ports_csv_output_per_arch(tmp_path):
    report(tmp_path / "x", "a")
    report(tmp_path / "x", "b", build_result="failed", tests_ran=False, patches_kept=1, patches_by_rule=1)
    report(tmp_path / "x", "c", patches_kept=3, patches_by_rule=2, patches_by_model=1)
    report(tmp_path / "y", "a", arch="aarch64le", tests_passed=4, patches_kept=5, patches_by_rule=5)
    data = ports_csv.rows(tmp_path / "x") + ports_csv.rows(tmp_path / "y")
    text = campaign_output(data)
    assert text.startswith("aarch64le: 1 libraries")  # aarch64le sorts first: the slide must anchor on x86_64
    f = render.campaign(text)
    assert (f["lib"], f["built"], f["ran"], f["ok"], f["total"]) == ("3", "2", "2", "6", "8")
    assert (f["patches"], f["by_rule"], f["by_model"]) == (6, 5, 1)  # x86_64 rows only, failed ones included
    assert (f["a_lib"], f["a_ok"], f["a_total"], f["a_patches"]) == ("1", "4", "4", 5)
    title, lines = render.slide("results", f)
    assert "2 of 3 libraries built" in lines[0] and "6 of 8" in lines[1]
    assert "6 patches: 5 by deterministic rules, 1 by a language model" in lines[2]
    assert lines[3].startswith("aarch64 on QEMU: 1 of 1 built; 4 of 4 tests passed; 5 patches, 0 by")


def test_results_slide_without_aarch64_and_without_results(tmp_path):
    report(tmp_path, "a")
    f = render.campaign(campaign_output(ports_csv.rows(tmp_path)))
    assert render.slide("results", f)[1][3] == "aarch64 on QEMU: campaign running."
    with pytest.raises(SystemExit, match="results not found"):
        render.slide("results", render.campaign("tests ran for 33: 1/2 passed\n"))


def test_a_table_that_disagrees_with_the_summary_stops_the_render(tmp_path):
    report(tmp_path, "a")
    report(tmp_path, "b")
    text = campaign_output(ports_csv.rows(tmp_path))
    with pytest.raises(SystemExit, match="1 x86_64 rows"):
        render.campaign("\n".join(ln for ln in text.splitlines() if not ln.startswith("b ")))


def test_the_committed_campaign_parses_to_the_readme_headline():
    data = ports_csv.rows(ROOT / "ports") + ports_csv.rows(ROOT / "ports-aarch64le")
    f = render.campaign(campaign_output(data))
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = re.search(r"x86_64: (\d+) of (\d+) libraries built for QNX 8\.0; (\d+) of (\d+) of their own tests passed "
                  r"on a QNX 8\.0 target \((\d+) libraries with tests that ran\); (\d+) patches, (\d+) by rules", readme)
    assert m, "README headline not found"
    assert (f["built"], f["lib"], f["ok"], f["total"], f["ran"]) == m.groups()[:5]
    assert (str(f["patches"]), str(f["by_rule"])) == m.groups()[5:]


def recorded_texts() -> dict:
    """What each terminal shot prints, taken from the committed logs and files the recording re-creates."""
    def block(log, name):
        text = (ROOT / "results" / "runs" / log).read_text(encoding="utf-8")
        return re.search(rf"^=== \[\d+/\d+\] {re.escape(name)} .*?(?=^===|\Z)", text, re.S | re.M)[0]
    cmp = (ROOT / "docs/related/qnx-ports-comparison.md").read_text(encoding="utf-8")
    rt = (ROOT / "docs/RT_RESULTS.md").read_text(encoding="utf-8")
    data = ports_csv.rows(ROOT / "ports") + ports_csv.rows(ROOT / "ports-aarch64le")
    return {"mbedtls": block("campaign-7.log", "mbedtls"), "json-c": block("campaign-5.log", "json-c"),
            "campaign": campaign_output(data),
            "comparison": cmp[cmp.index("## Summary"):cmp.index("## Library")]
            + f"{len(list((ROOT / 'recipes/build-files/ports').iterdir()))}\n",
            "rt": rt[rt.index("## Latency"):rt.index("## What")]}


def test_every_narration_line_and_slide_is_filled_from_files():
    f = render.facts(recorded_texts())
    for shot, _, kind, body in record.scenes():
        text = render.narration(shot, f)
        assert "{" not in text and text
        if kind == "slide":
            title, lines = render.slide(body, f)
            assert title and lines
    assert render.slide("why-c", f)[1][2].startswith("On QNX 8.0: zlib ")
    assert "did not build with rules only" in render.slide("failures", f)[1][2]


def test_a_number_missing_from_the_recording_stops_the_render():
    with pytest.raises(SystemExit, match="mb_errors"):
        render.narration("mbedtls", {})


def test_placeholder_shots_go_in_only_with_their_csv(tmp_path):
    shots = {s[0] for s in record.scenes(tmp_path)}
    assert "crates" not in shots and "model" not in shots
    (tmp_path / "results").mkdir()
    (tmp_path / "results" / "crates.csv").write_text("crate\n")
    (tmp_path / "results" / "model_eval.csv").write_text("library\n")
    assert {"crates", "model"} <= {s[0] for s in record.scenes(tmp_path)}


@pytest.mark.parametrize("with_placeholders", [False, True])
def test_the_shot_list_stays_in_the_aim(tmp_path, with_placeholders):
    if with_placeholders:
        (tmp_path / "results").mkdir()
        (tmp_path / "results" / "crates.csv").write_text("crate\n")
        (tmp_path / "results" / "model_eval.csv").write_text("library\n")
    total = sum(s[1] for s in record.scenes(tmp_path))
    assert render.AIM[0] <= total <= render.AIM[1] and total < render.LIMIT
    assert set(s[0] for s in record.scenes(tmp_path)) <= set(render.NARRATION)


def cmd(t0, *times, text="x"):
    return {"cmd": "echo " + "y" * 60, "t": t0, "end": times[-1] + 1, "events": [(t, text) for t in times]}


def test_fit_fills_each_scene_to_its_length():
    cmds = [cmd(0, 1, 30, 200), cmd(201, 202)]
    p, pad = render.fit(cmds, 12)
    assert render.RELAXED[0] < p[0] <= render.TIGHT[0]  # had to type faster than relaxed
    assert render.terminal_length(cmds, p) + pad == pytest.approx(12, abs=1e-6)
    p, pad = render.fit(cmds, 60)  # plenty of time: relaxed pacing, the rest is held on the last frame
    assert p == render.RELAXED and pad > 0
    assert render.terminal_length(cmds, p) + pad == pytest.approx(60)
    p, pad = render.fit([cmd(0, *range(1, 400))], 5)  # 399 output chunks cannot fit in 5 s
    assert p == pytest.approx(render.TIGHT) and pad == 0 and render.terminal_length([cmd(0, *range(1, 400))], p) > 5


def test_timeline_scene_lengths_match_their_targets(tmp_path):
    markers = [{"t": 0, "shot": "title", "seconds": 7, "slide": "title"},
               {"t": 0, "shot": "rt", "seconds": 7, "caption": "c"},
               {"t": 0, "command": "sed x"}, {"t": 9, "done": "sed x", "exit": 0},
               {"t": 9, "shot": "paper", "seconds": 5, "image": "shots/site-paper.png"}]
    (tmp_path / "markers.json").write_text(json.dumps(markers))
    (tmp_path / "demo.cast").write_text("{}\n" + json.dumps([0.5, "o", "## Latency (14 libraries measured)\n"])
                                        + "\n" + json.dumps([8.0, "o", "| zlib |\n"]) + "\n")
    scenes = render.load(tmp_path)
    f = render.facts(render.shot_texts(scenes))
    assert f["rt_libs"] == "14"
    steps, table = render.build_timeline(scenes, f)
    assert [round(t[3], 6) for t in table] == [7, 7, 5]
    assert sum(d for d, _ in steps) == pytest.approx(19)


def test_length_guard():
    render.check_length(150)
    render.check_length(169.9)  # warns, does not fail
    with pytest.raises(SystemExit, match="under 170"):
        render.check_length(170)


def test_why_c_numbers_come_from_ports_csv():
    with (ROOT / "results" / "ports.csv").open(newline="", encoding="utf-8") as fh:
        z = next(r for r in csv.DictReader(fh) if r["library"] == "zlib" and r["arch"] == "x86_64")
    assert f"zlib {z['tests_passed']}/{z['tests_total']} tests pass" in render.slide("why-c", {})[1][2]
