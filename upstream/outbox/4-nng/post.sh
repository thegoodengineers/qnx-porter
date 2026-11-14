#!/bin/sh
# nng: drop the non-POSIX <sys/errno.h> include. Run from an empty folder.
# nng's CONTRIBUTING (docs/CONTRIBUTING.adoc) and PR template want commits formatted
# "fixes #<issue> <issue synopsis>", so this opens the issue first and puts its number in the commit and PR.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=nanomsg/nng
BRANCH=posix-udp-no-sys-errno
ISSUE_TITLE='posix_udp.c includes the non-POSIX <sys/errno.h>'

ISSUE_URL=$(gh issue create --repo "$REPO" --title "$ISSUE_TITLE" --body-file "$HERE/issue.md")
N=${ISSUE_URL##*/}
echo "issue #$N: $ISSUE_URL"

gh repo fork "$REPO" --clone=true  # --clone sets origin to the fork and upstream to the parent
cd nng
git fetch upstream main
git checkout -b "$BRANCH" upstream/main
GIT_ID="-c user.name=Chirag -c user.email=118997601+Chirag6722@users.noreply.github.com"
git $GIT_ID am "$HERE"/0001-posix_udp-do-not-include-sys-errno.h.patch
MSG=$(git log -1 --format=%B)
git $GIT_ID commit --amend -m "fixes #$N $ISSUE_TITLE" -m "$MSG"
git push -u origin "$BRANCH"
sed "s/#ISSUE_NUMBER/#$N/" "$HERE/body.md" > "$HERE/body.final.md"
gh pr create --repo "$REPO" --base main --head "Chirag6722:$BRANCH" \
    --title "$(cat "$HERE/title.txt")" --body-file "$HERE/body.final.md"
