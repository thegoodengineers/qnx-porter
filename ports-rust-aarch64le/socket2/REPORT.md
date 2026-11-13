# socket2 0.6.5 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Crate | [socket2 0.6.5](https://crates.io/crates/socket2/0.6.5) |
| Rust target | `aarch64-unknown-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 10/10 passed (0 ignored) on `QNX qnx-porter-aarch64le 8.0.0 2026/06/05-16:21:14EDT QEMU_virt aarch64le` |
| Test binaries | 1 |
| Rounds | 2 |
| Patches | 1 |
| Time | 0.2 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-libc-update-libc-0.2.172.patch) | libc-update | libc@0.2.172 | Cargo.lock pins libc 0.2.172, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
