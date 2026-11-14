# Python on QNX over a qnx-porter port

Python's `zlib` and `gzip` modules are thin wrappers around the zlib C library. That is the case the README's
"Why C and C++" makes: port the C layer, and the languages that wrap it follow. Here the wrapping language runs on
QNX itself, over our port.

## What ran
- **Python:** the CPython 3.13.7 that SDP 8.0 ships for QNX (`target/qnx/x86_64/usr/bin/python3.13` and its
  standard library). We did not build it. Its `zlib` module was compiled against the SDP's zlib 1.2.13
  (`libz.so.2`, which the target image also has in `/proc/boot`).
- **zlib:** qnx-porter's port of madler/zlib `v1.4` (`99623ef70973`), made with
  `qnx-porter port https://github.com/madler/zlib.git --tag v1.4 --no-model`: built in one round with no patch.
  zlib's CMake builds the shared library too (`libz.so.1.4`). zlib keeps one ABI across versions, so our
  `libz.so.1.4` goes first on `LD_LIBRARY_PATH` under the name the module asks for, `libz.so.2`.
- **Tests:** CPython's own `Lib/test/test_zlib.py` and `Lib/test/test_gzip.py` from the `v3.13.7` tag, with
  `Lib/test/support`. The SDP ships no test suite, so they come from the CPython repository.
- **Target:** QNX 8.0 x86_64 in QEMU, the same image as the campaign.

[`scripts/python_on_qnx.sh`](../scripts/python_on_qnx.sh) does all of it and says how to prepare the two inputs.
It runs the tests twice: over our zlib, then over the image's zlib for comparison.

## Result (14 Nov 2026, [`results/runs/python-on-qnx.log`](../results/runs/python-on-qnx.log))
```
--- with the image's zlib
python 3.13.7 qnx | zlib compiled 1.2.13 | zlib loaded 1.2.13
--- with qnx-porter's zlib port first on LD_LIBRARY_PATH
python 3.13.7 qnx | zlib compiled 1.2.13 | zlib loaded 1.4
--- CPython's test_zlib and test_gzip, over qnx-porter's zlib
...
Ran 148 tests in 2.545s

OK (skipped=2)
--- the same tests, over the image's zlib (for comparison)
...
Ran 148 tests in 3.517s

OK (skipped=2)
```
`zlib.ZLIB_RUNTIME_VERSION` shows that the module really loaded our library (1.4), not the image's (1.2.13). All
148 tests of the two modules ran over our zlib with no failure, as over the image's. Both runs skip 2; the
verbose run over our zlib names them: `test_big_buffer` needs 4 GB of memory, and `test_refleaks_in___init__`
needs a debug build of Python.

## What this does not show
- It is one library under one wrapper. Python modules that wrap other C libraries (`sqlite3`, `ssl`, `ctypes`
  users such as PyNaCl) were not tried this way.
- The zlib port's own C tests ran in the campaign (`results/ports.csv`, row zlib: 4/4); this run adds
  CPython's tests on top of the same source, built once more on its own.
- QEMU, not hardware, as everywhere in this repository.
