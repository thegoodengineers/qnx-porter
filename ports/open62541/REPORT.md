# open62541 v1.5.10 on QNX 8.0 (x86_64)

| | |
|---|---|
| Upstream | https://github.com/open62541/open62541.git at `v1.5.10` (`93c3bdfc9ea4`) |
| Build system | cmake |
| Toolchain | QNX SDP 8.0, `qnx-toolchain.cmake` in this folder |
| Build | **built** after 2 round(s) |
| Library's own tests | 0/0 passed on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Patches kept | 2 (2 by rule, 0 by model) |
| Time | 1.9 min |

## Every change, with its reason
| # | Rule | From | Status | Files | Reason |
|---|---|---|---|---|---|
| [0001](patches/0001-add-include-eventloop-posix-h.patch) | add-include | rule | kept | arch/posix/eventloop_posix.h | `LIST_ENTRY` is a BSD list macro from <sys/queue.h>, which QNX 8.0 ships; arch/posix/eventloop_posix.h uses it without including that header. |
| [0002](patches/0002-add-include-eventloop-posix-interrupt-c.patch) | add-include | rule | kept | arch/posix/eventloop_posix_interrupt.c | `LIST_ENTRY` is a BSD list macro from <sys/queue.h>, which QNX 8.0 ships; arch/posix/eventloop_posix_interrupt.c uses it without including that header. |



All kept source changes in one file: `qnx.patch` (apply to the upstream tag with `git apply qnx.patch`).
Build logs for every round: `logs/`.

## Still failing
- nothing
