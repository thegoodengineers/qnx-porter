# Upstream patches and pull-request drafts

Source fixes from the ports that the original projects could take. Each draft waited for a person to review
it, sign it as themselves and open it; on 14 Nov 2026 the user sent five of them (open, under review, none
merged), listed with their links in [`upstream/outbox/README.md`](../../upstream/outbox/README.md). Each draft folder holds the patch
(`git format-patch` against the tag in [`campaign.yaml`](../../campaign.yaml), checked to apply there) and a
`PR.md` with the upstream URL, the reason, verification quoted from our logs, and a title and body to paste.

Candidates come from two places: the ports' kept patches, listed by `scripts/upstream.py` in
[`results/upstream.md`](../../results/upstream.md), and the findings in [`docs/qnx-reports/`](../qnx-reports/)
and [`docs/LEARNINGS.md`](../LEARNINGS.md). Upstream's default branch was checked read-only on 13 Nov 2026.

| Project | Patch | Status | Why |
|---|---|---|---|
| googletest | [googletest/0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch](googletest/0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch) | issue [#5170](https://github.com/google/googletest/issues/5170) sent; PR not sent ([PR.md](googletest/PR.md)) | QNX death-test path calls `fchdir()` on a directory opened without `O_DIRECTORY`; still in `main` `2910168b8bc1`, patch applies |
| libsrtp | [libsrtp/0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch](libsrtp/0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch) | sent, [PR #841](https://github.com/cisco/libsrtp/pull/841) ([PR.md](libsrtp/PR.md)) | `qsort()` with a random comparator is undefined C; still in `main` `1ed1396ff66c` (hunk context needs a refresh) |
| libconfig | [libconfig/0001-tests-do-not-pass-NULL-to-s-in-parse_string_and_comp.patch](libconfig/0001-tests-do-not-pass-NULL-to-s-in-parse_string_and_comp.patch) | draft ([PR.md](libconfig/PR.md)) | test passes NULL to `%s`; still in `master` `a82aa4dd3baf`, patch applies |
| nng (posix_udp.c) | [nng/0001-posix_udp-include-errno.h-instead-of-sys-errno.h.patch](nng/0001-posix_udp-include-errno.h-instead-of-sys-errno.h.patch) | sent, [PR #2422](https://github.com/nanomsg/nng/pull/2422) ([PR.md](nng/PR.md)) | `<sys/errno.h>` is not POSIX; still in `main` `caf6f9f0b220`, where the fix becomes deleting that line |
| nng (poller shutdown) | [nng-pollhup/0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch](nng-pollhup/0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch) | sent, [PR #2420](https://github.com/nanomsg/nng/pull/2420) ([PR.md](nng-pollhup/PR.md)) | QNX 8.0 reports no `POLLHUP` when a pipe's writer closes, so nng 2.x's poll thread never stops and every test hangs in `nng_fini()`; patch applies to `v2.1.0` and `main` `caf6f9f0b220`; QNX tests 3/64 to 60/64 |
| json-c | `ports/json-c/patches/0001-printf-null-test-json-patch-c.patch` | already fixed upstream | `master` commit `52f57ec18a01` ("AIX: Fix test_json_patch NULL pointer passed to printf") wraps the NULL argument in `STR_OR_NULL` |
| tinyxml2 | `ports-2024/tinyxml2/patches/0001-printf-null-xmltest-cpp.patch` | already fixed upstream | `master` commit `935ddecc910a` ("Null checks in test output (#1076)") maps NULL `expected`/`found` to `"(null)"`, the two arguments that were NULL in our crash |
| libxml2 | none | already fixed upstream | `xmlSAX2ResolveEntity()` warned with a NULL `systemId`; `master` (`21c8223ac091`) now checks `systemId != NULL` first (LEARNINGS, 12 Nov) |
| paho.mqtt.c | `ports-2024/paho.mqtt.c/patches/0001-bool-typedef-mqttpacket-h.patch` | already fixed upstream | `master` commit `9ff08fa5a78f` ("#1576 Changed 'bool' typedef to 'bit'") removes the clashing typedef |
| capstone | `ports/capstone/patches/0001-printf-null-test-iter-c.patch` | not applicable | `tests/test_iter.c` no longer exists on the default branch `next`; it is unchanged on the `v5` maintenance branch, a test-only fix for that branch only |
| nng (test logger) | none | not applicable (no tested fix) | `src/testing/util.c` `nuts_logger()` prints a NULL `msgid` with `%s` (still in `main`), but we never wrote, built or ran a fix, so there is nothing to quote as verification |

## Related
- [qnx-ports-build-files-PR.md](qnx-ports-build-files-PR.md): the draft PR for QNX's own `qnx-ports/build-files`
  (build recipes for 34 libraries), not sent; the yyjson recipe alone was sent as
  [build-files PR #343](https://github.com/qnx-ports/build-files/pull/343).
