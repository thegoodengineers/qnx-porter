#!/bin/sh
# libsrtp: replace qsort() with a random comparator in test/ut_sim.c. Run from an empty folder.
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=cisco/libsrtp
BRANCH=ut-sim-shuffle

gh repo fork "$REPO" --clone=true --remote=true
cd libsrtp
git fetch upstream main
git checkout -b "$BRANCH" upstream/main
git -c user.name=Chirag -c user.email=118997601+Chirag6722@users.noreply.github.com am "$HERE"/0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch
# Optional, if clang-format-17 is installed (CI's "Code Formatting Check" runs exactly this):
#   ./format.sh -d
git push -u origin "$BRANCH"
gh pr create --repo "$REPO" --base main --head "Chirag6722:$BRANCH" \
    --title "$(cat "$HERE/title.txt")" --body-file "$HERE/body.md"
