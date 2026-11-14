**Describe the bug**
With the poll(2)-based poller (`src/platform/posix/posix_pollq_poll.c`, the one used when there is no epoll, kqueue or event ports, as on QNX), `nng_fini()` never returns on QNX 8.0. Every test program hangs at exit.

`nni_poll_pq_destroy()` writes to the poll thread's waker pipe, closes the write end and joins the thread. The thread only leaves its loop when `poll()` reports `POLLHUP` on the read end. QNX 8.0 reports `POLLIN` and never `POLLHUP` for a pipe whose last writer has closed (also after the pipe is drained and `read()` returns 0), so the thread clears the pipe, polls, gets `POLLIN` again, and spins. `pq->closed` exists but is never set to true.

**Expected behavior**
`nng_fini()` returns, as on Linux.

**Actual Behavior**
The main thread waits in `nni_thr_fini()` under `nng_fini()` for ever; the poll thread loops between `poll()` and `nni_plat_pipe_clear()`. On a QNX 8.0 x86_64 target, 61 of nng 2.1.0's 64 tests are killed at the test time limit; 3 pass.

**To Reproduce**
Any nng program that calls `nng_fini()`, built for QNX 8.0. The platform behaviour on its own:

```c
#include <poll.h>
#include <stdio.h>
#include <unistd.h>
static void show(const char *what, int fd) {
    struct pollfd p = {fd, POLLIN, 0};
    int n = poll(&p, 1, 1000);
    printf("%-34s poll=%d revents=%#x POLLIN=%d POLLHUP=%d\n", what, n, p.revents,
           !!(p.revents & POLLIN), !!(p.revents & POLLHUP));
}
int main(void) {
    int fds[2];
    char c;
    pipe(fds);
    write(fds[1], "x", 1);
    show("byte waiting, writer open:", fds[0]);
    close(fds[1]);
    show("byte waiting, writer closed:", fds[0]);
    printf("read: %zd\n", read(fds[0], &c, 1));
    show("empty, writer closed:", fds[0]);
    printf("read: %zd (0 = end of file)\n", read(fds[0], &c, 1));
    return 0;
}
```

QNX 8.0 x86_64:
```
byte waiting, writer open:         poll=1 revents=0x1 POLLIN=1 POLLHUP=0
byte waiting, writer closed:       poll=1 revents=0x1 POLLIN=1 POLLHUP=0
read: 1
empty, writer closed:              poll=1 revents=0x1 POLLIN=1 POLLHUP=0
read: 0 (0 = end of file)
```

Linux (glibc):
```
byte waiting, writer open:         poll=1 revents=0x1 POLLIN=1 POLLHUP=0
byte waiting, writer closed:       poll=1 revents=0x11 POLLIN=1 POLLHUP=1
read: 1
empty, writer closed:              poll=1 revents=0x10 POLLIN=0 POLLHUP=1
read: 0 (0 = end of file)
```

** Environment Details **
 - NNG version: v2.1.0; the same code is in `main` at caf6f9f0b220. nng 1.9.0 is not affected on the same target.
 - Operating system and version: QNX SDP 8.0 (build 141), x86_64 target in QEMU
 - Compiler and language used: QCC 12.2.0, C
 - Shared or static library: static; CMake with a QNX toolchain file, `-DNNG_TESTS=ON`

**Additional context**
POSIX describes `POLLHUP` for a FIFO or pipe closed by its last writer, so QNX is arguably the one at fault, but the poller does not need to depend on it. I have a small fix ready: set `pq->closed` under the lock in `nni_poll_pq_destroy()` before waking the thread, and stop the thread when it sees the flag; the `POLLHUP` path stays.
