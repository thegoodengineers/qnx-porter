# nng v2.1.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/nanomsg/nng.git at `v2.1.0` (`0912dcbd63f2`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 3/64 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 1 (1 by rule, 0 by model) |
| Time | 69.4 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-header-alias-posix-udp-c.patch) | header-alias | rule | kept | src/platform/posix/posix_udp.c | <sys/errno.h> is a glibc alias QNX 8.0 does not ship; POSIX's <errno.h> declares the same things, and QNX has it. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing

## Hang on QNX: nng.core.aio_test
Killed at its time limit. Just before, on the target (`pidin`: state, blocked on, last kernel call):
```
     pid tid name               STATE          Blocked                      kernel call      
13250582   1 aio_test           REPLY          1                            msg_sendv
     pid tid name               STATE          Blocked                      kernel call      
13254680   1 aio_test           CONDVAR        (0x37fdf8e610)               sync_condvar_wa
13254680   2 aio_test           RUNNING                                     msg_sendv
13254680   3 aio_test           SIGWAITINFO                                 signal_waitinfo
13254680   4 aio_test           SIGWAITINFO                                 signal_waitinfo
13254680   5 aio_test           SIGWAITINFO                                 signal_waitinfo

killed on the target after 60 s
```
Kernel trace (`tracelogger`, read with `traceprinter`), per thread:
```
pid 13254680 tid 2: ran 93655 time(s), 185539 kernel call(s) (MSG_SENDV x92769, SYNC_CONDVAR_SIGNAL x46385, SIGNAL_ACTION x46385)
pid(s) 13250582: no thread ran during the trace
```

## Hang on QNX: nng.core.args_test
Killed at its time limit. Just before, on the target (`pidin`: state, blocked on, last kernel call):
```
     pid tid name               STATE          Blocked                      kernel call      
15302678   1 args_test          REPLY          1                            msg_sendv
     pid tid name               STATE          Blocked                      kernel call      
15306776   1 args_test          CONDVAR        (0x5c21743560)               sync_condvar_wa
15306776   2 args_test          RUNNING                                                      
15306776   3 args_test          SIGWAITINFO                                 signal_waitinfo
15306776   4 args_test          SIGWAITINFO                                 signal_waitinfo
15306776   5 args_test          SIGWAITINFO                                 signal_waitinfo

killed on the target after 60 s
```
Kernel trace (`tracelogger`, read with `traceprinter`), per thread:
```
pid 15306776 tid 2: ran 101187 time(s), 200695 kernel call(s) (MSG_SENDV x100347, SYNC_CONDVAR_SIGNAL x50174, SIGNAL_ACTION x50174)
pid(s) 15302678: no thread ran during the trace
```

## Hang on QNX: nng.core.buf_size_test
Killed at its time limit. Just before, on the target (`pidin`: state, blocked on, last kernel call):
```
     pid tid name               STATE          Blocked                      kernel call      
16642070   1 buf_size_test      CONDVAR        (0x154dd1d470)               sync_condvar_wa
16642070   2 buf_size_test      REPLY                                       msg_sendv
16642070   3 buf_size_test      SIGWAITINFO                                 signal_waitinfo
16642070   4 buf_size_test      SIGWAITINFO                                 signal_waitinfo
16642070   5 buf_size_test      SIGWAITINFO                                 signal_waitinfo

killed on the target after 60 s
```
Kernel trace (`tracelogger`, read with `traceprinter`), per thread:
```
pid 16642070 tid 2: ran 102023 time(s), 202328 kernel call(s) (MSG_SENDV x101164, SYNC_CONDVAR_SIGNAL x50582, SIGNAL_ACTION x50582)
```

57 more tests hung the same way: `logs/hangs.log`.
