# 3 - cisco/libsrtp: shuffle without qsort() and a random comparator

- **Upstream:** https://github.com/cisco/libsrtp (default branch `main`)
- **Checked:** `main` at `052aa2965e2c26f737087492d37a31c3ee09ddba` (commit date 2026-11-13T13:02:43+01:00), shallow
  clone on 14 Nov 2026. `test/ut_sim.c` still calls `qsort(utc->buffer, UT_BUF, sizeof(uint32_t), ut_compar)`
  in `ut_init()` and `ut_next_index()`, and `ut_compar()` still answers at random.
- **Apply check:** the draft in `docs/upstream/libsrtp/` (made against `v2.6.0`) does **not** apply: the `for`
  loop above the first `qsort()` now has braces. **Refreshed**: applied with `git am -C1` (same hunks, context
  reduced), then the new comment block was rewrapped from ~100 to 80 columns, because `.clang-format` has
  `ColumnLimit: 80` and CI runs a clang-format check. Code and comment text are unchanged; only line breaks in
  the comment moved. `git apply --check` of the new patch passes on `052aa2965e2c`.
- **Checked on Linux in a scratch clone (WSL Ubuntu 22.04, gcc 11.4.0):** `main` + this patch, CMake with
  `-DCRYPTO_LIBRARY=internal` (the default `openssl` was not installed there), built with the project's default
  warnings-as-errors; `ctest` reported all tests passed, including `rdbx_driver`, `replay_driver`, `roc_driver`.
  Not rebuilt for QNX on `main`. `clang-format-17` could not be run on this machine, so the format check is
  unverified until CI runs.

## Contribution rules found
None in the repository: no CONTRIBUTING file, no PR or issue template, no CLA or DCO (and no `cisco/.github`
repository). CI on PRs includes [`format_check.yml`](https://github.com/cisco/libsrtp/blob/main/.github/workflows/format_check.yml)
(`./format.sh -d` with clang-format-17).

## What the person must do first
Nothing required. Optionally run `./format.sh -d` with clang-format-17 before pushing.

## Evidence
QNX numbers (480 of 2000, exit codes) from `docs/upstream/libsrtp/PR.md` and
`docs/qnx-reports/qsort-inconsistent-comparator.md`; they are for v2.6.0.
