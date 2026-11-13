# getrandom 0.4.3 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Crate | [getrandom 0.4.3](https://crates.io/crates/getrandom/0.4.3) |
| Rust target | `aarch64-unknown-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 9/9 passed (0 ignored) on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Test binaries | 3 |
| Rounds | 3 |
| Patches | 2 |
| Time | 0.5 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-nto-to-qnx-getrandom-0.4.3.patch) | nto-to-qnx | getrandom-0.4.3 | The crate supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0002](patches/0002-libc-update-libc-0.2.186.patch) | libc-update | libc@0.2.186 | Cargo.lock pins libc 0.2.186, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
