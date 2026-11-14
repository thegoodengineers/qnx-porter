Fixes #ISSUE_NUMBER

On QNX, `ExecDeathTestSpawnChild()` saves the current directory with `open(".", O_RDONLY)`, spawns the child, and returns with `fchdir()`. QNX 8.0's `fchdir()` needs a descriptor opened with `O_DIRECTORY` (its C library reference lists `ENOTDIR` otherwise), so the `fchdir()` check aborts and every "threadsafe" death test aborts on QNX 8.0.

`O_DIRECTORY` only asks `open()` to confirm that `"."` is a directory, which it always is, so the change is safe wherever this code runs. The line is inside `#ifdef GTEST_OS_QNX`; no other platform compiles it. QNX's own googletest fork carries the same change.

Tested on QNX 8.0 x86_64 with v1.15.2: `googletest-death-test-test` passes 61/61 and `gtest_repeat_test` passes; both aborted (SIGABRT) before. The patch applies unchanged to `main` (e882c36410197464e3429546e6a7d5e217bde51e); it has not been rebuilt on `main`.
