import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("upstream", Path(__file__).parents[1] / "scripts" / "upstream.py")
upstream = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upstream)


def test_candidates_are_source_fixes_from_the_ports_not_build_workarounds():
    rows = upstream.candidates()
    found = {(c["library"], c["rule"]) for c in rows}
    assert ("json-c", "printf-null") in found and ("nng", "header-alias") in found
    assert not any(c["rule"].startswith(("link-", "no-werror")) for c in rows)  # QNX-side build choices
    assert all(Path(upstream.ROOT / c["patch"]).is_file() for c in rows)
