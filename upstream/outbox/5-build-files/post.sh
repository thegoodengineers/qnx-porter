#!/bin/sh
# qnx-ports/build-files: add yyjson. Run from an empty folder.
# The PR title must contain "yyjson": the new workflow runs on a pull request only if it does.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=qnx-ports/build-files
BRANCH=add-yyjson

gh repo fork "$REPO" --clone=true --remote=true
cd build-files
git fetch upstream main
git checkout -b "$BRANCH" upstream/main
git -c user.name=Chirag -c user.email=118997601+Chirag6722@users.noreply.github.com am "$HERE"/0001-yyjson-add-build-files.patch
git push -u origin "$BRANCH"
gh pr create --repo "$REPO" --base main --head "Chirag6722:$BRANCH" \
    --title "$(cat "$HERE/title.txt")" --body-file "$HERE/body.md"
