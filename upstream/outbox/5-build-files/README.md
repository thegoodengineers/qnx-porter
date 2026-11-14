# 5 - qnx-ports/build-files: add yyjson

- **Upstream:** https://github.com/qnx-ports/build-files (default branch `main`)
- **Checked:** `main` at `79d94bd6f1d66e524b17c1f26379ac0ef9bd24c5` (commit date 2026-11-13T18:22:28+01:00), shallow
  clone on 14 Nov 2026. No `ports/yyjson`, no `yyjson` workflow, no open or closed issue/PR mentioning yyjson.
- **Apply check:** `git apply --check` passes on that commit.
- **Patch:** one commit made with `git format-patch` in a scratch clone of that commit. It adds:
  - `ports/yyjson/` = `recipes/build-files/ports/yyjson/` from this repo, byte for byte, except one line of its
    README: the report path now reads `ports-2024/yyjson/REPORT.md` (the 0.10.0 report the recipe came from;
    `ports/yyjson/REPORT.md` is now the 0.13.0 run).
  - `.github/workflows/yyjson.yml`, written for this PR after `cJSON.yml` / `libwebsockets.yml` (every recent
    port PR in the repo adds one, e.g. #327, #320, #319).
  - one row in the port table of `README.md`.
- **Why this library:** `recipes/BUILD_CHECK.md` shows it built and installed with QNX make for `nto-x86_64-o`
  and notes it was built for `nto-aarch64-le` earlier; `ports-2024/yyjson/logs/tests.log` shows 12/12 tests on
  the QNX 8.0 x86_64 target; the port needs no source patch.

## Contribution rules found
No CONTRIBUTING file, PR template, CLA or DCO in the repository or in the `qnx-ports/.github` repository
(only a profile README). Conventions taken from merged PRs: one port per PR, titled `<port>: add build files`
or similar, adding `ports/<port>/`, `.github/workflows/<port>.yml` and a README table row. The workflow only
runs on a PR whose title contains the port name.

## What the person must do first
Nothing required. Optionally run the workflow's build command on a Linux host with the SDP once more.
