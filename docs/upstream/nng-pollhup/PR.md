# Draft pull request for nng: poller shutdown without POLLHUP (sent 14 Nov 2026 as [issue #2419](https://github.com/nanomsg/nng/issues/2419) and [PR #2420](https://github.com/nanomsg/nng/pull/2420))

- **Upstream:** https://github.com/nanomsg/nng
- **Patch:** [`0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch`](0001-posix-pollq-stop-the-poll-thread-on-a-flag-not-only-on-POLLHUP.patch),
  `git format-patch` output. `git apply --check` passes on tag `v2.1.0` (`0912dcbd63f2`, the tag in
  `campaign.yaml`) and on `main` at `caf6f9f0b220` (checked 14 Nov 2026).
- **Finding:** [`docs/qnx-reports/pipe-pollhup.md`](../../qnx-reports/pipe-pollhup.md).

## Why upstream would want it
On QNX 8.0 every nng program hangs in `nng_fini()`. `nni_poll_pq_destroy()` writes to the poll thread's waker
pipe, closes the write end and joins the thread; the thread leaves its loop only when `poll()` reports
`POLLHUP` on the read end. QNX 8.0 reports `POLLIN` and never `POLLHUP` for a pipe whose writer has closed, so
the thread drains the pipe, polls, and spins. The patch sets `pq->closed` (a field that exists but is never set
to true today) under the lock before waking the thread, and the thread stops when it sees it. The `POLLHUP`
path stays as it is.

## Verification, from our logs
QNX 8.0 x86_64 target in QEMU, nng v2.1.0 built with qcc 12.2.0 by qnx-porter (`-DNNG_TESTS=ON`):
- without the patch, 3 of 64 tests passed; the other 61 were killed at the time limit
  (`ports/nng/logs/tests.log`);
- with the patch, 60 of 64 passed ([`tests-qnx-x86_64-patched.log`](tests-qnx-x86_64-patched.log)). Still
  failing: `nng.platform.udp_test`, `nng.sp.transport.ipc.ipc_test`, `nng.sp.transport.tcp.tcp_test` (exit 1)
  and `nng.sp.reconnect_stress_test` (time limit). We have not looked into these four.

Linux (WSL Ubuntu 22.04, gcc 11.4.0), same tag, `ctest --timeout 300 -j2`:
- without the patch, 73 of 74 passed; `nng.sp.transport.udp.udp_tran_test` failed in that one run
  ([`tests-linux-plain.log`](tests-linux-plain.log)); we did not look into it;
- with the patch, 74 of 74 passed ([`tests-linux-patched.log`](tests-linux-patched.log)).

Correction (14 Nov 2026): these two Linux runs used nng's default poller on Linux, epoll, so they never
compiled `posix_pollq_poll.c`, the file the patch changes; they only show the patch does not break the build.
The final text in [`upstream/outbox/1-nng/`](../../../upstream/outbox/1-nng/) adds a Linux run on `main` with
`-DNNG_POLLQ_POLLER=poll`, where the changed file is the poller in use (all tests passed; that run's log is not
committed, so the text only says "all tests pass").

## Title and body to paste
**posix pollq: stop the poll thread on a flag, not only on POLLHUP**

`nni_poll_pq_destroy()` relies on `poll()` reporting `POLLHUP` on the waker pipe once its write end is closed.
QNX 8.0 reports `POLLIN` only in that case, so the poll thread never leaves its loop and `nng_fini()` never
returns (every test hangs at exit). This sets `pq->closed` under the lock before waking the thread and stops
the thread when it is set; platforms that report `POLLHUP` are unaffected. On a QNX 8.0 x86_64 target the test
suite goes from 3/64 to 60/64; on Linux all 74 tests pass with the change.
