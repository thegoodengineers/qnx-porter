"""The focused codelab: QNX codelab format, its copy for qnx/codelabs, and output blocks copied from real logs."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODELAB = ROOT / "docs" / "codelab" / "port-a-library.md"
QNX_COPY = ROOT / "docs" / "codelab" / "qnx-codelabs-format" / "markdown" / "port-cmake-library-qnx" / \
    "port-cmake-library-qnx.md"
LOGS = ["results/runs/campaign-7.log", "results/runs/campaign-aarch64-2.log", "ports-2024/json-c/qnx-toolchain.cmake",
        "ports-2024/json-c/logs/round-01.log", "ports-2024/json-c/logs/tests.log", "ports-2024/json-c/logs/crashes.log",
        "ports/json-c/patches/0001-printf-null-test-json-patch-c.patch",
        "ports-2024/mbedtls/patches/0001-link-libsocket.patch"]


def split(text: str) -> tuple[dict, str]:
    meta, body = text.split("\n# ", 1)
    return dict(re.findall(r"^(\w+): (.*)$", meta, re.M)), body


def test_metadata_and_a_duration_under_every_step():
    meta, body = split(CODELAB.read_text(encoding="utf-8"))
    assert set(meta) == {"id", "title", "summary", "categories", "tags", "difficulty", "status", "authors",
                         "feedback_link"}
    assert meta["id"] == CODELAB.stem
    steps = re.findall(r"^## (.+)\n(.*)$", body, re.M)
    assert steps[0][0] == "Introduction" and steps[-1][0] == "Summary and next steps"
    assert all(re.fullmatch(r"Duration: \d+:\d\d", d) for title, d in steps if title != "Troubleshooting")


def test_qnx_copy_differs_only_in_id_and_feedback_link():
    ours, theirs = (split(p.read_text(encoding="utf-8")) for p in (CODELAB, QNX_COPY))
    assert ours[1] == theirs[1]
    assert theirs[0]["id"] == QNX_COPY.stem == QNX_COPY.parent.name
    assert {k: v for k, v in ours[0].items() if k not in ("id", "feedback_link")} == \
        {k: v for k, v in theirs[0].items() if k not in ("id", "feedback_link")}


def test_every_output_block_is_copied_from_a_real_log():
    real = {ln for f in LOGS for ln in (ROOT / f).read_text(encoding="utf-8").splitlines()}
    blocks, fence = [], None  # fence: the open block's language ("" for output), None outside a block
    for ln in CODELAB.read_text(encoding="utf-8").splitlines():
        if ln.startswith("```"):
            fence = ln[3:] if fence is None else None
            if fence == "":
                blocks.append([])
        elif fence == "":
            blocks[-1].append(ln)
    assert len(blocks) >= 10
    for b in blocks:
        assert [ln for ln in b if ln not in real] == []
