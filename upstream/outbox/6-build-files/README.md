# 6 - qnx-ports/build-files: add mbedtls

- **Upstream:** https://github.com/qnx-ports/build-files (default branch `main`)
- **Checked:** `main` at `79d94bd6f1d66e524b17c1f26379ac0ef9bd24c5` (commit date 2026-11-13T18:22:28+01:00), shallow
  clone on 14 Nov 2026. No `ports/mbedtls`, no `mbedtls` workflow, no open or closed issue/PR mentioning mbedtls.
- **Apply check:** `git apply --check` passes on that commit.
- **Patch:** one commit made with `git format-patch` in a scratch clone of that commit. It adds:
  - `ports/mbedtls/` = `recipes/build-files/ports/mbedtls/` from this repo, byte for byte, except one line of its
    README: the report path now reads `ports-2024/mbedtls/REPORT.md` (the v3.6.2 report the recipe came from;
    `ports/mbedtls/REPORT.md` is now the v4.2.0 run).
  - `.github/workflows/mbedtls.yml`, written for this PR after `cJSON.yml` / `boost.yml` (submodules), as every
    recent port PR adds one.
  - one row in the port table of `README.md`.
- **Why this library:** `recipes/BUILD_CHECK.md` shows it built and installed with QNX make for `nto-x86_64-o`;
  `ports-2024/mbedtls/logs/tests.log` shows 130/130 on the QNX 8.0 x86_64 target; no source patch.
- **Weaker than item 5:** not built for `nto-aarch64-le` through make, and v3.6.2 is the 3.6 LTS line, not
  the newest release (v4.2.0, which the newer campaign ported with a different patch set). Send it only if the
  team is happy to offer the 3.6 LTS recipe.

## Contribution rules found
Same as item 5: no CONTRIBUTING file, PR template, CLA or DCO in the repository or in `qnx-ports/.github`.
One port per PR; the workflow only runs on a PR whose title contains the port name.

## What the person must do first
Nothing required.
