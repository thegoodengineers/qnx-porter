#!/bin/sh
# nng: stop the poll thread on a flag, not only on POLLHUP. Run from an empty folder.
# nng's CONTRIBUTING (docs/CONTRIBUTING.adoc) and PR template want commits formatted
# "fixes #<issue> <issue synopsis>", so this opens the issue first and puts its number in the commit and PR.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=nanomsg/nng
BRANCH=posix-pollq-closed-flag
ISSUE_TITLE='nng_fini() hangs where poll() reports no POLLHUP for a closed pipe (QNX 8.0)'

ISSUE_URL=$(gh issue create --repo "$REPO" --title "$ISSUE_TITLE" --body-file "$HERE/issue.md")
N=${ISSUE_URL##*/}
echo "issue #$N: $ISSUE_URL"

gh repo fork "$REPO" --clone=true --remote=true
cd nng
git fetch upstream main
git checkout -b "$BRANCH" upstream/main
GIT_ID="-c user.name=Chirag -c user.email=118997601+Chirag6722@users.noreply.github.com"
git $GIT_ID am "$HERE"/0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch
MSG=$(git log -1 --format=%B)
git $GIT_ID commit --amend -m "fixes #$N $ISSUE_TITLE" -m "$MSG"
git push -u origin "$BRANCH"
sed "s/#ISSUE_NUMBER/#$N/" "$HERE/body.md" > "$HERE/body.final.md"
gh pr create --repo "$REPO" --base main --head "Chirag6722:$BRANCH" \
    --title "$(cat "$HERE/title.txt")" --body-file "$HERE/body.final.md"
