# Codelab: port an open-source C library to QNX 8.0 with qnx-porter

**You will:** set up QNX SDP 8.0 and a QEMU target, port a real library, read every change the agent
made, run the library's own tests on QNX, and teach the agent a new porting rule.
**Time:** about 75 minutes (45 of them installing). **You need:** Ubuntu 22.04/24.04 or Windows 11 with
WSL2, 20 GB free disk, a free QNX Everywhere account.

---

## 1. Run the loop without QNX (5 min)
Before installing anything from QNX, see what the agent does on a small library that was written on Linux
and does not build cleanly elsewhere.

```bash
git clone https://github.com/thegoodengineers/qnx-porter && cd qnx-porter
python3 -m pip install -e ".[test]"
qnx-porter selftest
```
You will see two rounds. Round 1 fails twice: `strcasecmp` is used without `<strings.h>`, and an unused
variable trips `-Werror`. The agent fixes both, rebuilds, and the build passes. Open
`ports-selftest/brokenlib/REPORT.md` and the two files in `ports-selftest/brokenlib/patches/`.

**Why `<strings.h>` matters on QNX:** glibc's `<string.h>` happens to declare `strcasecmp`; POSIX puts it
in `<strings.h>`, and QNX's libc follows POSIX. Code written on Linux often only "works" by accident.

## 2. Install QNX SDP 8.0 and start a QNX target (45 min)
Follow [SETUP.md](../SETUP.md) steps 1-4. At the end you should have:
```bash
source ~/qnx800/qnxsdp-env.sh
qcc -V                               # gcc_ntox86_64 is in the list
ssh root@172.31.1.11 uname -a        # QNX ... 8.0.0 ... x86_64
qnx-porter doctor                    # every line says ok
```
`mkqnximage` built that QEMU image from the SDP's own packages; `/data` is its writable partition.

## 3. Port a real library (10 min)
json-c is a widely used JSON library, not yet on oss.qnx.com (see `results/candidates_check.csv`).
```bash
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 \
  --target root@172.31.1.11 --no-model
```
What happens, in the order the log prints it:
1. **fetch** - a shallow clone at the tag, tagged `qnx-porter-base` so every later change is a diff.
2. **build system** - `CMakeLists.txt` found, so CMake.
3. **toolchain** - `ports/json-c/qnx-toolchain.cmake` is written. Open it: `CMAKE_SYSTEM_NAME QNX`, `qcc`
   with `CMAKE_C_COMPILER_TARGET gcc_ntox86_64`, and `$QNX_TARGET` as the sysroot.
4. **rounds** - build, parse errors, fix, rebuild. Each fix line names its rule.
5. **tests** - ctest runs json-c's own tests. Each test binary runs on the QNX target over ssh through
   `work/qnx-run`, a wrapper the agent writes and passes as `CMAKE_CROSSCOMPILING_EMULATOR`.

## 4. Review what it changed (10 min)
```bash
cat ports/json-c/REPORT.md
ls ports/json-c/patches/
cat ports/json-c/qnx.patch           # every kept source change, against the upstream tag
less ports/json-c/logs/round-01.log  # the errors that started it
less ports/json-c/logs/tests.log     # the test run on QNX
```
Every patch starts with a header: the rule, whether it came from a rule or the model, the reason, and
the exact compiler error. If you disagree with a change, you have everything you need to say why.

Exercise: apply the port to a fresh checkout yourself.
```bash
git clone -q --depth 1 --branch json-c-0.18-20240915 https://github.com/json-c/json-c.git /tmp/jc
git -C /tmp/jc apply "$PWD/ports/json-c/qnx.patch"
cmake -S /tmp/jc -B /tmp/jc-build -DCMAKE_TOOLCHAIN_FILE="$PWD/ports/json-c/qnx-toolchain.cmake"
cmake --build /tmp/jc-build -j
```

## 5. Let the model handle the long tail (optional, 5 min)
Rules cover the errors that are always fixed the same way. For the rest:
```bash
export QNX_PORTER_API_KEY="..."   # your key, in this shell only
export QNX_PORTER_MODEL="..."     # a model ID from your provider
qnx-porter port https://github.com/nanomsg/nng.git --tag v1.9.0 --arg -DNNG_TESTS=ON --target root@172.31.1.11
```
The model gets the error, 65 lines of the file around it, and a hint about what QNX has instead (for
example "QNX has no epoll: use poll()"). Its diff must pass `git apply --check`. After the rebuild, if the
same error is still there, the agent reverts the patch and the report shows it as `reverted`.

## 6. Teach the agent a rule (10 min)
The simplest rule to extend is the symbol-to-header table. Say a library calls `getopt()` without
`#include <unistd.h>` and the build fails with `implicit declaration of function 'getopt'`.

1. Write the failing test first, in `tests/test_fixes_and_patches.py`:
   ```python
   def test_getopt_comes_from_unistd(tmp_path):
       (tmp_path / "a.c").write_text('#include <stdio.h>\nint main(int c, char **v) { return getopt(c, v, "x"); }\n')
       [f] = fixes.plan([implicit(sym="getopt")], tmp_path, Flags(), set())
       assert "#include <unistd.h>" in f.edits["a.c"]
   ```
2. Add `"getopt"` to the `unistd.h` entry of `SYMBOL_HEADERS` in `qnx_porter/fixes.py`.
3. `python3 -m pytest -q`. Re-run a port that hit the error and read the new patch and its reason.

A new kind of rule goes in `_rule()` in the same file. Rules act only on what the compiler or linker
said; if a fix needs judgement, it belongs to the model or a person.

## 7. Port a batch and publish the numbers
```bash
qnx-porter batch candidates.json --target root@172.31.1.11
python3 scripts/ports_csv.py         # writes results/ports.csv and the README table
```
`ports_csv.py` reads only the agent's own `report.json` files, so the table cannot drift from what ran.

## What you learned
- What QNX 8.0 changes for Linux-first code: POSIX headers, libsocket, libc-provided pthread/rt/dl,
  `_QNX_SOURCE`, and which Linux-only APIs have QNX equivalents.
- How to cross-compile CMake, Meson and autotools projects with `qcc`, and run their tests on a target.
- How to keep automated changes reviewable: one patch, one reason, one error.
