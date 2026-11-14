#!/bin/sh
# googletest: O_DIRECTORY for the QNX death-test working directory.
# googletest's CONTRIBUTING.md asks for an issue first and a signed Google CLA before a PR.
#   sh post.sh issue            # step 1: open the issue, then wait for a maintainer's answer
#   sh post.sh pr <issue-no>    # step 2: after the change is accepted and the CLA is signed
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=google/googletest
BRANCH=qnx-death-test-o-directory

case "$1" in
issue)
    gh issue create --repo "$REPO" \
        --title "[Bug]: QNX 8.0: threadsafe death tests abort, fchdir() needs a directory opened with O_DIRECTORY" \
        --body-file "$HERE/issue.md"
    ;;
pr)
    N="$2"
    [ -n "$N" ] || { echo "usage: sh post.sh pr <issue-number>"; exit 1; }
    gh repo fork "$REPO" --clone=true --remote=true
    cd googletest
    git fetch upstream main
    git checkout -b "$BRANCH" upstream/main
    git -c user.name=Chirag -c user.email=118997601+Chirag6722@users.noreply.github.com am "$HERE"/0001-*.patch
    git push -u origin "$BRANCH"
    sed "s/#ISSUE_NUMBER/#$N/" "$HERE/body.md" > "$HERE/body.final.md"
    gh pr create --repo "$REPO" --base main --head "Chirag6722:$BRANCH" \
        --title "$(cat "$HERE/title.txt")" --body-file "$HERE/body.final.md"
    ;;
*)
    echo "usage: sh post.sh issue | sh post.sh pr <issue-number>"; exit 1
    ;;
esac
