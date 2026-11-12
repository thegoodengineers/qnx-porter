"""Crash triage: real backtraces from QNX 8.0 core dumps (json-c and libconfig tests, 12 Nov 2026)."""
import os
import shutil
import subprocess

from qnx_porter import crash
from qnx_porter.fixes import in_tree

CC = shutil.which("cc") if os.name != "nt" else None

JSONC_BT = """Program terminated with signal SIGSEGV, Segmentation fault.
#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x000000121587908d in _Putfld (px=px@entry=0x3fef881440, pap=<optimized out>, code=<optimized out>, ac=ac@entry=0x3fef8815f0 "") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#2  0x0000001215878378 in _Printf (pfn=<optimized out>, arg=arg@entry=0x12158ba260 <_Stdout>, fmt=<optimized out>, fmt@entry=0x4ea063a268 "Testing '%s', doc '%s' patch '%s' : ", ap_arg=ap_arg@entry=0x3fef881680, secure=secure@entry=0) at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xprintf.c:603
#3  0x0000001215872d7c in printf (fmt=0x4ea063a268 "Testing '%s', doc '%s' patch '%s' : ") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/printf.c:37
#4  0x0000004ea062daf6 in test_json_patch_op (jo=0x582ac58c40) at {src}/tests/test_json_patch.c:11
#5  0x0000004ea062dfb1 in test_json_patch_using_file (testdir=0x3fef881df7 "/data/dbg", filename=0x4ea063a570 "json_patch_tests.json") at {src}/tests/test_json_patch.c:91
"""

JSONC_SRC = """#include <stdio.h>
#include "json.h"

static void test_json_patch_op(struct json_object *jo)
{
	const char *comment = 0;
	const char *error_s = 0;
	struct json_object *doc = 0, *patch = 0;
	int ret;

	printf("Testing '%s', doc '%s' patch '%s' : ",
		comment ? comment : error_s,
		json_object_get_string(doc),
		json_object_get_string(patch));
}
"""

LIBCONFIG_BT = """#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x00000018fee3408d in _Putfld (px=px@entry=0x3503e783d0, pap=<optimized out>, code=<optimized out>, ac=ac@entry=0x3503e78580 "") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#2  0x00000018fee33378 in _Printf (pfn=<optimized out>, arg=arg@entry=0x3503e78610, fmt=<optimized out>, ap_arg=ap_arg@entry=0x3503e78620, secure=secure@entry=0) at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xprintf.c:603
#3  0x00000018fee2e37d in snprintf (s=<optimized out>, size=<optimized out>, fmt=<optimized out>) at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/snprintf.c:71
#4  0x0000004959988eb1 in parse_string_and_compare_error (input_text=0x18fee7a240 <__main_arena+17088> "x\\n", parse_error=0x3503e78a00 "2 syntax error\\n") at {src}/tests/tests.c:7
#5  0x00000049599897f5 in ParseInvalidStrings () at {src}/tests/tests.c:20
"""

LIBCONFIG_SRC = """#include <stdio.h>
#include "libconfig.h"

static void check(config_t *cfg)
{
  char actual_error[128];
  snprintf(actual_error, sizeof(actual_error), "%s:%d %s\\n",
           config_error_file(cfg), config_error_line(cfg),
           config_error_text(cfg));
}
"""


def setup(tmp_path, rel, text):
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / rel).write_text(text)
    return tmp_path


def test_jsonc_null_percent_s_is_wrapped(tmp_path):
    src = setup(tmp_path, "tests/test_json_patch.c", JSONC_SRC)
    r = crash.printf_null(JSONC_BT.replace("{src}", str(src)), src, in_tree)
    assert r is not None
    rel, reason, new = r
    assert rel == "tests/test_json_patch.c" and "glibc prints" in reason
    assert "qnx_porter_str(comment ? comment : error_s)" in new
    assert "qnx_porter_str(json_object_get_string(doc))" in new and "qnx_porter_str(json_object_get_string(patch))" in new
    assert new.count("static const char *qnx_porter_str") == 1


def test_libconfig_snprintf_only_wraps_the_percent_s_arguments(tmp_path):
    src = setup(tmp_path, "tests/tests.c", LIBCONFIG_SRC)
    rel, _, new = crash.printf_null(LIBCONFIG_BT.replace("{src}", str(src)), src, in_tree)
    assert "qnx_porter_str(config_error_file(cfg)), config_error_line(cfg)" in new  # %d left alone
    assert "qnx_porter_str(config_error_text(cfg))" in new
    assert "snprintf(actual_error, sizeof(actual_error)," in new


def test_format_positions():
    assert crash.string_arg_positions("%s:%d %s\\n") == [0, 2]
    assert crash.string_arg_positions("%*s %%s %.*s %5.2f %s") == [1, 3, 5]


def test_crash_outside_printf_or_outside_the_library_is_left_alone(tmp_path):
    src = setup(tmp_path, "tests/tests.c", LIBCONFIG_SRC)
    assert crash.printf_null("#0  memcpy () at /x/memcpy.s:1\n#1  0x1 in f () at {}/tests/tests.c:7\n"
                             .format(src), src, in_tree) is None
    assert crash.printf_null(LIBCONFIG_BT.replace("{src}", "/elsewhere"), src, in_tree) is None


def test_gdb_name():
    assert crash.gdb_name("x86_64-pc-nto-qnx8.0.0") == "x86_64-nto-qnx8.0.0-gdb"
    assert crash.gdb_name("aarch64-unknown-nto-qnx8.0.0") == "aarch64-nto-qnx8.0.0-gdb"


def test_wrapped_code_still_compiles(tmp_path):
    if not CC:
        return
    src = setup(tmp_path, "tests/tests.c", LIBCONFIG_SRC.replace('#include "libconfig.h"\n', "")
                .replace("config_t *cfg", "void *cfg").replace("config_error_file(cfg)", "(const char *)0")
                .replace("config_error_line(cfg)", "1").replace("config_error_text(cfg)", "\"e\""))
    bt = LIBCONFIG_BT.replace("{src}", str(src))
    r = crash.printf_null(bt, src, in_tree)
    assert r is not None
    (tmp_path / "w.c").write_text(r[2])
    assert subprocess.run([CC, "-fsyntax-only", "-Wall", "-Werror", str(tmp_path / "w.c")]).returncode == 0


def test_helper_goes_after_the_platform_branch_holding_the_last_include():
    src = ('#include "tinyxml2.h"\n#if defined(_MSC_VER)\n#include <windows.h>\n#else\n#include <sys/stat.h>\n'
           '#endif\nint x;\n')
    lines = crash._insert_helper(src).splitlines()
    assert lines.index("#endif") < lines.index(crash.HELPER.splitlines()[-1])
    guarded = '#ifndef A_H\n#define A_H\n#include <stdio.h>\nint y;\n#endif\n'
    assert crash._insert_helper(guarded).rstrip().endswith("int y;\n#endif")
