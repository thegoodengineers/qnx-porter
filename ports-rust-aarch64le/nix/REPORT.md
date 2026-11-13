# nix 0.31.3 on QNX 8.0 (aarch64le)

| | |
|---|---|
| Crate | [nix 0.31.3](https://crates.io/crates/nix/0.31.3) |
| Rust target | `aarch64-unknown-qnx` (Tier 3; `std` built with `-Zbuild-std`, linked with qcc) |
| Build | **failed** |
| Crate's own tests | not run |
| Test binaries | 0 |
| Rounds | 5 |
| Patches | 7 |
| Time | 0.4 min |

## Every change, with its reason
| # | Rule | Dependency | Reason |
|---|---|---|---|
| [0001](patches/0001-nto-to-qnx-getrandom-0.3.4.patch) | nto-to-qnx | getrandom@0.3.4 | getrandom 0.3.4 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0002](patches/0002-nto-to-qnx-getrandom-0.4.1.patch) | nto-to-qnx | getrandom@0.4.1 | getrandom 0.4.1 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0003](patches/0003-libc-update-libc-0.2.186.patch) | libc-update | libc@0.2.186 | Cargo.lock pins libc 0.2.186, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0004](patches/0004-nto-to-qnx-rustix-1.1.4.patch) | nto-to-qnx | rustix@1.1.4 | rustix 1.1.4 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0005](patches/0005-libc-update-libc-0.2.191.patch) | libc-update | libc@0.2.191 | Cargo.lock pins libc 0.2.191, which does not build for QNX 8.0; newer libc releases in the same semver range do, so update it there. |
| [0006](patches/0006-nto-to-qnx-getrandom-0.4.3.patch) | nto-to-qnx | getrandom@0.4.3 | getrandom 0.4.3 supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |
| [0007](patches/0007-nto-to-qnx-nix-0.31.3.patch) | nto-to-qnx | nix-0.31.3 | The crate supports QNX 7 (`target_os = "nto"`) but not QNX 8.0 (`target_os = "qnx"`); let QNX 8.0 take the QNX 7 code path. |

## First errors
- `error[E0432]: unresolved import `self::consts``
- `error[E0432]: unresolved import `self::Errno``
- `error[E0432]: unresolved import `crate::errno::Errno``

Build logs: `logs/build-NN.log`. Test output: `logs/tests.log`. Doc tests are not run.
