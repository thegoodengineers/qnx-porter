# Draft pull request for libconfig (not sent)

- **Upstream:** https://github.com/hyperrealm/libconfig
- **Patch:** [`0001-tests-do-not-pass-NULL-to-s-in-parse_string_and_comp.patch`](0001-tests-do-not-pass-NULL-to-s-in-parse_string_and_comp.patch),
  made with `git format-patch` against tag `v1.7.3` (`525922a6b49c`, the tag in `campaign.yaml`). Source:
  the port's kept patch [`ports-2024/libconfig/patches/0001-printf-null-tests-c.patch`](../../../ports-2024/libconfig/patches/0001-printf-null-tests-c.patch).
- **Upstream today:** `master` at `a82aa4dd3baf` (13 Nov 2026) still passes `config_error_file(&cfg)` straight
  to `"%s:%d %s\n"` in `parse_string_and_compare_error()` (`tests/tests.c:100-102`), and the patch applies to
  it unchanged (`git apply --check`).

## Why upstream would want it
Undefined-behaviour hygiene in the test suite. When a string is parsed, `config_error_file()` is NULL, and
passing NULL to `%s` is undefined in C. The test only passes because glibc prints `(null)`, which the expected
text (`"(null):%s"`) already assumes. The patch maps NULL to `"(null)"` before formatting, so the output and
the expected text stay exactly the same. The library's own code is not touched.

Before sending, consider renaming the helper `qnx_porter_str()` and rewording its comment to the project's
style (for example `str_or_null()`); that is a rename only, but it is not the exact text we tested.

## Verification, from our logs
Without the patch, the test binary crashed on the QNX 8.0 x86_64 target; the core's backtrace
(`ports-2024/libconfig/logs/crashes.log`):
```
#3  ... in snprintf (s=s@entry=0x57bf4b1a00 "testdata", size=size@entry=128, fmt=fmt@entry=0x14b0135cae "%s:%d %s\n") at .../lib/c/stdio/snprintf.c:71
#4  ... in parse_string_and_compare_error (parse_error=0x57bf4b1980 "2 syntax error\n", input_text=... "x\n") at .../tests/tests.c:99
#5  ParseInvalidStrings () at .../tests/tests.c:209
```
With the patch, on the same target (`ports/libconfig/logs/tests.log`):
```
PASS  libconfig_tests (exit 0)

1/1 tests passed on the QNX target
```
`docs/LEARNINGS.md` (12 Nov 2026) records that the binary reports `13 tests; 13 passed, 0 failed`.

**Not verified:** the patched tests on Linux (the output should be the same, since glibc already prints
`(null)`, but we have no log of that run), and the patch rebuilt on `master`.

## PR title
```
tests: do not pass NULL to %s in parse_string_and_compare_error()
```

## PR body
```
When a string (not a file) is parsed, config_error_file() returns NULL, and
parse_string_and_compare_error() formats it with "%s". Passing NULL to %s is undefined in C.
glibc prints "(null)", and the expected text is built as "(null):...", so the test passes
there; C libraries that do not special-case NULL crash in strlen() instead (seen on QNX 8.0).

This maps a NULL argument to "(null)" before formatting, so the output, and the expected
text, stay the same. Only tests/tests.c changes.

Tested with v1.7.3 on QNX 8.0 x86_64: libconfig_tests reports 13 tests, 13 passed (without the
change it ended in a memory fault in strlen() under snprintf()).
```
