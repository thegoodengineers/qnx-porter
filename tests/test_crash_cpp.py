"""Crash triage on a C++ test whose backtrace has a string argument containing parentheses."""
from qnx_porter import crash
from qnx_porter.fixes import in_tree

# Real backtrace from tinyxml2 10.0.0's xmltest on QNX 8.0 (paths shortened to {src}).
TINYXML2_BT = r"""#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x0000004761ea008d in _Putfld (px=px@entry=0x530d09e6c0, pap=<optimized out>, code=<optimized out>, ac=ac@entry=0x530d09e870 "") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#3  0x0000004761e99d7c in printf (fmt=0x1ed3fa4b77 " %s [%s][%s]\n") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/printf.c:37
#4  0x0000001ed3f90aa5 in XMLTest (testString=testString@entry=0x1ed3fa8ad0 "XMLDocument::Value() returns null?", expected=expected@entry=0x0, found=0x0, extraNL=false, echo=true) at {src}/xmltest.cpp:3
#5  0x0000001ed3f8f83c in main (argc=<optimized out>, argv=<optimized out>) at {src}/xmltest.cpp:9
"""

SRC = r"""#include <cstdio>
bool XMLTest(const char *t, const char *e, const char *f) {
			printf (" %s [%s][%s]\n", t, e, f);
	return true;
}
"""


def test_cpp_frame_with_parentheses_in_a_string_argument(tmp_path):
    (tmp_path / "xmltest.cpp").write_text(SRC)
    bt = TINYXML2_BT.replace("{src}", str(tmp_path))
    fr = crash.frames(bt)
    assert fr[3][0] == "XMLTest" and fr[3][1].endswith("xmltest.cpp") and fr[3][2] == 3
    rel, _, new = crash.printf_null(bt, tmp_path, in_tree)
    assert rel == "xmltest.cpp"
    assert r'printf (" %s [%s][%s]\n", qnx_porter_str(t), qnx_porter_str(e), qnx_porter_str(f));' in new
