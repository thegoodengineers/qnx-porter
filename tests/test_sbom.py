import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("sbom", Path(__file__).parents[1] / "scripts" / "sbom.py")
sbom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sbom)  # flags() needs no ScanCode; it is imported only inside the scan


@pytest.mark.parametrize("expr, gpl, lgpl, note", [
    ("MIT", "no", "no", ""),
    ("NOASSERTION", "no", "no", "no licence detected in the scanned files"),
    ("", "no", "no", "no licence detected in the scanned files"),
    ("GPL-2.0-only", "yes", "no", "strong copyleft GPL"),
    ("LGPL-2.1-or-later", "no", "yes", "weak copyleft LGPL"),
    ("AGPL-3.0-only", "yes", "no", "strong copyleft AGPL"),
    ("MPL-2.0", "no", "no", "weak copyleft MPL"),
    ("EPL-2.0 OR BSD-3-Clause", "no", "no", "weak copyleft EPL; expression has OR choices"),
    ("Apache-2.0 OR GPL-2.0-or-later", "yes", "no", "strong copyleft GPL; expression has OR choices"),
    # mixed: library under one licence, tools under another; every family is reported
    ("(BSD-3-Clause AND LGPL-2.1-only AND GPL-2.0-only AND GFDL-1.2-only) AND GFDL-1.1-or-later", "yes", "yes",
     "strong copyleft GPL; weak copyleft LGPL; documentation copyleft GFDL"),
    # an exception after WITH is not a licence, even when its id contains GPL
    ("Apache-2.0 WITH LLVM-exception", "no", "no", ""),
    ("MIT AND BSD-2-Clause WITH LGPL-3.0-linking-exception", "no", "no", ""),
    ("GPL-2.0-only WITH Linux-syscall-note", "yes", "no", "strong copyleft GPL"),
    ("LicenseRef-scancode-lgpl-2.1-plus-linking-exception", "no", "yes", "weak copyleft LGPL"),
    ("LicenseRef-scancode-public-domain AND CC0-1.0", "no", "no", ""),
])
def test_flags(expr, gpl, lgpl, note):
    assert sbom.flags(expr) == {"gpl_family": gpl, "lgpl": lgpl, "copyleft_note": note}
