# QNX 8.0: fchdir() fails with ENOTDIR on a directory opened with open(".", O_RDONLY)

**Status:** draft report for QNX, not sent, plus a one-line patch for googletest (`googletest-qnx-fchdir.patch`,
not sent). Found by qnx-porter's campaign (googletest 1.15.2's own tests), reproduced with `fchdir_test.c`
(this folder) on 12 Nov 2026. The team decides whether and where to send them.

## Summary
On QNX SDP 8.0 (build 141, x86_64), `open(".", O_RDONLY)` succeeds, but `fchdir()` on that descriptor fails
with `ENOTDIR`. The same directory opened with `O_RDONLY | O_DIRECTORY` works with `fchdir()`. On Linux both
work. POSIX `fchdir()` takes any open descriptor that refers to a directory; `O_DIRECTORY` is only a check
that the path names one.

## Reproduce
```
qcc -Vgcc_ntox86_64 fchdir_test.c -o fchdir_test
```

On the QNX 8.0 x86_64 target (same result in /data, /data/qnx-porter/fc and /tmp):
```
open(".", O_RDONLY) = 3 (ok)
open(".", O_RDONLY|O_DIRECTORY) = 4 (ok)
fchdir(fd) = -1 (Not a directory)
fchdir(fd2) = 0 (ok)
```

On Linux (glibc, WSL Ubuntu 22.04):
```
open(".", O_RDONLY) = 3 (ok)
open(".", O_RDONLY|O_DIRECTORY) = 4 (ok)
fchdir(fd) = 0 (ok)
fchdir(fd2) = 0 (ok)
```

## Effect seen: googletest's QNX death tests
googletest has a QNX-only code path for "threadsafe" death tests (`ExecDeathTestSpawnChild()` in
`googletest/src/gtest-death-test.cc`): it saves the working directory with `open(".", O_RDONLY)`, calls QNX's
`spawn()`, then restores it with `fchdir()`. On QNX 8.0 that `fchdir()` fails, the check aborts the test
program, and `googletest-death-test-test` and `gtest_repeat_test` end with SIGABRT
(`ports/googletest/logs/tests.log`, `logs/crashes.log`). The abort message, read from the core file with the
SDP's gdb:

```
CHECK failed: File .../googletest/src/gtest-death-test.cc, line 1287: fchdir(cwd_fd) != -1
```

With `O_DIRECTORY` added to that `open()` (`googletest-qnx-fchdir.patch`), rebuilt with qcc and run on the
same target: `googletest-death-test-test` passes 61 of 61 tests and `gtest_repeat_test` passes.

## Workaround until fixed
Open directories that will be passed to `fchdir()` with `O_DIRECTORY`.
