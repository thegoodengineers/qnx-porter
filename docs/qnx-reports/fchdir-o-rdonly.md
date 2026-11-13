# QNX 8.0: fchdir() needs a directory opened with O_DIRECTORY (Linux does not)

**Status:** a documented QNX difference, not a QNX bug, plus a one-line patch for upstream googletest
(`googletest-qnx-fchdir.patch`, not sent). Found by qnx-porter's campaign (googletest 1.15.2's own tests),
reproduced with `fchdir_test.c` (this folder) on 12 Nov 2026. The team decides whether to send the patch.

## Summary
On QNX SDP 8.0 (build 141, x86_64), `open(".", O_RDONLY)` succeeds, but `fchdir()` on that descriptor fails
with `ENOTDIR`. The same directory opened with `O_RDONLY | O_DIRECTORY` works with `fchdir()`. On Linux both
work. QNX documents this: the 8.0 C library reference's
[`fchdir()` page](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/f/fchdir.html)
lists `ENOTDIR` for a descriptor that "wasn't opened with O_DIRECTORY". POSIX lets `fchdir()` take any open
descriptor that refers to a directory, so code written for Linux or POSIX trips on it.

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
(`ports-2024/googletest/logs/tests.log`, `logs/crashes.log`). The abort message, read from the core file with the
SDP's gdb:

```
CHECK failed: File .../googletest/src/gtest-death-test.cc, line 1287: fchdir(cwd_fd) != -1
```

With `O_DIRECTORY` added to that `open()` (`googletest-qnx-fchdir.patch`), rebuilt with qcc and run on the
same target: `googletest-death-test-test` passes 61 of 61 tests and `gtest_repeat_test` passes.

## QNX's own googletest port makes the same change
QNX's hand-made googletest port (`qnx-ports/googletest`, branch `qnx_v1.13.0`, `googletest/src/gtest-death-test.cc`
line 1296) opens the directory with `O_RDONLY | O_DIRECTORY` under `#if __QNX__ >= 800`. We found the same
fix independently, from the core dump, before reading their port. Upstream googletest 1.15.2 still opens it with
`O_RDONLY` only, which is what the patch in this folder changes.

## What to do
Open directories that will be passed to `fchdir()` with `O_DIRECTORY`.
