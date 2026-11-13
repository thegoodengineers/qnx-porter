# memchr 2.8.3 on QNX 8.0 (x86_64)

| | |
|---|---|
| Crate | [memchr 2.8.3](https://crates.io/crates/memchr/2.8.3) |
| Rust target | `x86_64-pc-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | 142/142 passed (0 ignored) on `QNX qnx-porter 8.0.0 2026/06/05-16:26:03EDT x86pc x86_64` |
| Test binaries | 1 |
| Rounds | 3 |
| Patches | 2 |
| Time | 0.6 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-libc-update-libc-0.2.176.patch) | libc-update | libc@0.2.176 | Cargo.lock pins libc 0.2.176, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0002](patches/0002-nto-to-qnx-getrandom-0.2.16.patch) | nto-to-qnx | getrandom@0.2.16 | getrandom 0.2.16 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
