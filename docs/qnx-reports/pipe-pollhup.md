# QNX 8.0: poll() reports no POLLHUP on a pipe whose writer has closed

**Status:** draft report for QNX, not sent. The fix for nng ([`docs/upstream/nng-pollhup/`](../upstream/nng-pollhup/))
was sent on 14 Nov 2026 as [nng issue #2419](https://github.com/nanomsg/nng/issues/2419) and [PR #2420](https://github.com/nanomsg/nng/pull/2420) (open, under review). Found by qnx-porter's campaign (every nng 2.1.0 test hung until its timeout), reproduced with
`pipe_pollhup.c` (this folder) on 13 Nov 2026.

## Summary
On QNX SDP 8.0 (build 141, x86_64 target in QEMU), once the last write end of a pipe is closed, `poll()` on the
read end reports `POLLIN` and never `POLLHUP`, also after the pipe is drained and `read()` returns 0 (end of
file). Linux reports `POLLHUP`. POSIX.1-2024 describes `POLLHUP` as "a device has been disconnected, or a pipe
or FIFO has been closed by the last process that had it open for writing"
([poll()](https://pubs.opengroup.org/onlinepubs/9799919799/functions/poll.html)).

## Reproduce
```
qcc -Vgcc_ntox86_64 pipe_pollhup.c -o pipe_pollhup
gcc pipe_pollhup.c -o pipe_pollhup_linux
```

On the QNX 8.0 x86_64 target:
```
byte waiting, writer open:         poll=1 revents=0x1 POLLIN=1 POLLHUP=0
byte waiting, writer closed:       poll=1 revents=0x1 POLLIN=1 POLLHUP=0
read: 1
empty, writer closed:              poll=1 revents=0x1 POLLIN=1 POLLHUP=0
read: 0 (0 = end of file)
```

On Linux (glibc, WSL Ubuntu 22.04):
```
byte waiting, writer open:         poll=1 revents=0x1 POLLIN=1 POLLHUP=0
byte waiting, writer closed:       poll=1 revents=0x11 POLLIN=1 POLLHUP=1
read: 1
empty, writer closed:              poll=1 revents=0x10 POLLIN=0 POLLHUP=1
read: 0 (0 = end of file)
```

The pipe itself behaves: `O_NONBLOCK` set with `fcntl(F_SETFL)` makes `read()` of an empty pipe return
`EAGAIN`, and a reader that waits for `read()` to return 0 sees the end of file.

## Effect seen: nng 2.1.0 never shuts down
nng's poll-based poller (`src/platform/posix/posix_pollq_poll.c`, the one nng picks when there is no epoll or
kqueue, as on QNX) stops its thread like this: `nng_fini()` writes a byte to the thread's wake-up pipe, closes the
write end, and joins the thread. The thread leaves its loop only when `poll()` reports `POLLHUP` on that pipe. On
QNX it gets `POLLIN`, drains the pipe, polls again, gets `POLLIN` again, and spins. Every nng test calls
`nng_fini()` when it ends, so 61 of the 64 tests ran into the 300 s timeout (`ports/nng/logs/tests.log`).

How we found it, on the target: `pidin` showed the test's main thread in `CONDVAR` and one nng thread
alternating between `RUNNING` and `REPLY`. A core dump read with the SDP's gdb put the main thread in
`nni_thr_fini()` under `nng_fini()`, and the other thread in `read()` from `nni_plat_pipe_clear()`. A debug print
showed the pipe was non-blocking and the clear loop running without end.

nng 1.9.0 passed 82 of 86 tests on the same target (`ports-2024/nng/logs/tests.log`), so this came in with 2.x.

## What to do
For QNX: report `POLLHUP` when the last writer of a pipe or FIFO closes, as POSIX describes.

For portable code: do not rely on `POLLHUP` alone to see that a pipe's writer is gone. Treat `read()` returning 0
as the end, or, as in the nng draft, set a flag under a lock before waking the thread.
