id: port-cmake-library-qnx
title: Port a CMake C Library to QNX 8.0 and Run Its Own Tests on a QEMU Target
summary: Cross-compile an open-source CMake C library with qcc using qnx-porter, run the library's own test suite on a QNX 8.0 target in QEMU, read a QNX core dump with the SDP's gdb, and link sockets from libsocket
categories: qnx, porting, cmake, qemu
tags: intermediate
difficulty: 2
status: published
authors: The Good Engineers
feedback_link: https://github.com/qnx/codelabs/issues

# Port a CMake C Library to QNX 8.0 and Run Its Own Tests on a QEMU Target

## Introduction
Duration: 3:00

Most open-source C libraries are written and tested on Linux. A QNX 8.0 system has a different C library, a
different socket library and, on a production target, no compiler at all. In this codelab you take a real
library, [json-c](https://github.com/json-c/json-c), cross-compile it for QNX 8.0 with the SDP's `qcc`, and run
**json-c's own 25 tests on a QNX 8.0 target** booted in QEMU. One test crashes on QNX; you read the QNX core dump
to find out why. Then you port a second library, mbedtls, that needs QNX's `libsocket`.

[qnx-porter](https://github.com/thegoodengineers/qnx-porter) does the porting: it generates the CMake toolchain
file, builds, applies reviewable patches, copies the build to the target and runs the tests there. This codelab
explains what each of those steps does on QNX, so you can do the same by hand.

**What you will learn:**

* Why QNX code is cross-compiled with `qcc`, and what a CMake toolchain file for QNX 8.0 contains
* What `mkqnximage` builds, and how to boot a QNX 8.0 target in QEMU
* How a library's own CMake tests can run on a QNX target over ssh
* How to read a QNX core dump with the SDP's gdb, and what a `printf("%s", NULL)` crash looks like on QNX
* Why socket code on QNX links with `-l socket`

**Prerequisites:**

* Ubuntu 22.04 or 24.04, or Windows 11 with WSL2 Ubuntu 22.04. QNX's `mkqnximage` runs QEMU targets on Ubuntu.
* QNX SDP 8.0 installed at `~/qnx800` with the free non-commercial licence. QNX's codelab
  [Get a non-commercial QNX licence](https://qnx.github.io/codelabs/get-non-commercial-qnx-license/index.html)
  and steps 1 to 3 of our [SETUP.md](https://github.com/thegoodengineers/qnx-porter/blob/main/SETUP.md) cover
  this (about 30 minutes, mostly downloads). It is not counted in the durations here.
* 20 GB of free disk and about 2 GB of free RAM for the QEMU target.
* You have built a C project with CMake before.

**How to read this codelab:** **[host]** means your Ubuntu (or WSL) terminal, inside your `qnx-porter` clone.
**[QNX]** means a shell on the QNX target.

<aside class="positive">
Every "you should see" block is copied from a real run on QNX 8.0, and each one names the file in the repository
it comes from. Our paths contain <code>/home/chirag</code>; yours will contain your own home folder.
</aside>

This is the focused version. The full reference, with every option, the whole 61-library campaign and how to
write your own porting rule, is the long [qnx-porter codelab](https://github.com/thegoodengineers/qnx-porter/blob/main/docs/CODELAB.md).

---

## Get the cross-compiler and qnx-porter
Duration: 8:00

### Why cross-compile

A QNX system in a car, a robot or a medical device usually has no compiler on it. QNX SDP 8.0 is a
cross-development environment: you build on a Linux or Windows host, for the target's CPU, against the target's
headers and libraries. The compiler driver is `qcc` (`q++` for C++). Its `-V` option picks the compiler and the
target, for example `qcc -Vgcc_ntox86_64` for 64-bit x86 or `qcc -Vgcc_ntoaarch64le` for 64-bit Arm. The headers
and libraries it builds against live under `$QNX_TARGET`, which acts as the sysroot.
QNX 8.0 docs: [qcc, q++](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/q/qcc.html).

### Install the host tools and qnx-porter

**[host]**
```bash
sudo apt update && sudo apt install -y build-essential cmake ninja-build meson autoconf automake libtool \
  pkg-config git python3 python3-pip qemu-system-x86 qemu-utils bridge-utils net-tools openssh-client \
  protobuf-compiler tcl
git clone https://github.com/thegoodengineers/qnx-porter && cd qnx-porter
python3 -m pip install --user --upgrade pip   # Ubuntu 22.04's pip 22 cannot do editable installs
python3 -m pip install --user -e ".[test]"
```

`~/.local/bin` must be on your `PATH` for the `qnx-porter` command after a `--user` install.

### Load the SDP environment

**[host]**
```bash
source ~/qnx800/qnxsdp-env.sh
qcc -V
```

`qnxsdp-env.sh` sets `QNX_HOST` (the host tools, including `qcc`) and `QNX_TARGET` (the target sysroot). The
`qcc -V` list must include `gcc_ntox86_64`. Add the `source` line to `~/.bashrc` so every new terminal has it.

---

## Boot QNX 8.0 in QEMU with mkqnximage
Duration: 10:00

### What mkqnximage builds

`mkqnximage` is the SDP's tool that generates a bootable QNX OS virtual machine image for VMware, VirtualBox,
QEMU or the QNX hypervisor, for x86_64 or aarch64le. The image has an image filesystem (IFS) that the system boots
from, a `/system` partition for binaries and configuration, and a writable `/data` partition. You customise an
image with *snippet* files in `local/snippets/`; for example `ifs_files.custom` adds files to the IFS. The
`--ssh-ident` option puts your public key in the image, so you can log in as `root` over ssh without a password.
QNX 8.0 docs: [mkqnximage](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/m/mkqnximage.html).

`scripts/qemu_target.sh` wraps it. Its `build` command runs:
```bash
mkqnximage --noprompt --type=qemu --arch="$ARCH" --ip="$IP" --hostname="qnx-porter-$ARCH" \
    --ssh-ident="$HOME/.ssh/id_ed25519.pub" --data-size=5000 --data-inodes=40000 --ram=2G --cpu=4
```
and then adds one snippet line: SDP 8.0's sshd also needs `/usr/libexec/sshd-auth`, which this `mkqnximage` does
not copy into the image. Without it, sshd exits at boot and ssh is refused.

### Build and boot the target

**[host]**
```bash
sudo scripts/qemu_target.sh net "$USER"   # once per boot (on WSL: after every `wsl --shutdown`)
scripts/qemu_target.sh build              # makes the image in ~/qnx-images/qemu
scripts/qemu_target.sh start              # boots headless, waits for ssh, prints the target's uname -a
```

`net` creates the `br0` bridge with QNX's own `qemu/net.sh` and starts a DHCP and DNS server on it. `start`
boots QEMU headless (`mkqnximage --run=-h`) and prints the target's `uname -a` once ssh answers. The target is at
`172.31.1.11`.

You should see a `uname -a` line like ours. This is how our campaign recorded our target in
[`results/runs/campaign-7.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/results/runs/campaign-7.log):
```
target: QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
```
(Our image was built with the host name `qnx-porter`; the script now names it `qnx-porter-x86_64`.)

### Checkpoint

**[host]**
```bash
qnx-porter doctor --target root@172.31.1.11
```

`doctor` checks the SDP install, the host tools and the target. Every line must start with `ok`, and the last line
is `all checks passed`. A `BAD` line names what is missing, usually with a `fix:` line under it.

<aside class="negative">
The target takes 2 GB of RAM (<code>--ram=2G</code>). On WSL, QEMU is started with <code>setsid</code> so it
outlives the shell that started it, and a sleeping laptop pauses WSL, QEMU and every test with it.
</aside>

---

## Port json-c with one command
Duration: 5:00

**[host]**
```bash
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 \
  --target root@172.31.1.11 --no-model
```

`--no-model` uses only qnx-porter's deterministic rules; no language model is called.

You should see (from
[`results/runs/campaign-7.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/results/runs/campaign-7.log),
printed by the same porting function the `port` command calls; long lines are cut in the log itself):
```
[1/5] fetch https://github.com/json-c/json-c.git @ json-c-0.18-20240915
[2/5] build system: cmake; target: x86_64-pc-nto-qnx8.0.0
[3/5] build OK after 1 round(s)
[4/5] tests on target root@172.31.1.11:22 (QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64)
      24/25 tests passed
      fix 0001 [printf-null] Crash on QNX: printf() at tests/test_json_patch.c:31 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C lea
      after crash fixes: 25/25 tests passed
[5/5] report: /home/chirag/qnx-porter/ports/json-c/REPORT.md
```

What happened, in five stages:

1. **fetch:** a shallow clone of json-c at the tag. Every later change is a diff against that upstream tag.
2. **build system:** json-c has a `CMakeLists.txt`, so it is a CMake build, for the target `x86_64-pc-nto-qnx8.0.0`.
3. **build:** configure and build with `qcc`. json-c needed no change to build: it builds in one round.
4. **tests on target:** 24 of 25 tests pass on QNX. One crashes, qnx-porter reads the crash, patches it and
   runs the tests again: 25/25.
5. **report:** everything is in `ports/json-c/`: `REPORT.md`, `qnx.patch`, the toolchain file and `logs/`.

The next three steps open up stages 3, 4 and the crash.

---

## Read the toolchain file: cross-compiling with qcc
Duration: 5:00

CMake cross-compiles when a *toolchain file* tells it the target system, the compilers and the sysroot. Most
upstream projects ship none for QNX. qnx-porter wrote one for json-c.

**[host]**
```bash
cat ports-2024/json-c/qnx-toolchain.cmake
```

The start of ours
([`ports-2024/json-c/qnx-toolchain.cmake`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports-2024/json-c/qnx-toolchain.cmake)):
```
# Generated by qnx-porter for QNX SDP 8.0, x86_64.
set(CMAKE_SYSTEM_NAME QNX)
set(CMAKE_SYSTEM_VERSION 8.0.0)
set(CMAKE_SYSTEM_PROCESSOR x86_64)
set(CMAKE_C_COMPILER "/home/chirag/qnx800/host/linux/x86_64/usr/bin/qcc")
set(CMAKE_C_COMPILER_TARGET gcc_ntox86_64)
set(CMAKE_CXX_COMPILER "/home/chirag/qnx800/host/linux/x86_64/usr/bin/q++")
set(CMAKE_CXX_COMPILER_TARGET gcc_ntox86_64_cxx)
set(CMAKE_SYSROOT "/home/chirag/qnx800/target/qnx")
```

* `CMAKE_SYSTEM_NAME QNX` is what makes CMake treat the build as a cross-compile for QNX.
* `qcc` with `CMAKE_C_COMPILER_TARGET gcc_ntox86_64` is the same choice as `qcc -Vgcc_ntox86_64` on the command line.
* `CMAKE_SYSROOT` is your `$QNX_TARGET`: QNX's headers and libraries, not your host's.
* Further down, the `CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY` and `..._INCLUDE ONLY` lines keep CMake from finding
  host libraries, and `-g` adds debug information (the same code) so a crash on the target has file and line
  numbers in its backtrace.

CMake docs: [cmake-toolchains](https://cmake.org/cmake/help/latest/manual/cmake-toolchains.7.html).

Check which compiler CMake used. **[host]**
```bash
grep "C compiler" ports-2024/json-c/logs/round-01.log
```

From our
[`ports-2024/json-c/logs/round-01.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports-2024/json-c/logs/round-01.log):
```
-- The C compiler identification is QCC 12.2.0
-- Detecting C compiler ABI info
-- Detecting C compiler ABI info - done
-- Check for working C compiler: /home/chirag/qnx800/host/linux/x86_64/usr/bin/qcc - skipped
```

---

## Run the library's own tests on QNX over ssh
Duration: 7:00

### Why the tests run over ssh

The binaries you just built are QNX binaries: your Linux host cannot run them. The QNX target, in turn, has no
CMake and no `ctest`. So the test list stays on the host and every test command runs on the target over ssh.

* The image runs an OpenSSH server, and `--ssh-ident` put your key in it. QNX 8.0 docs:
  [ssh](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/s/ssh.html) and
  [sshd](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/s/sshd.html).
* qnx-porter copies the source and build trees to `/data/qnx-porter` on the target and links them into place
  with QNX's `ln -sP`, so they appear at the same absolute paths as on the host. Test scripts that contain host
  paths still work.
* It asks ctest for the test list (`ctest --show-only=json-v1`) and runs each test's command on QNX, under the
  target's own `timeout -s KILL`, so a hung test cannot hold the session.
* CMake has a hook for this, [`CMAKE_CROSSCOMPILING_EMULATOR`](https://cmake.org/cmake/help/latest/variable/CMAKE_CROSSCOMPILING_EMULATOR.html),
  and qnx-porter sets it. But it never wraps a test whose command is a script, and json-c's tests are shell
  scripts (`test1.test`). That
  is why qnx-porter reads the list and runs every command on QNX itself (`ctest_on_target()` in
  [`qnx_porter/target.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/target.py)).

### Look at the test log

**[host]**
```bash
head -3 ports-2024/json-c/logs/tests.log
```

From our
[`ports-2024/json-c/logs/tests.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports-2024/json-c/logs/tests.log)
(the log of the last test run, after the crash fix):
```
$ ctest --show-only=json-v1 (in /home/chirag/qnx-porter/ports/json-c/work/build); every test command runs on root@172.31.1.11 over ssh
PASS  test1 (exit 0)
PASS  test2 (exit 0)
```
and its last line is:
```
25/25 tests passed on the QNX target
```

### Checkpoint

**[host]**
```bash
ssh root@172.31.1.11 uname -a
```

This prints the same QNX `uname -a` line that `start` printed: the machine that ran the tests is QNX 8.0.

---

## Read a QNX core dump with the SDP's gdb
Duration: 10:00

One json-c test, `test_json_patch`, died with a memory fault on QNX. Here is how to find out why.

### Where QNX puts a core dump

QNX's `dumper` runs in the background and writes a dump of any program that terminates abnormally, named after
the program with a `.core` extension. QNX 8.0 docs:
[dumper](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/d/dumper.html). The image
`mkqnximage` built for us runs `dumper -d /data/var/dumper`, so a crash leaves `<program>.core` there
([docs/LEARNINGS.md](https://github.com/thegoodengineers/qnx-porter/blob/main/docs/LEARNINGS.md), 12 Nov).
After the tests, qnx-porter copies each new core to `ports/json-c/work/cores/` on the host.

### Read the backtrace

The SDP ships a gdb for each target. QNX's docs name it `ntox86_64-gdb` for x86_64 and `ntoaarch64-gdb` for
aarch64 (QNX 8.0 docs: [gdb](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/g/gdb.html)).
In our SDP 8.0 install the x86_64 one is `$QNX_HOST/usr/bin/x86_64-nto-qnx8.0.0-gdb`. It runs on the host, reads
the core together with the binary, and needs QNX's target libraries to name the frames inside libc. This is the
command qnx-porter ran (from
[`qnx_porter/crash.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/crash.py)); use it on
your own next crash, with the binary that crashed and its core:
```bash
$QNX_HOST/usr/bin/x86_64-nto-qnx8.0.0-gdb -q -batch \
  -ex "set solib-search-path $QNX_TARGET/x86_64/lib:$QNX_TARGET/x86_64/usr/lib" \
  -ex "bt 12" <binary> <binary>.core
```

qnx-porter saved what gdb printed for json-c. **[host]**
```bash
cat ports-2024/json-c/logs/crashes.log
```

From our
[`ports-2024/json-c/logs/crashes.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports-2024/json-c/logs/crashes.log)
(gdb prints frame #0 twice):
```
=== /home/chirag/qnx-porter/ports/json-c/work/build/tests/test_json_patch
Core was generated by `/data/qnx-porter/home/chirag/qnx-porter/ports/json-c/work/build/tests/test_json_patch'.
Program terminated with signal SIGSEGV, Segmentation fault.
#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#0  strlen () at /builds/workspace/QNXOS_805/build_x86_64/lib/c/public/private/x86_64/strlen.si:65
#1  0x00000035a647108d in _Putfld (px=px@entry=0x5590af72a0, pap=<optimized out>, code=<optimized out>, ac=ac@entry=0x5590af7450 ": J\2465") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xputfld.c:261
#2  0x00000035a6470378 in _Printf (pfn=<optimized out>, arg=arg@entry=0x35a64b2260 <_Stdout>, fmt=<optimized out>, fmt@entry=0x18b4134fc8 "Testing '%s', doc '%s' patch '%s' : ", ap_arg=ap_arg@entry=0x5590af74e0, secure=secure@entry=0) at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/xprintf.c:603
#3  0x00000035a646ad7c in printf (fmt=fmt@entry=0x18b4134fc8 "Testing '%s', doc '%s' patch '%s' : ") at /builds/workspace/QNXOS_805/build_x86_64/lib/c/stdio/printf.c:37
#4  0x00000018b412cc07 in test_json_patch_op (jo=0x2552e24c40) at /home/chirag/qnx-porter/ports/json-c/work/src/tests/test_json_patch.c:31
#5  0x00000018b412cf47 in test_json_patch_using_file (testdir=testdir@entry=0x5590af7c95 "/home/chirag/qnx-porter/ports/json-c/work/src/tests", filename=filename@entry=0x18b4134b67 "json_patch_tests.json") at /home/chirag/qnx-porter/ports/json-c/work/src/tests/test_json_patch.c:91
#6  0x00000018b412c9ee in main (argc=<optimized out>, argv=<optimized out>) at /home/chirag/qnx-porter/ports/json-c/work/src/tests/test_json_patch.c:125
```

Read it from the bottom up. `main` calls `test_json_patch_op`, which calls `printf` at `test_json_patch.c:31`
with the format `"Testing '%s', doc '%s' patch '%s' : "`. Inside QNX's libc, `printf` formats a `%s` field
(`_Putfld`) and calls `strlen` on the string, which faults. A fault in `strlen` under `printf` means a `%s`
argument was NULL.

### Why this works on Linux and crashes on QNX

C leaves `printf("%s", NULL)` undefined. glibc prints `(null)`. QNX's `printf()` page warns that QNX does not
check its arguments for NULL, and that the result is typically a SIGSEGV. QNX 8.0 docs:
[printf()](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/p/printf.html). json-c's
own expected output for this test contains `Testing '(null)', ...`: the test was written against glibc's
behaviour. json-c's library code is fine; the test is glibc-only.

### The fix

**[host]**
```bash
cat ports/json-c/patches/0001-printf-null-test-json-patch-c.patch
```

From our
[`ports/json-c/patches/0001-printf-null-test-json-patch-c.patch`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports/json-c/patches/0001-printf-null-test-json-patch-c.patch):
```
Subject: [qnx-porter 0001] printf-null
Source: deterministic rule
Reason: Crash on QNX: printf() at tests/test_json_patch.c:31 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C leaves it undefined. Each %s argument of that call now goes through qnx_porter_str(), which prints "(null)" like glibc.
Error: Memory fault (SIGSEGV) in strlen <- printf on QNX
---
diff --git a/tests/test_json_patch.c b/tests/test_json_patch.c
index eeb791c..f1811e6 100644
--- a/tests/test_json_patch.c
+++ b/tests/test_json_patch.c
@@ -12,6 +12,9 @@
 #include "json.h"
 #include "snprintf_compat.h"
 
+/* qnx-porter: glibc prints "(null)" for a NULL %s argument; QNX's libc faults (it is undefined C). */
+static const char *qnx_porter_str(const char *s) { return s ? s : "(null)"; }
+
 #ifndef PATH_MAX
 #define PATH_MAX 256
 #endif
@@ -29,9 +32,9 @@ void test_json_patch_op(struct json_object *jo)
 	int ret;
 
 	printf("Testing '%s', doc '%s' patch '%s' : ",
-		comment ? comment : error_s,
-		json_object_get_string(doc),
-		json_object_get_string(patch));
+		qnx_porter_str(comment ? comment : error_s),
+		qnx_porter_str(json_object_get_string(doc)),
+		qnx_porter_str(json_object_get_string(patch)));
 	if (!error && !have_expected) {
 		printf("BAD TEST - no expected or error conditions in test: %s\n", json_object_to_json_string(jo));
 		assert(0);
```

Every patch names its rule, its reason and the error it answers, so a reviewer can accept or reject it on its
own. This one is kept only because the test run after the rebuild passed more tests (25/25 instead of 24/25);
otherwise qnx-porter reverts it.

<aside class="negative">
Do not "fix" a crash like this by changing QNX or by ignoring the test. The fix belongs in the code that relies on
undefined behaviour, here a test of json-c.
</aside>

---

## A library that needs libsocket: mbedtls
Duration: 10:00

### Sockets live in libsocket on QNX

On Linux, `socket()`, `connect()`, `inet_pton()` and the rest are in glibc, so nobody writes `-lsocket`. On QNX
8.0 the socket API comes from the io-sock networking stack (ported from FreeBSD) and you link it as `libsocket`:
`-l socket` on the `qcc` command line. QNX 8.0 docs:
[Socket API (io-sock)](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.io_sock/topic/socket_api.html)
and the [C library summary](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/summary.html),
whose example of linking a library is `-l socket`.

A Linux-first CMake project builds every object fine and then fails at the link with `undefined reference`.

### Port mbedtls

**[host]**
```bash
qnx-porter port https://github.com/Mbed-TLS/mbedtls.git --tag v3.6.2 --arg -DENABLE_PROGRAMS=OFF \
  --target root@172.31.1.11 --no-model
```

`--arg` passes a configure option to CMake; `-DENABLE_PROGRAMS=OFF` is what our campaign uses for mbedtls. Our
port took 4.6 minutes.

You should see (from
[`results/runs/campaign-7.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/results/runs/campaign-7.log)):
```
[1/5] fetch https://github.com/Mbed-TLS/mbedtls.git @ v3.6.2
[2/5] build system: cmake; target: x86_64-pc-nto-qnx8.0.0
      round 1: 26 error(s); first: /home/chirag/qnx-porter/ports/mbedtls/work/src/library/x509_crt.c:2867:(.text+0x843): undefined reference to `__inet_pton'
      fix 0001 [link-libsocket] `__inet_pton` is in QNX's libsocket, not in libc as on Linux: link with -lsocket.
[3/5] build OK after 2 round(s)
[4/5] tests on target root@172.31.1.11:22 (QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64)
      130/130 tests passed
[5/5] report: /home/chirag/qnx-porter/ports/mbedtls/REPORT.md
```

The linker asks for `__inet_pton`, not `inet_pton`: QNX's `<arpa/inet.h>` defines `inet_pton` as
`__inet_pton`, and `__inet_pton` is in libsocket (row 14c of our
[rule corpus](https://github.com/thegoodengineers/qnx-porter/blob/main/docs/LINUX_ISMS.md)).

### The fix

**[host]**
```bash
cat ports-2024/mbedtls/patches/0001-link-libsocket.patch
```

From our
[`ports-2024/mbedtls/patches/0001-link-libsocket.patch`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports-2024/mbedtls/patches/0001-link-libsocket.patch):
```
Subject: [qnx-porter 0001] link-libsocket
Source: deterministic rule
Reason: `__inet_pton` is in QNX's libsocket, not in libc as on Linux: link with -lsocket.
Error: /home/chirag/qnx-porter/ports/mbedtls/work/src/library/x509_crt.c:2867:(.text+0x843): undefined reference to `__inet_pton'
---
--- a/qnx-toolchain.cmake
+++ b/qnx-toolchain.cmake
@@ -19,5 +19,5 @@
 set(CMAKE_SHARED_LINKER_FLAGS_INIT "-L/home/chirag/qnx-porter/ports/mbedtls/work/stubs")
 # Flags after the project's own (appended by the compiler wrappers in -): none
 # Libraries the agent adds go at the end of every link line, after the objects that need them.
-set(CMAKE_C_STANDARD_LIBRARIES "")
-set(CMAKE_CXX_STANDARD_LIBRARIES "")
+set(CMAKE_C_STANDARD_LIBRARIES "-lsocket")
+set(CMAKE_CXX_STANDARD_LIBRARIES "-lsocket")
```

The fix is in the toolchain file, not in mbedtls's source. `CMAKE_C_STANDARD_LIBRARIES` goes at the end of every
link line, after the objects that need it, which is where a static link wants it. All 130 of mbedtls's own test
suites then passed on QNX.

---

## Optional: the same port on aarch64 on QEMU
Duration: 10:00

QNX 8.0 also runs on 64-bit Arm. The SDP cross-compiles for it (`gcc_ntoaarch64le`), and `mkqnximage` can build an
aarch64 image for QEMU's `virt` machine. This is aarch64 on QEMU, fully emulated, not hardware, so it is slower.

You need the SDP's qemuvirt BSP package (from the QNX Software Center) and QEMU for Arm.

**[host]**
```bash
sudo apt install -y qemu-system-arm
QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh build   # image in ~/qnx-images/qemu-aarch64le
QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh start   # 172.31.1.12, next to the x86_64 target
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 \
  --arch aarch64le --out ports-aarch64le --target root@172.31.1.12 --no-model
```

`--out ports-aarch64le` keeps the aarch64 port next to the x86_64 one instead of replacing it.

You should see (from
[`results/runs/campaign-aarch64-2.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/results/runs/campaign-aarch64-2.log)):
```
[1/5] fetch https://github.com/json-c/json-c.git @ json-c-0.18-20240915
[2/5] build system: cmake; target: aarch64-unknown-nto-qnx8.0.0
[3/5] build OK after 1 round(s)
[4/5] tests on target root@172.31.1.12:22 (QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le)
      24/25 tests passed
      fix 0001 [printf-null] Crash on QNX: printf() at tests/test_json_patch.c:31 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C lea
      after crash fixes: 25/25 tests passed
[5/5] report: /home/chirag/qnx-porter/ports-aarch64le/json-c/REPORT.md
```

The same test crashes the same way. In the aarch64 core the top frame is `__generic_strlen`, aarch64 libc's
`strlen` ([`ports-aarch64le/json-c/logs/crashes.log`](https://github.com/thegoodengineers/qnx-porter/blob/main/ports-aarch64le/json-c/logs/crashes.log)).
Our aarch64 port took 8.1 minutes, against 0.8 minutes on x86_64 under KVM (the `Time` rows of the two
`REPORT.md` files).

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `QNX SDP 8.0 not found` | the SDP environment was not loaded | `source ~/qnx800/qnxsdp-env.sh` |
| `doctor`: `BAD SDP complete` | an interrupted install left empty files | repair or reinstall SDP 8.0 in the Software Center |
| `start` prints `QNX target did not answer ssh` | no bridge, or QEMU failed to boot | `sudo scripts/qemu_target.sh net "$USER"`, then read `~/qnx-images/qemu/output/qemu.out` |
| `ssh: connect ... refused` or a timeout | QEMU is not running or still booting | `scripts/qemu_target.sh status`; if it prints nothing, `scripts/qemu_target.sh start` |
| `Permission denied (publickey)` | the image was built without your key | delete `~/qnx-images/qemu` and run `scripts/qemu_target.sh build` again |
| Tests fail with "No space left" | `/data` is too small | raise `--data-size` in `scripts/qemu_target.sh`, delete `~/qnx-images/qemu`, run `build` again |
| A library ends `failed` | something no rule handles | read "Still failing" in its `REPORT.md` |

---

## Summary and next steps
Duration: 2:00

You cross-compiled a Linux-first CMake library for QNX 8.0 and ran its own tests on a QNX 8.0 target.

**What you have learned:**

* QNX code is cross-compiled: `qcc -V<target>` against the sysroot in `$QNX_TARGET`, and a CMake toolchain file
  with `CMAKE_SYSTEM_NAME QNX` carries that into any CMake project.
* `mkqnximage` builds a bootable QNX image with an IFS, `/system` and `/data`, customised with snippet files.
* A QNX target has no build tools, so the tests stay listed on the host and run on QNX over ssh.
* QNX's `dumper` writes a core for every crash, and the SDP's gdb reads it on the host. `strlen` under `printf`
  means a NULL `%s`, which glibc prints as `(null)` and QNX does not.
* Socket functions are in `libsocket` on QNX: link with `-l socket`.

When you are done, stop the target. **[host]**
```bash
scripts/qemu_target.sh stop
```

**Next steps:**

* Build the port without qnx-porter: `ports/json-c/qnx.patch` applies to the upstream tag with `git apply`, and
  `ports-2024/json-c/qnx-toolchain.cmake` is a normal CMake toolchain file. Step 5 of the
  [full qnx-porter codelab](https://github.com/thegoodengineers/qnx-porter/blob/main/docs/CODELAB.md) shows how.
* Port your own library: `qnx-porter port <git URL> --tag <tag> --target root@172.31.1.11`. The full codelab also
  covers teaching qnx-porter a new rule, porting a whole list of libraries with `scripts/run_campaign.py`, and
  handing a port to QNX's [qnx-ports/build-files](https://github.com/qnx-ports/build-files).
* Every QNX difference qnx-porter knows, with its source, is a row in
  [docs/LINUX_ISMS.md](https://github.com/thegoodengineers/qnx-porter/blob/main/docs/LINUX_ISMS.md).
* QNX's own codelab [Cross-compile for QNX Using Open Source Packages](https://qnx.github.io/codelabs/apk-based-cross-compile/index.html)
  shows how to use QNX's prebuilt open-source packages in a `qcc` sysroot.

Questions or problems: open an issue at https://github.com/thegoodengineers/qnx-porter/issues.
