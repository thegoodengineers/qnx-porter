# ryu 1.0.23 on QNX 8.0 (x86_64)

| | |
|---|---|
| Crate | [ryu 1.0.23](https://crates.io/crates/ryu/1.0.23) |
| Rust target | `x86_64-pc-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 46/46 passed (1 ignored) on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Test binaries | 9 |
| Rounds | 2 |
| Patches | 2 |
| Time | 0.4 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-libc-update-libc-0.2.180.patch) | libc-update | libc@0.2.180 | Cargo.lock pins libc 0.2.180, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0002](patches/0002-nto-to-qnx-getrandom-0.4.1.patch) | nto-to-qnx | getrandom@0.4.1 | getrandom 0.4.1 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
