import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("latest_tags", ROOT / "scripts" / "latest_tags.py")
lt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lt)


@pytest.mark.parametrize("pin, same, other", [
    ("json-c-0.18-20240915", ["json-c-0.19-20260627"], ["json-c-0.19", "0.19-20260627"]),
    ("R_2_6_4", ["R_2_10_0", "R_3_0"], ["R-2-7-0", "v2.7.0"]),
    ("release-2.1.12-stable", ["release-2.1.13-stable"], ["release-2.1.13-alpha", "2.1.13"]),
    ("version-3.47.2", ["version-3.54.1"], ["v3.54.1"]),
    ("pcre2-10.44", ["pcre2-10.49"], ["pcre-8.45", "10.49"]),
    ("cmocka-1.1.7", ["cmocka-2.0.2"], ["libcmocka-2.0.2"]),
    ("v1.3.1", ["v1.4", "v1.3.1.1"], ["1.4", "v1.4-final"]),
    ("0.10.0", ["0.13.0", "1.0"], ["v0.13.0", "yaml-cpp-0.9.0"]),
])
def test_pattern_keeps_the_pins_naming(pin, same, other):
    pat = lt.pattern(pin)
    assert pat.match(pin)
    assert all(pat.match(t) for t in same)
    assert not any(pat.match(t) for t in other)


def test_newest_sorts_by_version_not_text():
    tags = ["v1.9.0", "v1.10.0", "v1.49.2", "v1.53.0", "v1.6.1", "v1.53.0"]
    assert lt.newest("v1.49.2", tags) == "v1.53.0"
    assert lt.newest("R_2_6_4", ["R_2_9_1", "R_2_10_0", "R_2_6_4"]) == "R_2_10_0"
    assert lt.newest("v2.14", ["v2.14", "v2.14.1", "v2.15"]) == "v2.15"


def test_newest_drops_prereleases():
    tags = ["v1.54.0-rc1", "v1.54.0rc2", "v2.0.0-alpha", "v2.0.0-beta.1", "v1.55-pre", "v1.56-dev", "v1.53.0"]
    assert lt.newest("v1.49.2", tags) == "v1.53.0"
    assert lt.newest("v1.0", ["v1.0-rc1"]) is None


def test_libraries_reads_block_and_flow_entries():
    text = ("libraries:\n  - name: json-c   # comment\n    url: https://github.com/json-c/json-c.git\n"
            "    tag: json-c-0.18-20240915\n"
            "  - {name: zlib, url: https://github.com/madler/zlib.git, tag: v1.3.1}\n")
    assert lt.libraries(text) == [
        {"name": "json-c", "url": "https://github.com/json-c/json-c.git", "tag": "json-c-0.18-20240915", "line": 3},
        {"name": "zlib", "url": "https://github.com/madler/zlib.git", "tag": "v1.3.1", "line": 4}]


def test_every_campaign_pin_matches_its_own_pattern():
    for lib in lt.libraries((ROOT / "campaign.yaml").read_text(encoding="utf-8")):
        assert lt.pattern(lib["tag"]).match(lib["tag"]), lib["name"]
