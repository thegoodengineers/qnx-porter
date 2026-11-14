`ut_init()` and `ut_next_index()` in `test/ut_sim.c` shuffle the buffer by calling `qsort()` with `ut_compar()`, which returns -1 or 1 at random. C (C17 7.22.5p4) requires a `qsort()` comparator to be consistent, so this is undefined behaviour. glibc's `qsort` happens to stay inside the array, but a `qsort` that relies on the comparator can write past it: on QNX 8.0, a 2,000-call guard-word test saw 480 out-of-bounds writes (glibc: 0). That corrupts the test's stack and makes `rdbx_driver`, `replay_driver` and `roc_driver` crash or fail there.

This shuffles with a Fisher-Yates pass driven by the same test random source (`srtp_cipher_rand_for_tests`) instead. Library code is unchanged; `ut_compar()` is left in place.

Testing:
- v2.6.0 with this change: `rdbx_driver`, `replay_driver` and `roc_driver` exit 0 on QNX 8.0 x86_64 (before: `rdbx_driver` and `roc_driver` crashed with SIGSEGV, `replay_driver` exited 1) and still exit 0 on Linux.
- This branch (the same change on current `main`): builds on Linux (Ubuntu 22.04, gcc 11.4, `-DCRYPTO_LIBRARY=internal`, warnings as errors on by default) and the whole ctest suite passes.
