# Draft pull request for libsrtp (sent 14 Nov 2026 as [PR #841](https://github.com/cisco/libsrtp/pull/841), from the refreshed text in [`upstream/outbox/3-libsrtp/`](../../../upstream/outbox/3-libsrtp/))

- **Upstream:** https://github.com/cisco/libsrtp
- **Patch:** [`0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch`](0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch),
  made with `git format-patch` against tag `v2.6.0` (`fd08747fa680`, the tag in `campaign.yaml`). Source:
  [`docs/qnx-reports/libsrtp-ut-sim-shuffle.patch`](../../qnx-reports/libsrtp-ut-sim-shuffle.patch).
- **Upstream today:** `main` at `1ed1396ff66c` (13 Nov 2026) still calls `qsort(..., ut_compar)` in
  `test/ut_sim.c` (lines 74 and 87). The patch does not apply to `main` as it is: the `for` loop above the first
  `qsort()` now has braces, so that hunk's context needs refreshing. The change itself is the same.

## Why upstream would want it
Undefined-behaviour hygiene in a test helper. `ut_compar()` answers -1 or 1 at random, and C17 7.22.5p4
requires a `qsort()` comparator to be consistent. glibc's `qsort` happens to stay inside the array; a `qsort`
that relies on the comparator can write past it, and then the replay-database tests fail for a reason that has
nothing to do with libsrtp. A Fisher-Yates shuffle with the same test random source does what the helper means
to do. The library code (`srtp_rdbx_*`, `bitvector_*`) is not touched.

## Verification, from our logs
Without the patch, libsrtp 2.6.0's tests on the QNX 8.0 x86_64 target (`ports-2024/libsrtp/logs/tests.log`):
```
FAIL  rdbx_driver (exit 139)
FAIL  replay_driver (exit 1)
FAIL  roc_driver (exit 139)
8/12 tests passed on the QNX target
```
`roc_driver`'s core (`ports-2024/libsrtp/logs/crashes.log`) shows the test's own pointer overwritten:
```
#0  0x00000043e59fce5e in ut_next_index (utc=utc@entry=0xa3fcd98000000000) at .../test/ut_sim.c:81
```
The cause on its own, `qsort_inconsistent_comparator.c` (160 elements between guard words, 2,000 calls;
[`docs/qnx-reports/qsort-inconsistent-comparator.md`](../../qnx-reports/qsort-inconsistent-comparator.md)):
```
QNX 8.0 x86_64:  480 of 2000 qsort calls wrote outside the array
Linux (glibc):   0 of 2000 qsort calls wrote outside the array
```
With the patch (same document): built with qcc and run on the same target, `rdbx_driver`, `replay_driver` and
`roc_driver` all exit 0; built for Linux, all three still exit 0.

**Not verified:** the patch rebuilt on `main`. The fourth failing test, `rtpw_test` (exit 254), is a separate
matter and this patch does not claim to fix it.

## PR title
```
test: shuffle ut_sim's buffer without qsort() and a random comparator
```

## PR body
```
ut_init() and ut_next_index() in test/ut_sim.c shuffle the buffer by calling qsort() with
ut_compar(), which returns -1 or 1 at random. C (C17 7.22.5p4) requires a qsort() comparator
to be consistent, so this is undefined behaviour. glibc's qsort happens to stay inside the
array, but a qsort that relies on the comparator can write past it: on QNX 8.0, a 2,000-call
guard-word test saw 480 out-of-bounds writes. That corrupts the test's stack and makes
rdbx_driver, replay_driver and roc_driver crash or fail.

This shuffles with a Fisher-Yates pass driven by the same test random source
(srtp_cipher_rand_for_tests) instead. Library code is unchanged.

Tested with v2.6.0: rdbx_driver, replay_driver and roc_driver exit 0 on QNX 8.0 x86_64 (they
crashed or failed before) and still exit 0 on Linux.
```
