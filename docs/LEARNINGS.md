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
- [Verified, corrected later the same day] The broken first install had gcc/g++ only with a version suffix
  (`x86_64-pc-nto-qnx8.0.0-gcc-12.2.0`). The complete install (build 141) also has the plain
  `x86_64-pc-nto-qnx8.0.0-gcc`. `gnu_tool()` in `qnx_porter/qnx.py` takes the plain name when present and the
  versioned one otherwise. `qcc -V` lists 12.2.0 `gcc_ntox86_64` (default) and `gcc_ntoaarch64le`.
- [Verified] Our first install was incomplete: 4,019 of 8,726 files under `~/qnx800` were 0 bytes (including
  `cc1` and the target libc), the Software Center log stopped mid-unarchive after a connection reset, and qcc
  failed with `cc1: Exec format error`. `qnx-porter doctor` now checks for this ("SDP complete") and
  compiles a socket program with qcc before saying ok.
- [Verified] Ubuntu 22.04's pip 22 cannot install a pyproject-only package in editable mode; upgrade pip
  with `--user` first. Docs updated.

## 11 Nov 2026: QNX 8.0 running in QEMU, first port
- [Verified] After the SDP was repaired, `qnx-porter doctor` is all ok, including a qcc compile and link.
- [Verified] The mkqnximage QEMU image boots QNX 8.0 (`QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc
  x86_64`), but sshd stops at boot: `/usr/libexec/sshd-auth does not exist or is not executable`. The SDP has
  `sshd-auth`; mkqnximage does not put it in the image. A one-line `local/snippets/ifs_files.custom` entry
  with an absolute path (`/usr/libexec/...`; a relative path lands in `/proc/boot`) fixes it, then
  `mkqnximage --build` (a snippet change alone says "Nothing to do"). Now in `scripts/qemu_target.sh`.
- [Verified] QNX's `qemu/net.sh` starts dnsmasq with `--except-interface=lo0`; on WSL that collides with
  10.255.255.254 on `lo`, so DHCP never starts. We run dnsmasq with `--except-interface=lo --port=0`.
- [Verified] On WSL, QEMU started in the background dies when the `wsl` call exits; `setsid nohup` keeps it.
- [Verified] The image has `sh`, `ksh`, `tar`, `diff`, `cmp`, `sed`, `awk`; no `bash`, `perl` or `python3`.
- [Verified] **json-c's first run said 0/25 tests passed, and it was our fault, not QNX's.** json-c registers
  its tests as shell scripts (`test1.test`), and CMake applies `CMAKE_CROSSCOMPILING_EMULATOR` only to
  executable targets, so ctest ran the scripts on Linux, which then tried to exec QNX binaries ("not
  found"). Fix: `ctest_on_target()` in `qnx_porter/target.py` reads `ctest --show-only=json-v1` and runs every
  test command on QNX, applying ctest's WILL_FAIL / regex / skip rules itself. Generated scripts also
  hard-code host paths, so `Target.sync()` makes the copied trees appear at the same absolute path on QNX
  with a path-space link (`ln -sP /data/qnx-porter/home /home`).
- [Verified] json-c json-c-0.18-20240915 then built with qcc in one round with **no patches**, and **24 of 25**
  of its own tests passed on QNX 8.0. `test_json_patch` dies with "Memory fault" on the case
  `Out of bounds (lower)` (patch path `/bar/-1`), where Linux prints "Invalid argument". Not investigated
  further yet: the SDP has no x86_64 gdb installed and the image keeps no core dumps. Candidate upstream issue.

## Blocked on QNX SDP 8.0 (needs the install in SETUP.md)
1. `qnx-porter doctor` all ok on a real SDP.
2. First real port (json-c), by hand-checking every patch the agent wrote.
3. `python3 scripts/run_campaign.py` (all of campaign.yaml), which fills `results/ports.csv` and the README table.
4. Model runs on the long tail (needs `QNX_PORTER_API_KEY` / `QNX_PORTER_MODEL`).
5. Demo video shots of QNX in QEMU, and the numbers in docs/DEVPOST.md and docs/VIDEO_SCRIPT.md.
