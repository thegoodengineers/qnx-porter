"""Rust crate porting: rules from real `cargo test --no-run --target x86_64-pc-qnx` output (12 Nov 2026)."""
from qnx_porter import crate

REG = "/home/u/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f"


def test_old_libc_in_cargo_lock_is_updated():
    err = (f"error[E0432]: unresolved import `unistd`\n   --> {REG}/libc-0.2.180/src/new/mod.rs:230:17\n"
           "error: could not compile `libc` (lib) due to 1 previous error\n")
    [f] = crate.plan(err, set())
    assert f["rule"] == "libc-update" and f["dep"] == "libc@0.2.180"


def test_dependency_that_knows_qnx7_but_not_qnx8_is_vendored_and_patched(tmp_path):
    dep = tmp_path / "registry/src/idx/getrandom-0.3.4"
    (dep / "src").mkdir(parents=True)
    (dep / "src/backends.rs").write_text('} else if #[cfg(any(\n    target_os = "haiku",\n    target_os = "nto",\n))] {\n')
    (dep / "Cargo.toml").write_text("[target.'cfg(any(target_os = \"nto\", target_os = \"aix\"))'.dependencies.libc]\n")
    err = ("error: target is not supported. You may need to define a custom backend\n"
           f"   --> {dep}/src/backends.rs:204:9\n")
    done = set()
    [f] = crate.plan(err, done)
    assert f["rule"] == "nto-to-qnx" and f["dep"] == "getrandom@0.3.4"
    assert crate.plan(err, done) == []  # never the same fix twice
    config = []
    out = tmp_path / "out"
    patch = crate.apply(f, tmp_path, {}, tmp_path / "work", out, 1, config)
    vendored = tmp_path / "work/vendor/getrandom-0.3.4"
    assert 'any(target_os = "nto", target_os = "qnx")' in (vendored / "src/backends.rs").read_text()
    assert 'any(target_os = "nto", target_os = "qnx")' in (vendored / "Cargo.toml").read_text()
    assert 'target_os = "nto",' in (dep / "src/backends.rs").read_text()  # the registry copy is untouched
    assert config == [f'patch.crates-io.getrandom_0_3_4.path="{vendored}"',
                      'patch.crates-io.getrandom_0_3_4.package="getrandom"']
    assert "+    any(target_os" in (out / patch).read_text()


def test_crate_that_already_knows_qnx8_is_left_alone(tmp_path):
    dep = tmp_path / "registry/src/idx/mio-1.2.4"
    (dep / "src").mkdir(parents=True)
    (dep / "src/lib.rs").write_text('#[cfg(target_os = "nto")]\nmod a;\n#[cfg(target_os = "qnx")]\nmod b;\n')
    assert crate.plan(f"error[E0425]: x\n  --> {dep}/src/lib.rs:1:1\n", set()) == []


def test_libtest_summaries_are_counted():
    out = ("test a ... ok\ntest result: ok. 12 passed; 0 failed; 3 ignored; 0 measured\n"
           "test result: FAILED. 4 passed; 2 failed; 0 ignored; 0 measured\n")
    assert [tuple(map(int, m)) for m in crate.LIBTEST.findall(out)] == [(12, 0, 3), (4, 2, 0)]


def test_link_error_names_the_dependency_through_its_rlib(tmp_path, monkeypatch):
    # errno 0.3.14 links __get_errno_ptr only for target_os = "nto"; QNX 8.0 fails at link time
    home = tmp_path / "cargo"
    dep = home / "registry/src/idx/errno-0.3.14"
    (dep / "src").mkdir(parents=True)
    (dep / "src/unix.rs").write_text('#[cfg_attr(target_os = "nto", link_name = "__get_errno_ptr")]\n')
    monkeypatch.setenv("CARGO_HOME", str(home))
    crate_dir = tmp_path / "crossbeam-channel-0.5.17"
    crate_dir.mkdir()
    (crate_dir / "Cargo.lock").write_text('[[package]]\nname = "errno"\nversion = "0.3.14"\n')
    err = ("  = note: ld: /t/release/build/errno/4b2a/out/liberrno-4b2a85f8f3fcdda8.rlib(errno-4b2a.cgu.0.rcgu.o): "
           "in function `errno::errno':\n          undefined reference to `errno_location'\n")
    [f] = crate.plan(err, set(), crate_dir)
    assert f["rule"] == "nto-to-qnx" and f["dep"] == "errno@0.3.14"
