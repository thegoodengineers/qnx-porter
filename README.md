# qnx-porter

[![tests](https://github.com/thegoodengineers/qnx-porter/actions/workflows/test.yml/badge.svg)](https://github.com/thegoodengineers/qnx-porter/actions/workflows/test.yml)

**Point it at an open-source C/C++ library. It builds the library for QNX 8.0, fixes what breaks,
and proves the port by running the library's own tests on a QNX 8.0 target.**

Built for the [QNX Global Hackathon](https://qnx.devpost.com/) (Developer Tooling & Host Tools) by
Chirag, Bhumika, Ayush and Abhijeet (The Good Engineers).

## Why it matters
- QNX 8.0 is free for non-commercial use, but most open-source C/C++ libraries have never been built
  for it. QNX runs its own ports site ([oss.qnx.com](https://oss.qnx.com)) and a prize category for ports,
  because every missing library is a reason a team picks another OS.
- Porting is repetitive: the same missing headers, the same `-lsocket`, the same Linux-only calls,
  library after library. That part should be automatic, and every change should be reviewable.
- A port that compiles is not a port. qnx-porter counts a library as ported only when its own test
  suite runs on QNX 8.0.

## For judges, start here
- **Evidence of QNX use:** see [Evidence of QNX use](#evidence-of-qnx-use) below. Every claim points at a file.
- **Results:** [`results/ports.csv`](results/ports.csv), written by `scripts/ports_csv.py` from each
  port's own `ports/<library>/report.json`. No number in this README or the video comes from anywhere else.
- **Every patch the agent made:** `ports/<library>/patches/*.patch`, each with the rule, the reason and
  the exact compiler error it answers. `ports/<library>/REPORT.md` is the summary.
- **Candidates were new to QNX:** [`results/candidates_check.csv`](results/candidates_check.csv), written by
  `scripts/check_candidates.py`, which queries all of oss.qnx.com and the qnx-ports GitHub organisation.
- Setup: [SETUP.md](SETUP.md). Tutorial: [docs/CODELAB.md](docs/CODELAB.md).

## Results
Status: the agent and its tests are done and green in CI. The QNX runs need QNX SDP 8.0 installed
(see SETUP.md) and fill `results/ports.csv`; until then this table is intentionally empty.

<!-- results:start -->
| Library | Version | Build | Tests on QNX 8.0 | Patches (rule / model) | Minutes |
|---|---|---|---|---|---|
<!-- results:end -->

## How it works
```
git URL + tag
   │
   ▼
detect build system ──► CMake | Meson | autotools | Make
   │
   ▼
generate QNX toolchain ──► qnx-toolchain.cmake (qcc -Vgcc_ntox86_64, sysroot $QNX_TARGET)
   │                       qnx-cross.ini (meson) | --host=x86_64-pc-nto-qnx8.0.0 (autotools)
   ▼
build ──► parse GCC / ld / CMake / configure errors
   │            │
   │            ├─ deterministic rule? ──► patch + reason ──┐
   │            ├─ else model (optional) ──► diff, git apply --check, kept only if the rebuild clears it
   │            └─ else stop, report what is left and why   │
   ◄────────────────────────────── rebuild ◄────────────────┘
   │
   ▼
tests on the QNX 8.0 target ──► ctest / meson test / make check, each test binary run over ssh
   │
   ▼
ports/<library>/  REPORT.md · report.json · patches/ · qnx.patch · toolchain file · logs/
```

**Rules first.** Each rule acts only on what the compiler or linker said, plus facts about QNX's libc:

| Rule | Fires on | Change |
|---|---|---|
| `add-include` | implicit declaration / undeclared symbol | `#include` the header GCC's own note names, or the POSIX header from a table |
| `qnx-source` | the header is already included but the symbol is hidden | `-D_QNX_SOURCE` |
| `link-libsocket` | `undefined reference to socket/getaddrinfo/...` | `-lsocket` (QNX keeps sockets in libsocket) |
| `stub-lib` | `cannot find -lpthread/-lrt/-ldl` | an empty archive, because QNX has these in libc |
| `no-werror` | a warning promoted by `-Werror` | `-Wno-error=<that warning>` |
| `guard-linux-header` | `<sys/epoll.h>`, `<sys/sendfile.h>`, ... missing and unused by the file | `#ifndef __QNX__` around the include |
| `byteswap-builtins`, `prctl-set-name`, `pthread-setname*` | `<byteswap.h>`, `prctl(PR_SET_NAME)`, BSD/macOS thread-name calls | QNX's `__builtin_bswap*`, `pthread_setname_np(tid, name)` |
| `qnx-platform-guard` | `#error "Unsupported platform"` after an OS `#if` chain | QNX joins the BSD/Unix branch; kept only if the rebuild proves it |
| `map-anon`, `msg-nosignal`, `link-libfsnotify`, `fcommon` | `MAP_ANONYMOUS`, `MSG_NOSIGNAL`, inotify, GCC 12 `-fno-common` | see the corpus |

All 22 patterns, where each QNX fact comes from, and the test for each:
[docs/LINUX_ISMS.md](docs/LINUX_ISMS.md). Linux-only code that is actually *used* (epoll loops, sendfile)
is never rewritten by a rule; it goes to the model with a QNX-specific hint, or is reported as blocked.

**The model is optional and checked.** Set `QNX_PORTER_API_KEY` and `QNX_PORTER_MODEL` (any
OpenAI-compatible endpoint; `QNX_PORTER_BASE_URL` to change it). It must answer with a unified diff and
a one-sentence reason. The diff must pass `git apply --check`; after the rebuild, if the error it targeted
is still there or the error count grew, the agent reverts it and marks it `reverted` in the report.

## Evidence of QNX use
The path from "a git URL" to "tests passed on QNX 8.0", function by function:

| Step | What touches QNX | Exact place |
|---|---|---|
| 1. Find the SDP | sources `~/qnx800/qnxsdp-env.sh` to get `QNX_HOST` and `QNX_TARGET` | [`qnx.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/qnx.py) `sdp_env()` |
| 2. Check it | runs `qcc -V` and looks for `gcc_ntox86_64`; checks the `x86_64-pc-nto-qnx8.0.0-gcc` drivers | `qnx.py` `doctor()` (CLI: `qnx-porter doctor`) |
| 3. Write the QNX toolchain | CMake: `CMAKE_SYSTEM_NAME QNX`, `CMAKE_C_COMPILER $QNX_HOST/usr/bin/qcc`, `CMAKE_C_COMPILER_TARGET gcc_ntox86_64`, `CMAKE_SYSROOT $QNX_TARGET`. Meson: a cross file with `system = 'qnx'`. Autotools: `--host=x86_64-pc-nto-qnx8.0.0` | `qnx.py` `cmake_toolchain()`, `meson_cross()`, `gnu_env()`, `ARCHES`; saved per port as `ports/<library>/qnx-toolchain.cmake` |
| 4. Invoke qcc | the configure and build commands that drive qcc through that toolchain; output goes to `ports/<library>/logs/round-NN.log` | [`build.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/build.py) `Job.steps()` builds the commands, `run()` executes them; called from [`agent.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/agent.py) `port()` |
| 5. Fix what QNX rejects | 22 Linux-isms and the QNX 8.0 answer to each (libsocket, libfsnotify, libc-provided pthread/rt/dl, `MAP_ANON`, `pthread_setname_np`, `<process.h>`, `_QNX_SOURCE`, ...), sourced from QNX's 8.0 documentation | [`fixes.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/fixes.py) `_rule()`, [`linuxisms.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/linuxisms.py); sources per fact in [docs/LINUX_ISMS.md](docs/LINUX_ISMS.md) |
| 6. Start the QNX target | QEMU image made by QNX's `mkqnximage --type=qemu --arch=x86_64` from the SDP | [SETUP.md](SETUP.md) step 4 |
| 7. Run tests on QNX | copies the build to the target (`tar` over ssh), then ctest / meson test / make check run every test binary on QNX through a generated wrapper (`CMAKE_CROSSCOMPILING_EMULATOR`, meson `exe_wrapper`, automake `LOG_COMPILER`) | [`target.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/qnx_porter/target.py) `Target.sync()`, `write_wrapper()`, `remote_command()`, `main()`; output `ports/<library>/logs/tests.log` |
| 8. Record the target | `uname -a` from the QNX target in every report | `target.py` `Target.uname()`; `ports/<library>/report.json` field `target` |
| 9. One command for all of it | stops early if `qcc` or the target is missing | [`scripts/run_campaign.py`](https://github.com/thegoodengineers/qnx-porter/blob/main/scripts/run_campaign.py) `preflight()`, `check_target()` |

## Why a real-time OS needs this tooling
- **Nothing builds on the target.** A QNX system in a car, a robot or a medical device has no compiler; every
  library is cross-compiled with qcc against the SDP's sysroot. On Linux you can `./configure && make` on the
  machine itself. On QNX, each library needs a cross toolchain file and build flags first, and most upstream
  projects ship neither.
- **The host cannot run what it built.** QNX binaries do not run on the build machine, so "it compiled" proves
  little. qnx-porter runs the library's own tests on a QNX 8.0 target and counts only those results.
- **QNX's libc is POSIX, not glibc.** Linux code relies on things glibc adds (implicit headers, `epoll`,
  `prctl`, sockets in libc), so the same breakages come back in every library. That is why the fixes can be
  rules, collected once in [docs/LINUX_ISMS.md](docs/LINUX_ISMS.md).
- **The markets QNX serves review every change.** Automotive, medical and industrial teams cannot take a
  silently patched dependency. Every change here is a separate patch with the rule, the reason and the
  compiler error that caused it. Rules run the same way every time, and a model's patch is reverted unless the
  rebuild proves it. This is a review aid, not a safety certification.
- **The libraries chosen are the ones those systems need:** TLS (mbedtls), crypto (libsodium), MQTT
  (paho.mqtt.c), Modbus (libmodbus), messaging (nng), CBOR and JSON. None was on oss.qnx.com when checked
  ([results/candidates_check.csv](results/candidates_check.csv)).

## Quick start
```bash
python3 -m pip install --user --upgrade pip   # Ubuntu 22.04's pip 22 cannot do editable installs
python3 -m pip install --user -e ".[test]"
python3 -m pytest -q                                   # no QNX needed
source ~/qnx800/qnxsdp-env.sh && qnx-porter doctor
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11
python3 scripts/run_campaign.py                       # every library in campaign.yaml, then the CSV
```
Build and run requirements: **QNX SDP 8.0**, target **x86_64 QEMU** (from `mkqnximage`) or **aarch64le**
hardware with ssh, toolchain **qcc / GCC from SDP 8.0**, host **Ubuntu 22.04/24.04 or WSL2**. Details: [SETUP.md](SETUP.md).

## Known limits
- Linux host only (WSL2 on Windows), because QNX's QEMU tooling is Ubuntu-only.
- Tests that need a network peer or root-only devices are counted as they run; nothing is excluded by hand.
- A rule never rewrites Linux-only code (epoll, inotify, ...). That is the model's job, or a person's.
- The model is never trusted: a diff that does not clear its error is reverted and shown as reverted.

## Licence
Apache-2.0. Patches produced for a library are offered under that library's own licence.
