# Not a QNX bug: libsrtp's tests sort with a random comparator

**Status:** finding for libsrtp (the fix belongs upstream there, not in QNX). Found by qnx-porter's campaign:
3 of libsrtp 2.6.0's tests crash or fail on QNX 8.0. Reproduced with `qsort_inconsistent_comparator.c`
(this folder) on 12 Nov 2026.

## What happens
libsrtp's test helper `test/ut_sim.c` shuffles a 160-entry buffer by calling `qsort()` with a comparator that
returns -1 or 1 at random. C17 7.22.5p4 requires a comparator's answers to be consistent, so this is undefined
behaviour. glibc's `qsort` happens to stay inside the array anyway; QNX 8.0's does not, and overwrites memory
next to it.

`qsort_inconsistent_comparator.c` sorts a 160-element array between guard words 2,000 times:
```
QNX 8.0 x86_64:  480 of 2000 qsort calls wrote outside the array
Linux (glibc):   0 of 2000 qsort calls wrote outside the array
```

## Effect seen (`ports-2024/libsrtp/logs/tests.log`, `logs/crashes.log`)
- `roc_driver`: SIGSEGV in `ut_next_index()` (test/ut_sim.c:81); the `ut_connection` pointer on the stack has
  been overwritten (`utc=0x3515583000000000`).
- `rdbx_driver`: SIGSEGV in `bitvector_left_shift()` called from the test's `rdbx_check_add_unordered()`, fed
  by the same helper.
- `replay_driver`: `rdb_check_add_unordered failed at index 150`, same helper.

## Fix (for libsrtp; sent as [cisco/libsrtp PR #841](https://github.com/cisco/libsrtp/pull/841), open, under review)
`libsrtp-ut-sim-shuffle.patch` (this folder) shuffles with a Fisher-Yates loop driven by the same test random
source instead of `qsort()`. Built with qcc and run on the same QNX 8.0 target, `rdbx_driver`,
`replay_driver` and `roc_driver` all exit 0; built for Linux, all three still exit 0. The library code itself
(`srtp_rdbx_*`, `bitvector_*`) needs no change.
