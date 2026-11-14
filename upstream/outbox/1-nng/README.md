# 1 - nanomsg/nng: stop the poll thread on a flag, not only on POLLHUP

- **Upstream:** https://github.com/nanomsg/nng (default branch `main`)
- **Checked:** `main` at `caf6f9f0b220a8e182875707db3fd05142d913ea` (commit date 2026-11-03T16:48:14-08:00), shallow
  clone on 14 Nov 2026. `nni_poll_thr()` still stops only on `POLLHUP` from the waker pipe, and `pq->closed` is
  still only ever set to `false`.
- **Apply check:** `git apply --check` passes on that commit; the patch is the unchanged draft from
  `docs/upstream/nng-pollhup/` (also applies to `v2.1.0`).
- **Files:** the patch, `title.txt`, `body.md` (PR, follows the PR template: `fixes #<n> <synopsis>` then
  comments; `post.sh` fills in the number), `issue.md` (issue, follows `.github/ISSUE_TEMPLATE/bug_report.md`),
  `post.sh`.

## Verification
- QNX numbers (3/64 before, 60/64 after, v2.1.0) from `docs/upstream/nng-pollhup/PR.md`,
  `ports/nng/logs/tests.log` and `docs/upstream/nng-pollhup/tests-qnx-x86_64-patched.log`. The reproducer
  output in `issue.md` is from `docs/qnx-reports/pipe-pollhup.md`.
- Note on the earlier Linux run in `PR.md` (74/74 with the patch on v2.1.0): Linux uses the epoll poller by
  default, so that run did not compile `posix_pollq_poll.c`. To exercise the change on Linux, a scratch clone of
  `main` + this patch was built in WSL Ubuntu 22.04 (gcc 11.4.0) with `-DNNG_TESTS=ON -DNNG_POLLQ_POLLER=poll`
  (`posix_pollq_poll.c` compiled, cache shows `NNG_POLLQ_POLLER=poll`); `ctest --timeout 300 -j2` reported 100%
  passed. Unpatched `main` with the same poll poller also passes (Linux reports `POLLHUP`, so it never hung
  there); the same patched clone with the default poller also reported 100% passed. The PR body states only "all tests
  pass" for these runs, since they are not in the repo's committed logs.

## Contribution rules found
- [docs/CONTRIBUTING.adoc](https://github.com/nanomsg/nng/blob/main/docs/CONTRIBUTING.adoc): submitting grants
  an MIT licence (no CLA, no DCO); file a GitHub issue with platform, CMake configuration, expected/observed
  behaviour and a minimal C test case; follow `.clang-format`, braces on all conditionals, parenthesised return
  values; one issue per PR, one squashed commit, merged and tested against latest `main`; commit message format
  `fixes #<issue> <issue-synopsis>` followed by comments; respond to review.
- [.github/pull_request_template.md](https://github.com/nanomsg/nng/blob/main/.github/pull_request_template.md):
  `fixes #<issue number> <issue synopsis>` then comments, same format in the commit.
- CONTRIBUTING also says: "Code submitted should contain updates to any copyright files to add your copyright"
  (`// Copyright <year> <owner> <email or url>` below the existing lines). **Not added** to the patch: it is a
  legal statement only the author can make. If wanted, add
  `// Copyright 2026 Chirag <https://github.com/Chirag6722>` below the existing copyright lines of
  `src/platform/posix/posix_pollq_poll.c` and amend before pushing.

## What the person must do first
- Decide on the copyright line (above).
- `post.sh` opens the issue first, then uses its number in the commit message and PR body.
- Be ready to answer review; CONTRIBUTING says abandoned PRs get closed.
