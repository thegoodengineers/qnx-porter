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

Linux-only headers (`sys/epoll.h`, `sys/inotify.h`, `linux/*`, ...) are never patched by a rule; they go
to the model with a QNX-specific hint (for example "use poll(), or ionotify()"), or are reported as blocked.

**The model is optional and checked.** Set `QNX_PORTER_API_KEY` and `QNX_PORTER_MODEL` (any
OpenAI-compatible endpoint; `QNX_PORTER_BASE_URL` to change it). It must answer with a unified diff and
a one-sentence reason. The diff must pass `git apply --check`; after the rebuild, if the error it targeted
is still there or the error count grew, the agent reverts it and marks it `reverted` in the report.

## Evidence of QNX use
| What | Where |
|---|---|
| CMake toolchain for QNX 8.0: `CMAKE_SYSTEM_NAME QNX`, `qcc` with `CMAKE_C_COMPILER_TARGET gcc_ntox86_64`, sysroot `$QNX_TARGET` | `qnx_porter/qnx.py`, `cmake_toolchain()`; written per port as `ports/<library>/qnx-toolchain.cmake` |
| Meson cross file and autotools `--host=x86_64-pc-nto-qnx8.0.0` | `qnx_porter/qnx.py`, `meson_cross()`, `gnu_env()` |
| SDP discovery (`qnxsdp-env.sh`, `QNX_HOST`, `QNX_TARGET`) and `qnx-porter doctor` | `qnx_porter/qnx.py`, `sdp_env()`, `doctor()` |
| QNX-specific porting knowledge: libsocket, pthread/rt/dl in libc, `_QNX_SOURCE`, Linux-only headers | `qnx_porter/fixes.py`, `SOCKET_SYMBOLS`, `IN_LIBC`, `LINUX_ONLY`, `_rule()` |
| Tests run on the QNX 8.0 target (QEMU image from `mkqnximage`) over ssh | `qnx_porter/target.py`, `write_wrapper()`, `Target.sync()`; output in `ports/<library>/logs/tests.log` |
| Target identity recorded in every report (`uname -a` on the target) | `report.json` field `target` |

## Quick start
```bash
python3 -m pip install -e ".[test]"
python3 -m pytest -q                                   # no QNX needed
source ~/qnx800/qnxsdp-env.sh && qnx-porter doctor
qnx-porter port https://github.com/json-c/json-c.git --tag json-c-0.18-20240915 --target root@172.31.1.11
qnx-porter batch candidates.json --target root@172.31.1.11
python3 scripts/ports_csv.py
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
