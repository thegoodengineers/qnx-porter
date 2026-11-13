# Codelab: port an open-source C library to QNX 8.0 with qnx-porter

**You will:** install QNX SDP 8.0 and boot QNX 8.0 in QEMU, port a real library with one command, read
every change the tool made and why, run the library's own tests on QNX, teach the tool a new rule, and then
run the same pipeline on aarch64, through a network outage, into build-files recipes and every week at
upstream HEAD.

| | |
|---|---|
| Time | about 90 minutes for steps 1 to 9; 45 of them are downloads and installs |
| Host | Ubuntu 22.04 or 24.04, or Windows 11 with WSL2 Ubuntu 22.04 (QNX's QEMU tooling runs only on Ubuntu) |
| Disk | 20 GB free |
| Accounts | a free myQNX account (QNX Everywhere). No API key is needed except for the optional step 6 |
| Skills | a Linux shell, and having built a C project with CMake once |

Every command block says where to run it. **[host]** means your Ubuntu (or WSL) terminal, inside your
`qnx-porter` clone. **[QNX]** means a shell on the QNX target. Every "you should see" block is copied from a
real run: `results/runs/*.log`, `ports/<library>/logs/` or `ports/<library>/REPORT.md` in this repository.
If something does not match what you see, jump to [If something goes wrong](#if-something-goes-wrong).

---

## 1. See the idea without QNX (5 min)
**[host]**
```bash
sudo apt update && sudo apt install -y git python3-pip cmake build-essential
git clone https://github.com/thegoodengineers/qnx-porter && cd qnx-porter
python3 -m pip install --user --upgrade pip   # Ubuntu 22.04's pip 22 cannot do editable installs
python3 -m pip install --user -e ".[test]"
qnx-porter selftest
```
You should see (long paths shortened to `...`):
```
[2/5] build system: cmake; target: host compiler (self-test)
      round 1: 2 error(s); first: .../brokenlib/work/src/textutil.c:8:12: error: impl
      fix 0001 [add-include] `strcasecmp` is declared in <strings.h> (that is where QNX declares it); textutil.c did not include it. glibc pulls it in through other headers, QNX's libc does not.
      fix 0002 [no-werror] Warning -Wunused-variable is promoted to an error by the project's -Werror. Keep it a warning (still printed in the build log) instead of editing the library's code; QNX's h
[3/5] build OK after 2 round(s)
[4/5] tests skipped: no --target given
```
This bundled library was "written on Linux": it calls `strcasecmp` without `<strings.h>`. glibc's
`<string.h>` happens to declare it; POSIX puts it in `<strings.h>`, and QNX's libc follows POSIX. Open
`ports-selftest/brokenlib/REPORT.md` and the two files in `ports-selftest/brokenlib/patches/`. Each patch
names its rule, its reason and the exact compiler error it answers. That is the whole product in miniature.
[ARCHITECTURE.md](ARCHITECTURE.md) shows the same loop as a diagram, one box per source file.

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
   The list must include `gcc_ntox86_64` (and `gcc_ntoaarch64le` for step 10). Add
   `source ~/qnx800/qnxsdp-env.sh` to `~/.bashrc` so every new terminal has it.

## 3. Boot QNX 8.0 in QEMU (10 min)
`scripts/qemu_target.sh` wraps QNX's own `mkqnximage` and adds the two fixes SDP 8.0 needed on our machine
(sshd's missing `sshd-auth`, and a DHCP/DNS server on the bridge; SETUP.md step 4 explains both).

**[host]**
```bash
sudo scripts/qemu_target.sh net "$USER"   # once per boot (on WSL: after every `wsl --shutdown`)
scripts/qemu_target.sh build              # makes the image in ~/qnx-images/qemu
scripts/qemu_target.sh start              # boots headless, waits for ssh, prints the target's uname -a
```
`start` ends with the target's `uname -a`. Ours, as `run_campaign.py` recorded it in
`results/runs/campaign-7.log`:
```
target: QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64
```
(Our image was built with the host name `qnx-porter`; the script now names it `qnx-porter-x86_64`.)
The script's other commands are `status` (prints `uname -a` again) and `stop`. You are now on a real QNX 8.0
system built by QNX's `mkqnximage` from the SDP you installed. Look around:

**[QNX]** (`ssh root@172.31.1.11`, then)
```sh
pidin | head        # QNX's process list: procnto is the microkernel
df -h /data         # the writable partition qnx-porter copies test builds to
exit
```

Back on the host, check everything qnx-porter needs:

**[host]**
```bash
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
You should see (from `results/runs/campaign-7.log`; your paths differ):
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
The five stages:
1. **fetch**: a shallow clone at the tag, tagged `qnx-porter-base`, so every later change is a diff against upstream.
2. **build system**: `CMakeLists.txt` was found, so CMake.
3. **build OK / rounds**: build with qcc, parse the errors, apply rules, rebuild. Each `fix` line names its
   rule. json-c builds in one round. A library that is already portable is a good result too; port `yyjson`
   (tag `0.10.0`, `--arg -DYYJSON_BUILD_TESTS=ON`) to watch a rule fire:
   ```
         round 1: 14 error(s); first: /home/chirag/qnx-porter/ports/yyjson/work/src/test/test_json_writer.c:15:(.text+0xd5): undefined reference to `__isinf'
         fix 0001 [link-libm] `__isinf` is in QNX's libm, not in libc: QNX's <math.h> implements isinf/isfinite/isnan as calls to __isinf etc. in libm, where glibc needs no library. Link with -lm.
   [3/5] build OK after 2 round(s)
   ```
4. **tests on target**: the build tree is copied to `/data/qnx-porter` on QNX, and every test ctest knows
   about runs **on QNX** over ssh.
5. **report**: `ports/json-c/REPORT.md`.

One test crashed on QNX ("Memory fault"). The agent copied the core dump from the target, read it with the
SDP's gdb (`logs/crashes.log`), saw `strlen <- printf`, and found the cause: the test prints a NULL string with
`%s`, which glibc prints as `(null)` and QNX's libc does not. It patched the call, rebuilt and re-ran, and kept
the patch because more tests passed. See [LINUX_ISMS.md](LINUX_ISMS.md) row 14g.

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
less ports/json-c/logs/round-01.log  # the build log of round 1
less ports/json-c/logs/tests.log     # the test run on QNX
```
Each patch begins like this one (`ports/json-c/patches/0001-printf-null-test-json-patch-c.patch`):
```
Subject: [qnx-porter 0001] printf-null
Source: deterministic rule
Reason: Crash on QNX: printf() at tests/test_json_patch.c:31 formats a NULL pointer with %s (backtrace: strlen <- printf). glibc prints "(null)" for that, QNX's libc faults; C leaves it undefined. Each %s argument of that call now goes through qnx_porter_str(), which prints "(null)" like glibc.
Error: Memory fault (SIGSEGV) in strlen <- printf on QNX
```
If you disagree with a change, you have the error, the rule and the reason in one place.

Now see for yourself that the tests ran on QNX, not on your host:
```bash
file ports/json-c/work/build/tests/test1     # its interpreter is QNX's /usr/lib/ldqnx-64.so.2
head -3 ports/json-c/logs/tests.log
ssh root@172.31.1.11 ls -l /home            # a QNX path-space link to /data/qnx-porter/home
```
`tests.log` starts like this:
```
$ ctest --show-only=json-v1 (in /home/chirag/qnx-porter/ports/json-c/work/build); every test command runs on root@172.31.1.11 over ssh
PASS  test1 (exit 0)
PASS  test2 (exit 0)
```
and ends with `25/25 tests passed on the QNX target`. json-c's tests are shell scripts; CMake's
cross-compiling emulator never wraps scripts, which is why qnx-porter reads ctest's test list and runs every
command on QNX itself (`ctest_on_target()` in `qnx_porter/target.py`).

Exercise: apply the port to a clean checkout and build it yourself.
```bash
git clone -q --depth 1 --branch json-c-0.18-20240915 https://github.com/json-c/json-c.git /tmp/jc
git -C /tmp/jc apply "$PWD/ports/json-c/qnx.patch"
cmake -S /tmp/jc -B /tmp/jc-build -DCMAKE_TOOLCHAIN_FILE="$PWD/ports/json-c/qnx-toolchain.cmake"
cmake --build /tmp/jc-build -j
```

## 6. Optional: a language model for the long tail (5 min)
Rules handle errors that are always fixed the same way. For the rest, any endpoint that speaks the common
chat-completions API works. **[host]**
```bash
export QNX_PORTER_API_KEY="..."    # your key, in this shell only; never in a file in the repo
export QNX_PORTER_MODEL="..."      # a model ID from your provider's model list
export QNX_PORTER_BASE_URL="..."   # your provider's base URL (the part before /chat/completions)
qnx-porter port https://github.com/nanomsg/nng.git --tag v1.9.0 --arg -DNNG_TESTS=ON --target root@172.31.1.11
```
`QNX_PORTER_TEMPERATURE` and `QNX_PORTER_MAX_TOKENS` are optional and sent only when set. The model gets the
error, the code around it (40 lines above, 25 below), the end of the build log and a QNX hint (for example
"QNX has no epoll: use poll()/select(), or ionotify() for event delivery"). Its diff must pass
`git apply --check`. After the rebuild, if the same error is still there, or new errors appear in the files
it touched, the tool reverts the patch and the report marks it `reverted`. `--no-model` turns the step off.
All our published results used rules only.

## 7. Teach the tool a rule (10 min)
Rules live in `qnx_porter/fixes.py` (small ones) and `qnx_porter/linuxisms.py` (rewrites). Every one we have,
each with its QNX documentation source or the real build that found it, is a row in
[LINUX_ISMS.md](LINUX_ISMS.md). Add one:

Say a library calls `getopt()` without `#include <unistd.h>` and the build fails with
`implicit declaration of function 'getopt'`.

1. Write the failing test first, at the end of `tests/test_fixes_and_patches.py`:
   ```python
   def test_getopt_comes_from_unistd(tmp_path):
       (tmp_path / "a.c").write_text('#include <stdio.h>\nint main(int c, char **v) { return getopt(c, v, "x"); }\n')
       [f] = fixes.plan([implicit(sym="getopt")], tmp_path, Flags(), set())
       assert "#include <unistd.h>" in f.edits["a.c"]
   ```
2. `python3 -m pytest -q -k getopt`: it fails (no rule knows `getopt`, so `plan()` returns nothing).
3. Add `"getopt"` to the list that maps to `"unistd.h"` in `SYMBOL_HEADERS` in `qnx_porter/fixes.py`.
4. `python3 -m pytest -q`: everything passes. Add a row to `docs/LINUX_ISMS.md` naming the source.

The bar for a rule: it acts only on what the compiler or linker printed, and the fix never needs judgement.
If it does, it belongs to the model or a person.

## 8. Port the whole campaign with one command
**[host]**
```bash
python3 scripts/run_campaign.py
```
It checks `qcc` and the target first, notes which libraries oss.qnx.com already lists, ports every library in
`campaign.yaml` (61 of them; each library's minutes are in the `minutes` column of `results/ports.csv`), and
rewrites `results/ports.csv`, the README table and the README headline from the reports. Nothing in that table
is typed by hand. The last lines of our final run (`results/runs/campaign-7.log`):
```
x86_64: 61 libraries, 57 built for QNX 8.0; tests ran for 33 (at least one test each): 1332/1366 passed
-> /home/chirag/qnx-porter/results/ports.csv
```

Every switch `run_campaign.py` has:

| Switch | What it does |
|---|---|
| `--only zlib,expat` | port only these libraries (comma-separated names from `campaign.yaml`) |
| `--arch aarch64le` | build for 64-bit Arm instead of `campaign.yaml`'s `arch`; results go to `ports-aarch64le/` |
| `--target root@HOST[:PORT]` | the QNX target for tests; `--target none` builds only |
| `--no-tests` | build only, never touch the target |
| `--no-model` | rules only, even if `QNX_PORTER_*` is set |
| `--skip-oss-check` | do not re-query oss.qnx.com before the run |
| `--head` | port each library's upstream default branch instead of its pinned tag (step 13) |
| `--out DIR` | where the port folders go (default `ports/`, or `ports-<arch>/`) |
| `--campaign FILE` | another library list instead of `campaign.yaml` |

`QNX_PORTER_JOBS=2 python3 scripts/run_campaign.py` limits parallel compiles (the QEMU target already takes
2 GB of RAM).

## 9. Find the QNX difference behind a failing test (15 min)
A failing test after a clean build is the interesting case: either the test assumes glibc, or QNX behaves
differently. Take googletest's death tests, which abort on QNX 8.0.

1. Read the backtrace the agent took from the core dump:
   ```bash
   grep -A8 googletest-death-test-test ports/googletest/logs/crashes.log
   ```
   It shows `SIGABRT`, then `DeathTestAbort` and below it `ExecDeathTestSpawnChild`, a QNX-only code path in
   googletest.
2. Find the check that failed. The message is in the core; `docs/qnx-reports/fchdir-o-rdonly.md` shows how we
   read it with the SDP's gdb: `fchdir(cwd_fd) != -1`.
3. Reduce it to a few lines and run them on both systems:
   ```bash
   qcc -Vgcc_ntox86_64 docs/qnx-reports/fchdir_test.c -o /tmp/fchdir_test
   scp /tmp/fchdir_test root@172.31.1.11:/data/ && ssh root@172.31.1.11 /data/fchdir_test
   gcc docs/qnx-reports/fchdir_test.c -o /tmp/fchdir_host && /tmp/fchdir_host
   ```
   On QNX, `fchdir()` on a directory opened with `open(".", O_RDONLY)` fails with "Not a directory"; with
   `O_DIRECTORY` it works. On Linux both work.
4. Check QNX's documentation, then decide where the fix belongs. QNX's
   [`fchdir()` page](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.lib_ref/topic/f/fchdir.html)
   lists ENOTDIR for a descriptor not opened with `O_DIRECTORY`, so this is intended QNX behaviour and the fix
   belongs in googletest: a one-line patch (`docs/qnx-reports/googletest-qnx-fchdir.patch`), checked on the
   target as the report describes.

The same method found every report in [docs/qnx-reports/](qnx-reports/): `strtod()` rounding, `strftime()`
with `%Ex`, and a libsrtp test that sorts with a random comparator.

## 10. The same pipeline on aarch64 on QEMU
QNX 8.0 also runs on 64-bit Arm. The SDP cross-compiles for it (`gcc_ntoaarch64le`), and `mkqnximage` can boot
an aarch64 QNX image on QEMU's `virt` machine. This is aarch64 on QEMU, not hardware.

**[host]** (needs the SDP's qemuvirt BSP package, installed from the Software Center, and `qemu-system-arm`)
```bash
sudo apt install -y qemu-system-arm
QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh build   # image in ~/qnx-images/qemu-aarch64le
QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh start   # 172.31.1.12, next to the x86_64 target
python3 scripts/run_campaign.py --arch aarch64le --target root@172.31.1.12 --only json-c,yyjson
```
Single libraries work the same way: `qnx-porter port ... --arch aarch64le --target root@172.31.1.12`.
Ports go to `ports-aarch64le/`, and `scripts/ports_csv.py` reads `ports/` and `ports-aarch64le/` together, so
`results/ports.csv` gets one row per library per architecture and the README headline one sentence per
architecture. The results committed in this repository today are x86_64 only.

To cross-build every library without a target: `python3 scripts/run_campaign.py --arch aarch64le --target none`.

## 11. Survive a network drop or a hung target
A full campaign runs for hours, and on our run the network did not stay up. Here is what the campaign does on
its own, and what you do afterwards.

**A clone fails.** Our final run lost DNS partway through. Each library that could not be cloned got a
`report.json` with `build_result: error`, and the campaign went on to the next one
(`results/runs/campaign-7.log`, command shortened):
```
=== [29/61] xxHash v0.8.2 ===
[1/5] fetch https://github.com/Cyan4973/xxHash.git @ v0.8.2
fatal: unable to access 'https://github.com/Cyan4973/xxHash.git/': Could not resolve host: github.com
    xxHash: agent error: Command '['git', ..., 'clone', ...]' returned non-zero exit status 128.
```
When the network is back, find those libraries and port just them:
```bash
grep -l '"build_result": "error"' ports/*/report.json
python3 scripts/run_campaign.py --only xxHash,BLAKE3,libtommath,wolfssl,libsrtp,libuv
```
That is what the `=== re-run of ...` sections at the end of `campaign-7.log` are.

**oss.qnx.com does not answer.** The campaign keeps the last saved answer and continues:
```
oss.qnx.com check failed (The read operation timed out); using the last saved list in results/oss_listed.json
```
`--skip-oss-check` skips the query entirely.

**A test hangs.** Each test runs under QNX's own `timeout -s KILL` on the target (300 s, or the test's own
smaller `TIMEOUT`), so a hung test cannot hold the ssh session. It is counted as failed, and `tests.log` says
so; from `ports/flac/logs/tests.log`:
```
    killed on the target after 300 s
```

**The target stops answering.** The campaign checks the target once, at the start
(`QNX target ... did not answer over ssh`). If QEMU hangs partway through, the libraries after that point fail
or the run stops. Restart the target and port what is left:
```bash
scripts/qemu_target.sh status                              # no uname -a: the target is gone
scripts/qemu_target.sh stop; scripts/qemu_target.sh start
python3 scripts/run_campaign.py --only <the libraries after the hang>
```
Under heavy host load the QEMU target can stop answering; `QNX_PORTER_JOBS=2` keeps the compiles from
starving it.

## 12. Hand a port to qnx-ports as a build-files recipe
QNX keeps hand-made recipes in [qnx-ports/build-files](https://github.com/qnx-ports/build-files).
`scripts/emit_recipes.py` writes one in that layout for every CMake library the campaign built that qnx-ports
does not have yet (names in `results/qnx_ports_names.txt`), from what the campaign actually built and tested.

**[host]**
```bash
python3 scripts/emit_recipes.py
ls recipes/build-files/ports/yyjson
```
You should see (our run on the committed reports):
```
34 recipes -> recipes/build-files/ports: json-c, yyjson, cmocka, libcbor, mbedtls, nng, libconfig, paho.mqtt.c, msgpack-c, nanopb, flatcc, cmark, miniz, libdeflate, xxHash, BLAKE3, libtommath, wolfssl, libsrtp, libcoap, open62541, Micro-CDR, fmt, spdlog, yaml-cpp, tomlplusplus, opus, libogg, flac, libsamplerate, cglm, libccd, kissfft, capstone
not emitted (only CMake ports that built are): libsodium (autotools, built), libmodbus (autotools, built), tinycbor (make, built), inih (meson, built), libgpiod (autotools, failed), can-utils (cmake, failed)
```
Each recipe has `Makefile`, `common.mk`, `qnx.nto.toolchain.cmake`, `nto-x86_64-o/`, `nto-aarch64-le/` and a
`README.md`, plus `qnx.patch` and `qnx-compat/` when the port needed them (json-c's recipe carries its
`printf-null` patch). The flags and CMake options are the ones the campaign used. The recipe's README says how
to build it from a build-files checkout and lists every QNX change with its reason; from yyjson's:
```
| link-libm | `__isinf` is in QNX's libm, not in libc: QNX's <math.h> implements isinf/isfinite/isnan as calls to __isinf etc. in libm, where glibc needs no library. Link with -lm. |
```
The script never sends anything. The pull request text for qnx-ports is drafted, not sent:
[docs/upstream/qnx-ports-build-files-PR.md](upstream/qnx-ports-build-files-PR.md).

## 13. Watch upstream HEAD every week
A port at a release tag says nothing about next month's commits. `.github/workflows/weekly-head.yml` runs every
Monday (and on demand): it ports every library in `campaign.yaml` at its upstream default branch, build only and
rules only, and appends one row per library to `results/head/history.csv` on the `data/head-history` branch.
The QNX SDP needs a myQNX licence, so it cannot be installed on GitHub's hosted runners; the job runs on a
self-hosted runner with the SDP installed and the label `qnx-sdp`.

The same run by hand **[host]**:
```bash
python3 scripts/run_campaign.py --head --no-tests --no-model --skip-oss-check --out ports-head --only yyjson
python3 scripts/head_history.py ports-head
```
Leave out `--only` for all of `campaign.yaml`. On GitHub, a quick test of the runner on one library:
```bash
gh workflow run weekly-head.yml -f only=yyjson
```
Read the history:
```bash
git fetch origin data/head-history
git show origin/data/head-history:results/head/history.csv
```
Our first run:
```
run,library,branch,commit,arch,build_result,rounds,patches,minutes
2026-11-12,yyjson,master,ebb8d7e5aaa5,x86_64,built,1,0,1.1
```
A row that turns from `built` to `failed` names the upstream commit that broke the QNX build. Its report is in
the run's `head-reports` artifact.

When you are done: `scripts/qemu_target.sh stop` (and `QNX_TARGET_ARCH=aarch64le scripts/qemu_target.sh stop`).

## If something goes wrong
| Symptom | Cause | Fix |
|---|---|---|
| `QNX SDP 8.0 not found` | the environment script was not sourced | `source ~/qnx800/qnxsdp-env.sh` |
| `qcc not found at ...` | the SDP is not installed at `QNX_HOST` | redo step 2.4; then `qnx-porter doctor` |
| `doctor`: `BAD SDP complete` | an interrupted install left empty files | repair or reinstall SDP 8.0 in the Software Center |
| `doctor`: `BAD x86_64 gcc` | autotools/meson drivers named differently in your SDP | look in `$QNX_HOST/usr/bin` for `*-nto-qnx*-gcc` and report it as an issue |
| `start` prints `QNX target did not answer ssh` | no bridge, or QEMU failed to boot | `sudo scripts/qemu_target.sh net "$USER"`, then read `~/qnx-images/qemu/output/qemu.out` |
| `ssh: connect ... refused` / timeout | QEMU not running or still booting | `scripts/qemu_target.sh status`; if nothing, `scripts/qemu_target.sh start` |
| `Permission denied (publickey)` | image built without your key | delete `~/qnx-images/qemu` and run `scripts/qemu_target.sh build` again |
| `QNX target ... did not answer over ssh` from `run_campaign.py` | same as above | start the target, or build only: `python3 scripts/run_campaign.py --no-tests` |
| `Could not resolve host` in the campaign log | the network dropped | step 11: re-run those libraries with `--only` |
| Tests fail with "No space left" | `/data` too small | raise `--data-size` in `scripts/qemu_target.sh`, delete `~/qnx-images/qemu`, run `build` again |
| A library ends `failed` | something no rule handles | read "Still failing" in its REPORT.md; try step 6, or write a rule (step 7) |

## What you learned
- What QNX 8.0 changes for Linux-first code: POSIX headers, libsocket and libfsnotify, libc-provided
  pthread/rt/dl, `_QNX_SOURCE`, and which Linux-only APIs have QNX equivalents.
- How to cross-compile CMake, Meson and autotools projects with `qcc` for x86_64 and aarch64, and run their
  tests on a QNX target.
- How to keep automated changes reviewable: one patch, one reason, one error.
- How to keep a port alive: re-run what a network drop cut short, hand recipes to qnx-ports, and watch
  upstream HEAD every week.
