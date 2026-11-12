# Rust on QNX 8.0: the feasibility gate for crate porting

Before building a Rust crate porter, we checked that Rust programs that use the standard library build for
QNX 8.0 and run there. This is that check, run on 12 Nov 2026. Its output is in this folder.

## What the Rust project says
The rustc book's [QNX platform page](https://doc.rust-lang.org/nightly/rustc/platform-support/nto-qnx.html)
lists two targets for QNX SDP 8.0: `x86_64-pc-qnx` and `aarch64-unknown-qnx`. Both are **Tier 3**: Rust ships
no prebuilt standard library for them, so it has to be built with `-Zbuild-std`. The page marks "full support"
(the whole standard library) for these targets as "?", meaning in progress, and `no_std` as supported. For
SDP 8.0, `target_os` is `"qnx"`; the older `*-nto-qnx7xx` targets use `"nto"`. `qcc` from the SDP is the
linker.

So the gate asks a narrower question than "does all of std work": **do the parts of std that ported crates
lean on work on QNX 8.0?**

## What we ran
- Toolchain: `rustc 1.102.0-nightly (3ef0c22cd 2026-11-11)`, with the `rust-src` component. QNX SDP 8.0
  (build 141) with `qnxsdp-env.sh` sourced, so `qcc` is on PATH.
- Build: `cargo +nightly build --release -Zbuild-std --target <target>` in [`rust/gate/`](../../rust/gate/).
  This builds `core`, `alloc` and `std` from source for the target, and the target spec links with `qcc`
  (`-Vgcc_ntox86_64_cxx` / `-Vgcc_ntoaarch64le_cxx`). It took 2 min 10 s (x86_64) and 1 min 44 s (aarch64)
  on a laptop.
- The binaries need `libc.so.6`, `libsocket.so.4` and `libgcc_s.so.1`, all present on a stock QNX 8.0 image.
- Two programs:
  - `hello` prints `std::env::consts::OS`.
  - `stdcheck` makes 12 checks: threads with a mutex, an mpsc channel, file
    write/read/metadata/remove, `create_dir_all`/`read_dir`/`remove_dir_all`, `Instant` with `sleep`,
    `SystemTime`, a TCP loopback echo, a UDP loopback, `process::Command` running `uname -s`, environment
    variables, `available_parallelism`, and catching a panic by unwinding.

## Result
| target | QNX 8.0 target | `hello` | `stdcheck` | output |
|---|---|---|---|---|
| `x86_64-pc-qnx` | x86_64 QEMU (KVM) | `hello from Rust on qnx`, exit 0 | 12/12, exit 0 | [gate-x86_64.txt](gate-x86_64.txt) |
| `aarch64-unknown-qnx` | aarch64 QEMU `virt` (emulated) | `hello from Rust on qnx`, exit 0 | 12/12, exit 0 | [gate-aarch64le.txt](gate-aarch64le.txt) |

The `thread 'main' panicked ... unwind` lines in the output come from the deliberate panic in the last check,
which the program catches.

## What this does not show
- That every part of std works. We checked 12 areas, not std's own test suite.
- Anything about real aarch64 hardware. Both runs are QEMU.
- Anything about crates with C dependencies or `build.rs` scripts. That is the crate porter's job, and its
  results will be reported separately.
