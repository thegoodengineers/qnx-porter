# Devpost submission text

Category: **Developer Tooling & Host Tools**. Fill every `[from results/ports.csv]` from the script's
output on the day; never type a number that `scripts/ports_csv.py` did not print.

## Name
qnx-porter

## Tagline (under 200 characters)
Point it at an open-source C/C++ library: it builds it for QNX 8.0, fixes what breaks with reviewable
patches, and proves the port by running the library's own tests on QNX.

## Inspiration
QNX 8.0 is free for non-commercial use, and QNX runs a ports site and a whole prize category for ports,
because every library that has never been built for QNX is a reason a team picks another OS. When we
looked at what porting actually involves, most of it is the same work again and again: a header glibc
includes implicitly and QNX does not, sockets living in `libsocket`, `-lpthread` and `-lrt` pointing at
libraries whose functions are already in QNX's libc, `-Werror` tripping on new warnings. That part should
be a tool. The rest, real Linux-only code like epoll, deserves a person's or a model's attention, with
every change visible.

## What it does
`qnx-porter port <git URL> --tag <release> --target root@<qnx-ip>`:
1. Clones the library at the tag and detects CMake, Meson, autotools or Make.
2. Generates a QNX SDP 8.0 toolchain: a CMake toolchain file using `qcc` with
   `CMAKE_C_COMPILER_TARGET gcc_ntox86_64` and `$QNX_TARGET` as sysroot, a Meson cross file, or
   `--host=x86_64-pc-nto-qnx8.0.0` for autotools.
3. Builds, and parses every GCC, linker, CMake and configure error into structured diagnostics.
4. Applies deterministic QNX rules first (missing headers, `_QNX_SOURCE`, `-lsocket`, libc-provided
   libraries, `-Werror` warnings). Each change is a numbered patch file with the rule, the reason and the
   exact error it answers.
5. Sends only what no rule handles to an optional model, with QNX-specific hints. The model must answer
   with a diff; it must pass `git apply --check`, and if the rebuild still shows the error, the agent
   reverts it and marks it reverted in the report.
6. When the build is clean, runs the library's **own** test suite (ctest, meson test or make check) on a
   QNX 8.0 target: each test binary is copied and executed over ssh on the QEMU image from `mkqnximage`.
7. Writes `ports/<library>/`: REPORT.md, report.json, every patch, one combined `qnx.patch`, the toolchain
   file and every build log.

Results on [N, from results/ports.csv] libraries that were not on oss.qnx.com: [built] built for QNX 8.0,
[passed]/[total] of their own tests passed on QNX 8.0 in QEMU, [rule] patches by rules and [model] by the
model, [minutes] minutes in total. Table: `results/ports.csv`.

## Evidence of QNX use
| Claim | File, function, output |
|---|---|
| Builds with the QNX SDP 8.0 toolchain | `qnx_porter/qnx.py`: `cmake_toolchain()`, `meson_cross()`, `gnu_env()`, `ARCHES` (gcc_ntox86_64, gcc_ntoaarch64le, x86_64-pc-nto-qnx8.0.0) |
| Finds and checks the SDP | `qnx_porter/qnx.py`: `sdp_env()` sources `qnxsdp-env.sh`; `doctor()` runs `qcc -V` |
| QNX-specific porting knowledge | `qnx_porter/fixes.py`: `SOCKET_SYMBOLS` (libsocket), `IN_LIBC` (pthread/rt/dl), `_QNX_SOURCE` rule, `LINUX_ONLY` hints (ionotify, timer_create, pthread_setname_np) |
| Runs tests on QNX 8.0 | `qnx_porter/target.py`: `write_wrapper()` is the ctest/meson/automake test wrapper, `Target.sync()`; output `ports/<library>/logs/tests.log` |
| Target identity | every `ports/<library>/report.json` has `target` = `uname -a` from the QNX target |
| Per-library QNX build files | `ports/<library>/qnx-toolchain.cmake` (or `qnx-cross.ini`, `qnx-env.sh`) and `qnx.patch` |

## How we built it
Python 3 standard library only (no runtime dependencies), so it installs anywhere the SDP does. The
agent loop is in `qnx_porter/agent.py`; rules in `fixes.py`; error parsing in `errors.py`; the model
client in `llm.py` (any OpenAI-compatible endpoint, configured only through `QNX_PORTER_API_KEY`,
`QNX_PORTER_MODEL` and `QNX_PORTER_BASE_URL`). 35 pytest tests run in CI without QNX, including full
runs of the porting loop on a deliberately broken library with the host compiler. Candidates were
checked against all of oss.qnx.com and the qnx-ports organisation by `scripts/check_candidates.py`.

## Challenges we ran into
[Fill from docs/LEARNINGS.md after the QNX runs: what broke first, what the agent could not fix.]

## Accomplishments that we're proud of
- Every change is a patch file with a reason; nothing is hidden, and a model patch that does not help is
  reverted and shown as reverted.
- A port only counts when the library's own tests ran on QNX 8.0.
- [Ports offered upstream / to qnx-ports: link PRs here.]

## What we learned
[One line each from Chirag, Bhumika, Ayush, Abhijeet.]

## What's next
- aarch64 runs on a Raspberry Pi 5 with QNX 8.0.
- Publishing finished ports as pull requests to qnx-ports with the agent's report attached.
- More rules from the long tail the model handled most often.

## Built with
python, qnx, qnx-sdp-8.0, qcc, qemu, cmake, meson, autotools, git

## Links
- Repo: https://github.com/thegoodengineers/qnx-porter
- Video: [YouTube link]
- Codelab: https://github.com/thegoodengineers/qnx-porter/blob/main/docs/CODELAB.md
