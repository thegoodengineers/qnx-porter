# Outbox: upstream contributions

Prepared 14 Nov 2026. With the user's approval, items 1 to 5 were sent the same day from the `Chirag6722`
account (for 2, the issue only); item 6 was not sent. They are **opened and under review**; none is merged.
Each folder holds the patch, the title and body that were pasted, and the `post.sh` that was run; read the
folder's `README.md` first. Run a `post.sh` from an empty working folder (`gh repo fork --clone` clones into the
current folder), with `gh` logged in as `Chirag6722`.

| # | Repository | Kind | Title | Before sending | Sent (14 Nov 2026), open |
|---|---|---|---|---|---|
| 1 | [nanomsg/nng](https://github.com/nanomsg/nng) | issue, then PR | issue: `nng_fini() hangs where poll() reports no POLLHUP for a closed pipe (QNX 8.0)`; PR: `posix pollq: stop the poll thread on a flag, not only on POLLHUP` | `post.sh` opens the issue and puts its number in the commit and PR (nng's commit format is `fixes #<n> <synopsis>`) | [issue #2419](https://github.com/nanomsg/nng/issues/2419), [PR #2420](https://github.com/nanomsg/nng/pull/2420) |
| 2 | [google/googletest](https://github.com/google/googletest) | issue, then PR | issue: `[Bug]: QNX 8.0: threadsafe death tests abort, fchdir() needs a directory opened with O_DIRECTORY`; PR: `Open the saved working directory with O_DIRECTORY in QNX death tests` | **sign the Google CLA**; open the issue first and wait for a maintainer before the PR | [issue #5170](https://github.com/google/googletest/issues/5170); PR waits for the CLA and a maintainer |
| 3 | [cisco/libsrtp](https://github.com/cisco/libsrtp) | PR | `test: shuffle ut_sim's buffer without qsort() and a random comparator` | none (no CONTRIBUTING, CLA or DCO); patch refreshed for `main` | [PR #841](https://github.com/cisco/libsrtp/pull/841) |
| 4 | [nanomsg/nng](https://github.com/nanomsg/nng) | issue, then PR | issue: `posix_udp.c includes the non-POSIX <sys/errno.h>`; PR: `posix_udp: do not include <sys/errno.h>` | same as 1; patch refreshed for `main` (the fix there is deleting the line) | [issue #2421](https://github.com/nanomsg/nng/issues/2421), [PR #2422](https://github.com/nanomsg/nng/pull/2422) |
| 5 | [qnx-ports/build-files](https://github.com/qnx-ports/build-files) | PR | `yyjson: add build files` | none | [PR #343](https://github.com/qnx-ports/build-files/pull/343) |
| 6 | [qnx-ports/build-files](https://github.com/qnx-ports/build-files) | PR | `mbedtls: add build files` | optional, weaker than 5 (x86_64 only through make; 3.6 LTS) | not sent |

Upstream HEADs checked (shallow clones, 14 Nov 2026):

| Repository | Branch | HEAD | Commit date | Patch |
|---|---|---|---|---|
| nanomsg/nng | `main` | `caf6f9f0b220a8e182875707db3fd05142d913ea` | 2026-11-03 | 1: applies as drafted; 4: refreshed |
| google/googletest | `main` | `e882c36410197464e3429546e6a7d5e217bde51e` | 2026-11-13 | applies as drafted |
| cisco/libsrtp | `main` | `052aa2965e2c26f737087492d37a31c3ee09ddba` | 2026-11-13 | refreshed |
| qnx-ports/build-files | `main` | `79d94bd6f1d66e524b17c1f26379ac0ef9bd24c5` | 2026-11-13 | new, applies |

## Not included
- **libconfig** (`tests: do not pass NULL to %s ...`): still present at `master` `bb0dc9a03e35` and the drafted
  patch applies, but it is the weakest of the candidates (test-only, passes on glibc) and the only tested text
  names its helper `qnx_porter_str()` with a tool-specific comment. Renaming it would make it a text we never
  ran. It can be sent later from `docs/upstream/libconfig/` after a rename and a rebuild.
- Everything `docs/upstream/README.md` lists as already fixed upstream or not applicable (json-c, tinyxml2,
  libxml2, paho.mqtt.c, capstone, nng test logger).
- The other 32 build-files recipes. All 34 built (`recipes/BUILD_CHECK.md`); yyjson and mbedtls were picked
  because their ports need no source patch and passed all their tests on the target (12/12, 130/130), and
  yyjson was also built for aarch64. The next candidate would be cmocka (46/46, no source patch).
