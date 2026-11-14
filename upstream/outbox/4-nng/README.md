# 4 - nanomsg/nng: do not include <sys/errno.h>

- **Upstream:** https://github.com/nanomsg/nng (default branch `main`)
- **Checked:** `main` at `caf6f9f0b220a8e182875707db3fd05142d913ea` (commit date 2026-11-03T16:48:14-08:00), shallow
  clone on 14 Nov 2026. `#include <sys/errno.h>` is still at `src/platform/posix/posix_udp.c:14`; `main` now also
  has `#include <errno.h>` at line 20, inside `#ifdef NNG_PLATFORM_POSIX` (the rest of the file is inside it too).
- **Apply check:** the draft in `docs/upstream/nng/` (made against `v1.9.0`, replacing the include with
  `<errno.h>`) does **not** apply to `main`. **Refreshed**: on `main` the same change (stop including
  `<sys/errno.h>`, rely on `<errno.h>`) is deleting line 14, since `<errno.h>` is already there; replacing it
  would include `<errno.h>` twice. New commit made in a scratch clone and exported with `git format-patch`;
  subject changed to match (`posix_udp: do not include <sys/errno.h>`). `git apply --check` passes on `caf6f9f0b220`.
- **Checked on Linux in a scratch clone (WSL Ubuntu 22.04, gcc 11.4.0):** `main` + this patch configures and
  builds with `-DNNG_TESTS=ON` (posix_udp.c compiled). The tests were not run for this item; it is an include
  change. Not rebuilt for QNX on `main`.

## Contribution rules found
Same as item 1 ([docs/CONTRIBUTING.adoc](https://github.com/nanomsg/nng/blob/main/docs/CONTRIBUTING.adoc),
[PR template](https://github.com/nanomsg/nng/blob/main/.github/pull_request_template.md)): MIT grant by
submitting, follow `.clang-format`, one issue per PR with one squashed commit, rebased on latest `main`, commit
and PR formatted `fixes #<issue> <synopsis>`; the CONTRIBUTING also asks contributors to add their own
copyright line to changed files. No CLA, no DCO.

## What the person must do first
- `post.sh` opens the issue, then uses its number in the commit message and PR body.
- Decide on the copyright line (see item 1); for a one-line deletion it is probably not wanted.
- Item 1 and this item are separate PRs from separate branches; run each `post.sh` from its own empty folder.

## Evidence
"82 of 86" and the build error are from `docs/upstream/nng/PR.md` (`ports-2024/nng/logs/`), for v1.9.0.
