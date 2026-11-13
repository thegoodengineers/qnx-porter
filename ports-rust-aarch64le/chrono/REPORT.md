# chrono 0.4.45 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Crate | [chrono 0.4.45](https://crates.io/crates/chrono/0.4.45) |
| Rust target | `aarch64-unknown-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 281/290 passed (0 ignored) on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Test binaries | 4 |
| Rounds | 2 |
| Patches | 1 |
| Time | 0.6 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-libc-update-libc-0.2.180.patch) | libc-update | libc@0.2.180 | Cargo.lock pins libc 0.2.180, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
