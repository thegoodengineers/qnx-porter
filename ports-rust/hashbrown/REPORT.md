# hashbrown 0.17.1 on QNX 8.0 (x86_64)

| | |
|---|---|
| Crate | [hashbrown 0.17.1](https://crates.io/crates/hashbrown/0.17.1) |
| Rust target | `x86_64-pc-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 113/113 passed (0 ignored) on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Test binaries | 7 |
| Rounds | 2 |
| Patches | 2 |
| Time | 0.3 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-nto-to-qnx-getrandom-0.3.4.patch) | nto-to-qnx | getrandom@0.3.4 | getrandom 0.3.4 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0002](patches/0002-libc-update-libc-0.2.186.patch) | libc-update | libc@0.2.186 | Cargo.lock pins libc 0.2.186, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
