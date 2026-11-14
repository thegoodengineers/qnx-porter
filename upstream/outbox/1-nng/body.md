fixes #ISSUE_NUMBER nng_fini() hangs where poll() reports no POLLHUP for a closed pipe (QNX 8.0)

`nni_poll_pq_destroy()` relies on `poll()` reporting `POLLHUP` on the waker pipe once its write end is closed. QNX 8.0 reports `POLLIN` only in that case, so the poll thread never leaves its loop and `nng_fini()` never returns (every test hangs at exit).

This sets `pq->closed` (the field exists, but nothing sets it to true today) under the lock before waking the thread, and the thread stops when it sees it, then runs the existing cleanup after the loop. The `POLLHUP` path is unchanged, so platforms that report it behave as before. Only `src/platform/posix/posix_pollq_poll.c` changes.

Testing:
- QNX 8.0 x86_64 target, v2.1.0 with this change: the test suite goes from 3/64 to 60/64 passing. The four still failing (`nng.platform.udp_test`, `nng.sp.transport.ipc.ipc_test`, `nng.sp.transport.tcp.tcp_test`, `nng.sp.reconnect_stress_test`) are separate; I have not looked into them.
- Linux, current `main` with this change and `-DNNG_POLLQ_POLLER=poll` (so the changed file is the poller in use): all tests pass. With the default poller (epoll) all tests pass too.
