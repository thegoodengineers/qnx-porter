### Describe the issue

On QNX 8.0, every "threadsafe" death test aborts the test program.

`ExecDeathTestSpawnChild()` in `googletest/src/gtest-death-test.cc` has a QNX-only path (`#ifdef GTEST_OS_QNX`): it saves the current directory with `open(".", O_RDONLY)`, spawns the child, and goes back with `fchdir(cwd_fd)`. QNX 8.0's `fchdir()` fails with `ENOTDIR` for a descriptor that was not opened with `O_DIRECTORY` (documented in the QNX 8.0 C library reference: https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/f/fchdir.html). The `GTEST_DEATH_TEST_CHECK_SYSCALL_(fchdir(cwd_fd))` check then aborts:

```
CHECK failed: File .../googletest/src/gtest-death-test.cc, line 1287: fchdir(cwd_fd) != -1
```

Expected: the death tests run as on other platforms.

Proposed fix (one line, I can send a PR): `open(".", O_RDONLY | O_DIRECTORY)`. `O_DIRECTORY` is POSIX and only makes `open()` check that the path is a directory, which `"."` always is, so it cannot change behaviour where `fchdir()` already works. QNX's own googletest fork (`qnx-ports/googletest`, branch `qnx_v1.13.0`) carries the same change.

### Steps to reproduce the problem

Build googletest with its own tests (`-Dgtest_build_tests=ON`) for QNX 8.0 x86_64 with qcc and run them on a QNX 8.0 target. `googletest-death-test-test` and `gtest_repeat_test` end with SIGABRT:

```
FAIL  googletest-death-test-test (exit 134)
FAIL  gtest_repeat_test (exit 134)
```

The underlying behaviour on its own, with a small C program on the same target:

```
open(".", O_RDONLY) = 3 (ok)
open(".", O_RDONLY|O_DIRECTORY) = 4 (ok)
fchdir(fd) = -1 (Not a directory)
fchdir(fd2) = 0 (ok)
```

On Linux all four calls succeed.

### What version of GoogleTest are you using?

Seen with v1.15.2. The same line (`open(".", O_RDONLY)`, `googletest/src/gtest-death-test.cc:1263`) is still in `main` at e882c36410197464e3429546e6a7d5e217bde51e.

### What operating system and version are you using?

QNX SDP 8.0 (build 141), x86_64 target running in QEMU.

### What compiler and version are you using?

QCC 12.2.0 (QNX SDP 8.0, `-Vgcc_ntox86_64`).

### What build system are you using?

CMake, cross-compiling with a QNX toolchain file.

### Additional context

With the one-line change, rebuilt with qcc and run on the same target, `googletest-death-test-test` passes 61 of 61 tests and `gtest_repeat_test` passes.

Not checked: QNX 7.x. QNX's fork guards the change with `#if __QNX__ >= 800`; I can add that guard if you prefer it.
