# On-target diagnosis with QNX's own tools

When a library's test misbehaves on the QNX target, qnx-porter records what QNX itself can say about it, and puts
that in the port's `REPORT.md`. Every target here is QEMU (x86_64 under KVM, aarch64 emulated), never hardware.

| Symptom | What qnx-porter records | QNX tools used |
|---|---|---|
| A test crashes | the core dump from the image's `dumper`, read on the host with the SDP's gdb: a backtrace with file and line | `dumper`, `ntox86_64-gdb` / `ntoaarch64-gdb` |
| A test hangs (still running when its time limit is near) | each thread's state, what it is blocked on and its last kernel call, then a 2 s kernel trace summarised per thread | [`pidin`](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/p/pidin.html), [`tracelogger`](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/tracelogger.html), [`traceprinter`](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.neutrino.utilities/topic/t/traceprinter.html) |
| A build stops on a Linux kernel interface | each Linux-only interface the source uses and QNX's equivalent | (source scan; [`qnx_porter/advisor.py`](../qnx_porter/advisor.py)) |

## Hangs: `pidin` and a kernel trace, taken before the test is killed
Each test runs on the target under QNX's `timeout`. Beside it, a watcher ([`qnx_porter/hang.py`](../qnx_porter/hang.py))
sleeps until 8 s before the limit. If the test is still running then, the watcher:
1. runs `pidin -p <pid> -F "%a %b %N %J %B %K"` for every process whose executable is under the port's trees
   (`/proc/<pid>/exefile`): pid, tid, name, thread state, what the thread is blocked on, last kernel call;
2. runs `tracelogger -s 2`, which logs all kernel events for 2 s (the image runs the instrumented kernel,
   `procnto-smp-instr`, which `tracelogger` needs).

After QNX's `timeout` has killed the test, qnx-porter copies the `.kev` file back, prints it with the SDP's
`traceprinter`, and counts, per thread of the stuck processes, how often it was scheduled (`THRUNNING`) and which
kernel calls it made. Kernel-call events carry no pid, so each one is attributed to the thread that the last
`THRUNNING` event put on that CPU. The REPORT.md section "Hang on QNX" shows the first three; `logs/hangs.log` has
all of them, and `logs/hang-1.kev` to `hang-3.kev` keep the first three raw traces (about 50 MB each for 2 s)
for QNX's IDE or `traceprinter`; later ones keep only the summary.

A thread with no kernel calls in the window is waiting, and `pidin` says on what (`CONDVAR`, `REPLY <pid>`,
`RECEIVE`, ...). A thread with thousands of calls is spinning.

Two QNX shell details we hit while building this, both checked on the x86_64 target:
- QNX's `sh` cannot parse a `case` pattern inside `$( )` ("syntax error: `;;' unexpected"); the watcher uses a
  `${e#*path}` test instead.
- With `( ... ) >/dev/null 2>&1 &`, the shell kept copies of the ssh session's descriptors, the watcher's `sleep`
  inherited them, and every test's ssh session waited for the watcher (a 1 s test took 25 s). Redirecting with
  `exec` inside the subshell fixed it (1.3 s).

## Adaptive partitioning: not available on QNX 8.0
We wanted to run one ported library's latency benchmark inside an adaptive-partitioning (APS) partition with a CPU
budget while a load generator ran in another, and compare it with no partition. QNX OS 8.0 does not support
adaptive partitioning. QNX's own 8.0 documentation says so
([QNX IDE User's Guide, APS View](https://www.qnx.com/developers/docs/8.0/com.qnx.doc.ide.userguide/topic/APS_view.html):
"QNX OS 8.0 does not support adaptive partitioning"), and what we have agrees: the 8.0 target image has no `aps`
utility, and SDP 8.0 (build 141) ships no APS header or scheduler interface. So that experiment was not run; the
real-time measurements we have are in [RT_RESULTS.md](RT_RESULTS.md): the latency of one call at SCHED_FIFO
priority 60, idle, under load, and under load with the measuring thread isolated on its own CPU by runmask.
