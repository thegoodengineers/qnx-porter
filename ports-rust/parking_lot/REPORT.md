# parking_lot 0.13.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Crate | [parking_lot 0.13.0](https://crates.io/crates/parking_lot/0.13.0) |
| Rust target | `x86_64-pc-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 100/100 passed (0 ignored) on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Test binaries | 3 |
| Rounds | 2 |
| Patches | 1 |
| Time | 0.3 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-nto-to-qnx-getrandom-0.4.3.patch) | nto-to-qnx | getrandom@0.4.3 | getrandom 0.4.3 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
