# 2 - google/googletest: O_DIRECTORY for the QNX death-test working directory

- **Upstream:** https://github.com/google/googletest (default branch `main`)
- **Checked:** `main` at `e882c36410197464e3429546e6a7d5e217bde51e` (commit date 2026-11-13T13:40:10-08:00),
  shallow clone on 14 Nov 2026. `open(".", O_RDONLY)` is still at `googletest/src/gtest-death-test.cc:1263`.
- **Apply check:** `git apply --check` passes on that commit. The patch is the unchanged draft from
  `docs/upstream/googletest/` (made against `v1.15.2`); `git am` onto `main` also succeeds.
- **Files:** `0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch`, `title.txt`, `body.md` (PR),
  `issue.md` (issue, filled in along the bug-report form's fields), `post.sh`.

## Contribution rules found
- [CONTRIBUTING.md](https://github.com/google/googletest/blob/main/CONTRIBUTING.md):
  - **Google CLA required** before a PR can be accepted
    ([individual CLA](https://developers.google.com/open-source/cla/individual), signed at https://cla.developers.google.com/).
  - **Issue first:** "Submit an issue describing your proposed change to the issue tracker", wait for it to be
    accepted, then sign the CLA, then open the PR. One logical change per PR. Google C++ style / `.clang-format`.
- Issue form: [.github/ISSUE_TEMPLATE/00-bug_report.yml](https://github.com/google/googletest/blob/main/.github/ISSUE_TEMPLATE/00-bug_report.yml)
  (fields: describe the issue, steps, version, OS, compiler, build system, additional context). `issue.md` uses
  those headings. The form's title prefix is `[Bug]: `. No PR template, no DCO.

## What the person must do first
1. Sign the Google individual CLA with the GitHub account that will open the PR.
2. Run `sh post.sh issue`, wait for a maintainer to agree.
3. Then `sh post.sh pr <issue-number>`.

## Evidence
All numbers come from `docs/upstream/googletest/PR.md` and `docs/qnx-reports/fchdir-o-rdonly.md`
(QNX 8.0 x86_64 target, v1.15.2). Not verified: QNX 7.x, and a rebuild on `main`. The line is QNX-only, so a
Linux build does not compile it.
