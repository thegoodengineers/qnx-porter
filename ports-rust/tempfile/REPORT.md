# tempfile 3.27.0 on QNX 8.0 (x86_64)

| | |
|---|---|
| Crate | [tempfile 3.27.0](https://crates.io/crates/tempfile/3.27.0) |
| Rust target | `x86_64-pc-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 61/63 passed (0 ignored) on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Test binaries | 6 |
| Rounds | 5 |
| Patches | 6 |
| Time | 0.6 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-nto-to-qnx-getrandom-0.4.1.patch) | nto-to-qnx | getrandom@0.4.1 | getrandom 0.4.1 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0002](patches/0002-libc-update-libc-0.2.182.patch) | libc-update | libc@0.2.182 | Cargo.lock pins libc 0.2.182, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0003](patches/0003-nto-to-qnx-rustix-1.1.4.patch) | nto-to-qnx | rustix@1.1.4 | rustix 1.1.4 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0004](patches/0004-libc-update-libc-0.2.191.patch) | libc-update | libc@0.2.191 | Cargo.lock pins libc 0.2.191, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0005](patches/0005-nto-to-qnx-getrandom-0.4.3.patch) | nto-to-qnx | getrandom@0.4.3 | getrandom 0.4.3 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0006](patches/0006-nto-to-qnx-errno-0.3.14.patch) | nto-to-qnx | errno@0.3.14 | errno 0.3.14 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
