#!/bin/bash
# Python on QNX over a qnx-porter port: the SDP's own CPython 3.13 (target/qnx/x86_64/usr/bin/python3.13) runs on the
# x86_64 QNX 8.0 target with qnx-porter's zlib v1.4 port in place of the image's zlib, and CPython's own tests for
# the zlib and gzip modules run against it, then against the image's zlib for comparison. docs/PYTHON_ON_QNX.md.
#
# Before (once):
#   qnx-porter port https://github.com/madler/zlib.git --tag v1.4 --no-model --out ~/py-demo
#   git clone --depth 1 --branch v3.13.7 --filter=blob:none --sparse https://github.com/python/cpython ~/cpython-tests
#   git -C ~/cpython-tests sparse-checkout set Lib/test/__init__.py Lib/test/support Lib/test/libregrtest \
#       Lib/test/test_zlib.py Lib/test/test_gzip.py
# Run (SDP sourced, target started with scripts/qemu_target.sh start):
#   scripts/python_on_qnx.sh | tee results/runs/python-on-qnx.log
set -e
TARGET=${QNX_TARGET_SSH:-root@172.31.1.11}
ZLIB=${ZLIB_BUILD:-$HOME/py-demo/zlib/work/build}
TESTS=${CPYTHON_TESTS:-$HOME/cpython-tests}
[ -n "$QNX_TARGET" ] || { echo "source the SDP's qnxsdp-env.sh first" >&2; exit 1; }
T=$QNX_TARGET/x86_64
S="ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR $TARGET"
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/bin" "$STAGE/lib" "$STAGE/ourlib" "$STAGE/tests"
cp "$T/usr/bin/python3.13" "$STAGE/bin/"
cp "$T/usr/lib/libpython3.13.so.1.0" "$STAGE/lib/"
cp -a "$T/usr/lib/python3.13" "$STAGE/lib/"
find "$STAGE" -name '*.sym' -delete
# CPython's zlib module is linked against libz.so.2 (the SDP's zlib); zlib keeps one ABI, so our build stands in
# under that name.
cp "$ZLIB/libz.so.1.4" "$STAGE/ourlib/libz.so.2"
cp -a "$TESTS/Lib/test" "$STAGE/tests/"
echo "CPython: the SDP's python3.13; its tests: $TESTS at $(git -C "$TESTS" describe --tags) ($(git -C "$TESTS" rev-parse --short HEAD))"
echo "our zlib: $ZLIB/libz.so.1.4, sha256 $(sha256sum "$ZLIB/libz.so.1.4" | cut -c1-16)"
tar -C "$STAGE" -cf - . | $S "rm -rf /data/py313 && mkdir -p /data/py313 && tar -C /data/py313 -xf -"
probe='import sys, zlib; print("python", sys.version.split()[0], sys.platform, "| zlib compiled", zlib.ZLIB_VERSION, "| zlib loaded", zlib.ZLIB_RUNTIME_VERSION)'
run() { $S "cd /data/py313 && PYTHONHOME=/data/py313 PYTHONPATH=/data/py313/tests LD_LIBRARY_PATH=$1 ./bin/python3.13 $2" 2>&1; }
OURS=/data/py313/ourlib:/data/py313/lib
SDP=/data/py313/lib
echo "--- \$ uname -a"; $S "uname -a"
echo "--- with the image's zlib"; run $SDP "-c '$probe'"
echo "--- with qnx-porter's zlib port first on LD_LIBRARY_PATH"; run $OURS "-c '$probe'"
echo "--- CPython's test_zlib and test_gzip, over qnx-porter's zlib"; run $OURS "-m unittest -v test.test_zlib test.test_gzip"
echo "--- the same tests, over the image's zlib (for comparison)"; run $SDP "-m unittest test.test_zlib test.test_gzip" | tail -n 4
$S "rm -rf /data/py313"
