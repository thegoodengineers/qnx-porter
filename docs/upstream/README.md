# Upstream patches and pull-request drafts (none sent)

Source fixes from the ports that the original projects could take. Nothing here has been sent: each draft
waits for a person to review it, sign it as themselves and open it. Each draft folder holds the patch
(`git format-patch` against the tag in [`campaign.yaml`](../../campaign.yaml), checked to apply there) and a
`PR.md` with the upstream URL, the reason, verification quoted from our logs, and a title and body to paste.

Candidates come from two places: the ports' kept patches, listed by `scripts/upstream.py` in
[`results/upstream.md`](../../results/upstream.md), and the findings in [`docs/qnx-reports/`](../qnx-reports/)
and [`docs/LEARNINGS.md`](../LEARNINGS.md). Upstream's default branch was checked read-only on 13 Nov 2026.

| Project | Patch | Status | Why |
|---|---|---|---|
| googletest | [googletest/0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch](googletest/0001-Open-the-saved-working-directory-with-O_DIRECTORY-in.patch) | draft ([PR.md](googletest/PR.md)) | QNX death-test path calls `fchdir()` on a directory opened without `O_DIRECTORY`; still in `main` `2910168b8bc1`, patch applies |
| libsrtp | [libsrtp/0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch](libsrtp/0001-test-shuffle-ut_sim-s-buffer-without-qsort-and-a-ran.patch) | draft ([PR.md](libsrtp/PR.md)) | `qsort()` with a random comparator is undefined C; still in `main` `1ed1396ff66c` (hunk context needs a refresh) |
| libconfig | [libconfig/0001-tests-do-not-pass-NULL-to-s-in-parse_string_and_comp.patch](libconfig/0001-tests-do-not-pass-NULL-to-s-in-parse_string_and_comp.patch) | draft ([PR.md](libconfig/PR.md)) | test passes NULL to `%s`; still in `master` `a82aa4dd3baf`, patch applies |
| nng (posix_udp.c) | [nng/0001-posix_udp-include-errno.h-instead-of-sys-errno.h.patch](nng/0001-posix_udp-include-errno.h-instead-of-sys-errno.h.patch) | draft ([PR.md](nng/PR.md)) | `<sys/errno.h>` is not POSIX; still in `main` `caf6f9f0b220`, where the fix becomes deleting that line |
| nng (poller shutdown) | [nng-pollhup/0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch](nng-pollhup/0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch) | draft ([PR.md](nng-pollhup/PR.md)) | QNX 8.0 reports no `POLLHUP` when a pipe's writer closes, so nng 2.x's poll thread never stops and every test hangs in `nng_fini()`; patch applies to `v2.1.0` and `main` `caf6f9f0b220`; QNX tests 3/64 to 60/64 |
| json-c | `ports/json-c/patches/0001-printf-null-test-json-patch-c.patch` | already fixed upstream | `master` commit `52f57ec18a01` ("AIX: Fix test_json_patch NULL pointer passed to printf") wraps the NULL argument in `STR_OR_NULL` |
| tinyxml2 | `ports/tinyxml2/patches/0001-printf-null-xmltest-cpp.patch` | already fixed upstream | `master` commit `935ddecc910a` ("Null checks in test output (#1076)") maps NULL `expected`/`found` to `"(null)"`, the two arguments that were NULL in our crash |
| libxml2 | none | already fixed upstream | `xmlSAX2ResolveEntity()` warned with a NULL `systemId`; `master` (`21c8223ac091`) now checks `systemId != NULL` first (LEARNINGS, 12 Nov) |
| paho.mqtt.c | `ports/paho.mqtt.c/patches/0001-bool-typedef-mqttpacket-h.patch` | already fixed upstream | `master` commit `9ff08fa5a78f` ("#1576 Changed 'bool' typedef to 'bit'") removes the clashing typedef |
| capstone | `ports/capstone/patches/0001-printf-null-test-iter-c.patch` | not applicable | `tests/test_iter.c` no longer exists on the default branch `next`; it is unchanged on the `v5` maintenance branch, a test-only fix for that branch only |
| nng (test logger) | none | not applicable (no tested fix) | `src/testing/util.c` `nuts_logger()` prints a NULL `msgid` with `%s` (still in `main`), but we never wrote, built or ran a fix, so there is nothing to quote as verification |

## Related
- [qnx-ports-build-files-PR.md](qnx-ports-build-files-PR.md): the draft PR for QNX's own `qnx-ports/build-files`
  (build recipes for 34 libraries), also not sent.
