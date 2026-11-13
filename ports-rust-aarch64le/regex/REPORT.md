# regex 1.13.1 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Crate | [regex 1.13.1](https://crates.io/crates/regex/1.13.1) |
| Rust target | `aarch64-unknown-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **built** |
| Crate's own tests | not run |
| Test binaries | 0 |
| Rounds | 3 |
| Patches | 2 |
| Time | 0.2 min |
| Note | library only: the published crate does not include the files its tests read |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-libc-update-libc-0.2.177.patch) | libc-update | libc@0.2.177 | Cargo.lock pins libc 0.2.177, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0002](patches/0002-nto-to-qnx-getrandom-0.2.16.patch) | nto-to-qnx | getrandom@0.2.16 | getrandom 0.2.16 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
