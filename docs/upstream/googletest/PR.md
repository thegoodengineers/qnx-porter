# Draft pull request for googletest (not sent)

- **Upstream:** https://github.com/google/googletest
- **Patch:** [`0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch`](0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch),
  made with `git format-patch` against tag `v1.15.2` (`b514bdc898e2`, the tag in `campaign.yaml`). Source:
  [`docs/qnx-reports/googletest-qnx-fchdir.patch`](../../qnx-reports/googletest-qnx-fchdir.patch).
- **Upstream today:** `main` at `2910168b8bc1` (13 Nov 2026) still has `open(".", O_RDONLY)` at
  `googletest/src/gtest-death-test.cc:1263`, and the patch applies to it unchanged (`git apply --check`).

## Why upstream would want it
The change is in googletest's QNX-only path (`#ifdef GTEST_OS_QNX`). POSIX says `O_DIRECTORY` only makes
`open()` check that the path is a directory, and `"."` always is, so the flag cannot change behaviour where
`fchdir()` already worked. QNX 8.0 documents that its `fchdir()` needs it: the 8.0 C library reference lists
`ENOTDIR` for a descriptor that was not opened with `O_DIRECTORY`. QNX's own googletest fork
(`qnx-ports/googletest`, branch `qnx_v1.13.0`) makes the same one-line change.

## Verification, from our logs
Without the patch, googletest 1.15.2's own tests on the QNX 8.0 x86_64 target (`ports/googletest/logs/tests.log`):
```
FAIL  googletest-death-test-test (exit 134)
FAIL  gtest_repeat_test (exit 134)
25/27 tests passed on the QNX target; 18 not runnable there
```
The core dump (`ports/googletest/logs/crashes.log`) ends in `DeathTestAbort` called from
`ExecDeathTestSpawnChild`; the abort message read from the core
([`docs/qnx-reports/fchdir-o-rdonly.md`](../../qnx-reports/fchdir-o-rdonly.md)):
```
CHECK failed: File .../googletest/src/gtest-death-test.cc, line 1287: fchdir(cwd_fd) != -1
```
The behaviour on its own, `fchdir_test.c` on the same target (same document):
```
open(".", O_RDONLY) = 3 (ok)
open(".", O_RDONLY|O_DIRECTORY) = 4 (ok)
fchdir(fd) = -1 (Not a directory)
fchdir(fd2) = 0 (ok)
```
With the patch, rebuilt with qcc and run on the same target (same document): `googletest-death-test-test`
passes 61 of 61 tests and `gtest_repeat_test` passes.

**Not verified:** QNX 7.x (QNX's fork guards the change with `#if __QNX__ >= 800`; if maintainers want that
guard, add it), and the patch rebuilt on `main` rather than on `v1.15.2`.

## PR title
```
Open the saved working directory with O_DIRECTORY in QNX death tests
```

## PR body
```
On QNX, ExecDeathTestSpawnChild() saves the current directory with open(".", O_RDONLY),
spawns the child, and returns with fchdir(). QNX 8.0's fchdir() needs a descriptor opened
with O_DIRECTORY (its C library reference lists ENOTDIR otherwise), so the fchdir() check
aborts and every "threadsafe" death test aborts on QNX 8.0.

O_DIRECTORY only asks open() to confirm that "." is a directory, which it always is, so
the change is safe wherever this code runs. QNX's own googletest fork carries the same
change.

Tested on QNX 8.0 x86_64 with v1.15.2: googletest-death-test-test passes 61/61 and
gtest_repeat_test passes; both aborted (SIGABRT) before.
```
