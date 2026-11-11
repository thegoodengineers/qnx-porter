# Learnings and status

Dated entries. Labels: [Verified] ran it ourselves, [To verify] from documentation, not yet run.

## 10 Nov 2026
- [Verified] QNX SDP 8.0 was not installed on the build machine (no `~/qnx800`, no `qcc`). Everything that
  needs no SDP is built and tested: 35 pytest tests on Linux (WSL Ubuntu 22.04) and in CI.
- [Verified] oss.qnx.com lists 2,498 packages (13,931 builds) through its public API; the qnx-ports GitHub
  organisation has 239 repos. Many obvious picks are already there: lz4, zstd, inih, pcre2, cJSON, expat,
  libuv, sqlite, zlib, utf8proc, miniz, libdeflate. Our 12 candidates are on neither
  (`results/candidates_check.csv`, from `scripts/check_candidates.py`).
- [Verified] QNX's `mkqnximage` runs QEMU targets only on Ubuntu hosts (QNX 8.0 docs, mkqnximage page), so
  the agent is Linux-host only; Windows users run it in WSL2.
- [To verify] SDP 8.0 ships `x86_64-pc-nto-qnx8.0.0-gcc` style drivers for autotools/meson. `qnx-porter doctor`
  checks it. If missing, switch `gnu_env()` / `meson_cross()` in `qnx_porter/qnx.py` to `qcc -Vgcc_ntox86_64`.
- [To verify] The QEMU image's sshd accepts root with the `--ssh-ident` key, and the image has `tar`.

- [Verified] From QNX's 8.0 docs (C Library Reference, io-sock Networking APIs, Migrating to QNX OS 8.0):
  libsocket still exists; dlopen, pthread_setname_np, pipe2, clock_gettime are in libc; mmap documents
  `MAP_ANON`; `gettid()` is in `<process.h>`; the socket API is ported from FreeBSD 14.3; SDP 8.0 uses GCC 12.
  Correction: QNX 8.0 *has* inotify (moved to libfsnotify); our first hint said it had none.
  These became 22 rows in docs/LINUX_ISMS.md, each with a test.
- [Verified] On the host, GCC's wording for `#error`, the one-argument `pthread_setname_np`, and ld's
  "multiple definition" matches what the parser expects (checked with gcc 11 in WSL and gcc 13 in CI).

## 11 Nov 2026: first real SDP install
- [Verified] SDP 8.0 ships gcc/g++ only with a version suffix (`x86_64-pc-nto-qnx8.0.0-gcc-12.2.0`); binutils
  and `qcc`/`q++` are unversioned. `qcc -V` lists 12.2.0 `gcc_ntox86_64` (default) and `gcc_ntoaarch64le`.
  `gnu_tool()` in `qnx_porter/qnx.py` now picks the versioned driver.
- [Verified] Our first install was incomplete: 4,019 of 8,726 files under `~/qnx800` were 0 bytes (including
  `cc1` and the target libc), the Software Center log stopped mid-unarchive after a connection reset, and qcc
  failed with `cc1: Exec format error`. `qnx-porter doctor` now checks for this ("SDP complete") and
  compiles a socket program with qcc before saying ok.
- [Verified] Ubuntu 22.04's pip 22 cannot install a pyproject-only package in editable mode; upgrade pip
  with `--user` first. Docs updated.

## Blocked on QNX SDP 8.0 (needs the install in SETUP.md)
1. `qnx-porter doctor` all ok on a real SDP.
2. First real port (json-c), by hand-checking every patch the agent wrote.
3. `python3 scripts/run_campaign.py` (all of campaign.yaml), which fills `results/ports.csv` and the README table.
4. Model runs on the long tail (needs `QNX_PORTER_API_KEY` / `QNX_PORTER_MODEL`).
5. Demo video shots of QNX in QEMU, and the numbers in docs/DEVPOST.md and docs/VIDEO_SCRIPT.md.
