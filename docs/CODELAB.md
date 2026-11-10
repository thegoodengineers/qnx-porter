# Codelab: port an open-source C library to QNX 8.0 with qnx-porter

**You will:** install QNX SDP 8.0 and boot QNX 8.0 in QEMU, port a real library with one command, read
every change the tool made and why, run the library's own tests on QNX, and teach the tool a new rule.

| | |
|---|---|
| Time | about 90 minutes; 45 of them are downloads and installs |
| Host | Ubuntu 22.04 or 24.04, or Windows 11 with WSL2 Ubuntu 22.04 (QNX's QEMU tooling runs only on Ubuntu) |
| Disk | 20 GB free |
| Accounts | a free myQNX account (QNX Everywhere). No API key is needed except for the optional step 6 |
| Skills | a Linux shell, and having built a C project with CMake once |

Every command block says where to run it. **[host]** means your Ubuntu (or WSL) terminal. **[QNX]** means a
shell on the QNX target. If something does not match what you see, jump to [If something goes wrong](#if-something-goes-wrong).

---

## 1. See the idea without QNX (5 min)
**[host]**
```bash
sudo apt update && sudo apt install -y git python3-pip cmake build-essential
git clone https://github.com/thegoodengineers/qnx-porter && cd qnx-porter
python3 -m pip install -e ".[test]"
qnx-porter selftest
```
You should see:
```
[2/5] build system: cmake; target: host compiler (self-test)
      round 1: 2 error(s); first: .../textutil.c:8:12: error: implicit declaration of function 'strcasecmp' ...
      fix 0001 [add-include] `strcasecmp` is declared in <strings.h> ...
      fix 0002 [no-werror] Warning -Wunused-variable is promoted to an error ...
[3/5] build OK after 2 round(s)
```
This bundled library was "written on Linux": it calls `strcasecmp` without `<strings.h>`. glibc's
`<string.h>` happens to declare it; POSIX puts it in `<strings.h>`, and QNX's libc follows POSIX. Open
`ports-selftest/brokenlib/REPORT.md` and the two files in `ports-selftest/brokenlib/patches/`. Each patch
names its rule, its reason and the exact compiler error it answers. That is the whole product in miniature.

## 2. Install QNX SDP 8.0 (30 min)
1. In a browser: https://qnx.software/en/developers/get-started/qnx-everywhere, then **Get QNX Everywhere**.
   Sign in or create a myQNX account and request the **free non-commercial licence**. It appears under
   *Licenses* in your myQNX account.
2. Download **QNX Software Center for Linux hosts** (`qnx-setup-*-linux.run`).
3. **[host]**
   ```bash
   sudo apt install -y meson ninja-build autoconf automake libtool pkg-config \
     qemu-system-x86 qemu-utils bridge-utils net-tools openssh-client
   chmod +x ~/Downloads/qnx-setup-*-linux.run && ~/Downloads/qnx-setup-*-linux.run
   ~/qnx/qnxsoftwarecenter/qnxsoftwarecenter &
   ```
   (On WSL, copy the installer from `/mnt/c/Users/<you>/Downloads/` first. The window opens through WSLg.)
4. In the Software Center: sign in, add your licence, then **Add Installation**, choose
   **QNX Software Development Platform 8.0**, and keep the default folder **`~/qnx800`**.
5. **[host]** check it:
   ```bash
   source ~/qnx800/qnxsdp-env.sh
   qcc -V
   ```
   The list must include `gcc_ntox86_64`. Add `source ~/qnx800/qnxsdp-env.sh` to `~/.bashrc` so every new
   terminal has it.

## 3. Boot QNX 8.0 in QEMU (10 min)
**[host]**
```bash
ls ~/.ssh/id_ed25519.pub || ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519
mkdir -p ~/qnx-images/qemu && cd ~/qnx-images/qemu
mkqnximage --type=qemu --arch=x86_64 --ip=172.31.1.11 \
  --ssh-ident=$HOME/.ssh/id_ed25519.pub --data-size=5000 --data-inodes=40000
mkqnximage --run=-h
ssh root@172.31.1.11 uname -a
```
The last line should print something like `QNX ... 8.0.0 ... x86_64`. You are now logged in to a real QNX 8.0
system built by QNX's own `mkqnximage` from the SDP you installed. Look around:

**[QNX]** (`ssh root@172.31.1.11`, then)
```sh
pidin | head        # QNX's process list: procnto is the microkernel
df -h /data         # the writable partition qnx-porter copies test builds to
exit
```

Back on the host, check everything qnx-porter needs:

**[host]**
```bash
cd ~/qnx-porter     # or wherever you cloned it in step 1
qnx-porter doctor
```
Every line must start with `ok`. A `BAD` line names what is missing.

## 4. Port a real library (10 min)
json-c is a widely used JSON library that was not on oss.qnx.com when we checked (`results/candidates_check.csv`).

**[host]**
```bash
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 \
  --target root@172.31.1.11 --no-model
```
The log has five stages:
1. **fetch**: a shallow clone at the tag, tagged `qnx-porter-base`, so every later change is a diff against upstream.
2. **build system**: `CMakeLists.txt` was found, so CMake.
3. **build OK / rounds**: build with qcc, parse the errors, apply rules, rebuild. Each `fix` line names its rule.
   A library that is already portable builds in round 1 with no fixes. That is a good result too.
4. **tests on target**: the build tree is copied to `/data/qnx-porter` on QNX, and ctest runs json-c's own
   tests. Each test binary runs **on QNX** through `work/qnx-run`, which the tool passes to CMake as
   `CMAKE_CROSSCOMPILING_EMULATOR`.
5. **report**: `ports/json-c/REPORT.md`.

Open the toolchain the tool generated:
```bash
cat ports/json-c/qnx-toolchain.cmake
```
Find `CMAKE_SYSTEM_NAME QNX`, `qcc` with `CMAKE_C_COMPILER_TARGET gcc_ntox86_64`, and `CMAKE_SYSROOT` set
to your `$QNX_TARGET`. This is the file most upstream projects are missing.

## 5. Review every change, and check one test by hand (10 min)
**[host]**
```bash
cat ports/json-c/REPORT.md
ls ports/json-c/patches/             # one file per change, numbered
cat ports/json-c/qnx.patch           # every kept source change, against the upstream tag
less ports/json-c/logs/round-01.log  # the errors that started it
less ports/json-c/logs/tests.log     # the test run on QNX
```
Each patch begins with:
```
Subject: [qnx-porter 0001] add-include
Source: deterministic rule
Reason: ...
Error: <the exact compiler line>
```
If you disagree with a change, you have the error, the rule and the reason in one place.

Now see for yourself that the tests ran on QNX, not on your host:
```bash
file ports/json-c/work/build/tests/test1     # its interpreter is QNX's dynamic linker (ldqnx...), not ld-linux
ctest --test-dir ports/json-c/work/build -R test1 -V | grep -E "Test command|Passed|Failed"
```
The `Test command` line starts with `.../work/qnx-run`: ctest called the wrapper, the wrapper ran `test1` on
172.31.1.11 over ssh.

Exercise: apply the port to a clean checkout and build it yourself.
```bash
git clone -q --depth 1 --branch json-c-0.18-20240915 https://github.com/json-c/json-c.git /tmp/jc
git -C /tmp/jc apply "$PWD/ports/json-c/qnx.patch"     # no output if the port needed no source change
cmake -S /tmp/jc -B /tmp/jc-build -DCMAKE_TOOLCHAIN_FILE="$PWD/ports/json-c/qnx-toolchain.cmake"
cmake --build /tmp/jc-build -j
```

## 6. Optional: a language model for the long tail (5 min)
Rules handle errors that are always fixed the same way. For the rest, any OpenAI-compatible endpoint works.
**[host]**
```bash
export QNX_PORTER_API_KEY="..."    # your key, in this shell only; never in a file in the repo
export QNX_PORTER_MODEL="..."      # a model ID from your provider's model list
export QNX_PORTER_BASE_URL="..."   # only if your provider is not the default endpoint
qnx-porter port https://github.com/nanomsg/nng.git --tag v1.9.0 --arg -DNNG_TESTS=ON --target root@172.31.1.11
```
The model gets the error, about 65 lines of code around it, and a QNX hint (for example "QNX has no epoll:
use poll()/select(), or ionotify()"). Its diff must pass `git apply --check`. After the rebuild, if the same
error is still there, the tool reverts the patch and the report marks it `reverted`.

## 7. Teach the tool a rule (10 min)
Rules live in `qnx_porter/fixes.py` (small ones) and `qnx_porter/linuxisms.py` (rewrites). The 22 we have,
each with its QNX documentation source, are listed in [LINUX_ISMS.md](LINUX_ISMS.md). Add one:

Say a library calls `getopt()` without `#include <unistd.h>` and the build fails with
`implicit declaration of function 'getopt'`.

1. Write the failing test first, at the end of `tests/test_fixes_and_patches.py`:
   ```python
   def test_getopt_comes_from_unistd(tmp_path):
       (tmp_path / "a.c").write_text('#include <stdio.h>\nint main(int c, char **v) { return getopt(c, v, "x"); }\n')
       [f] = fixes.plan([implicit(sym="getopt")], tmp_path, Flags(), set())
       assert "#include <unistd.h>" in f.edits["a.c"]
   ```
2. `python3 -m pytest -q -k getopt`: it fails (no rule knows `getopt`).
3. Add `"getopt"` to the list that maps to `"unistd.h"` in `SYMBOL_HEADERS` in `qnx_porter/fixes.py`.
4. `python3 -m pytest -q`: everything passes. Add a row to `docs/LINUX_ISMS.md` naming the source.

The bar for a rule: it acts only on what the compiler or linker printed, and the fix never needs judgement.
If it does, it belongs to the model or a person.

## 8. Port the whole campaign with one command
**[host]**
```bash
python3 scripts/run_campaign.py
```
It checks `qcc` and the target first, re-checks oss.qnx.com and skips anything QNX has published since, ports
every library in `campaign.yaml`, and rewrites `results/ports.csv` and the README table from the reports.
Nothing in that table is typed by hand.

When you are done: `cd ~/qnx-images/qemu && mkqnximage --stop`.

## If something goes wrong
| Symptom | Cause | Fix |
|---|---|---|
| `QNX SDP 8.0 not found` | the environment script was not sourced | `source ~/qnx800/qnxsdp-env.sh` |
| `qcc not found at ...` | the SDP is not installed at `QNX_HOST` | redo step 2.4; then `qnx-porter doctor` |
| `doctor`: `BAD x86_64 gcc` | autotools/meson drivers named differently in your SDP | look in `$QNX_HOST/usr/bin` for `*-nto-qnx*-gcc` and report it as an issue |
| `mkqnximage --run` complains about the network | QEMU needs a bridge once | run the `sudo .../net.sh` command it prints |
| `ssh: connect ... refused` / timeout | QEMU not running or still booting | `mkqnximage --run=-h` in `~/qnx-images/qemu`; wait 20 s |
| `Permission denied (publickey)` | image built without your key | rebuild the image with `--ssh-ident=$HOME/.ssh/id_ed25519.pub` |
| `QNX target ... did not answer` from `run_campaign.py` | same as above | or build only: `python3 scripts/run_campaign.py --no-tests` |
| Tests fail with "No space left" | `/data` too small | rebuild the image with a larger `--data-size` |
| A library ends `failed` | something no rule handles | read "Still failing" in its REPORT.md; try step 6, or write a rule (step 7) |

## What you learned
- What QNX 8.0 changes for Linux-first code: POSIX headers, libsocket and libfsnotify, libc-provided
  pthread/rt/dl, `_QNX_SOURCE`, and which Linux-only APIs have QNX equivalents.
- How to cross-compile CMake, Meson and autotools projects with `qcc`, and run their tests on a QNX target.
- How to keep automated changes reviewable: one patch, one reason, one error.
