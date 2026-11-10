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

## Blocked on QNX SDP 8.0 (needs the install in SETUP.md)
1. `qnx-porter doctor` all ok on a real SDP.
2. First real port (json-c), by hand-checking every patch the agent wrote.
3. `python3 scripts/run_campaign.py` (all of campaign.yaml), which fills `results/ports.csv` and the README table.
4. Model runs on the long tail (needs `QNX_PORTER_API_KEY` / `QNX_PORTER_MODEL`).
5. Demo video shots of QNX in QEMU, and the numbers in docs/DEVPOST.md and docs/VIDEO_SCRIPT.md.
