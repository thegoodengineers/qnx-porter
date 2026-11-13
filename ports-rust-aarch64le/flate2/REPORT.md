# flate2 1.1.11 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Crate | [flate2 1.1.11](https://crates.io/crates/flate2/1.1.11) |
| Rust target | `aarch64-unknown-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 97/97 passed (0 ignored) on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Test binaries | 10 |
| Rounds | 2 |
| Patches | 2 |
| Time | 0.7 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-nto-to-qnx-getrandom-0.4.3.patch) | nto-to-qnx | getrandom@0.4.3 | getrandom 0.4.3 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0002](patches/0002-nto-to-qnx-getrandom-0.3.4.patch) | nto-to-qnx | getrandom@0.3.4 | getrandom 0.3.4 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
