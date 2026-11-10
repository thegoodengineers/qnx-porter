from pathlib import Path

from qnx_porter import qnx
from qnx_porter.build import Job, detect

ENV = {"QNX_HOST": "/q/host/linux/x86_64", "QNX_TARGET": "/q/target/qnx"}


def tree(tmp_path, *names):
    for n in names:
        (tmp_path / n).write_text("")
    return tmp_path


def test_detect_prefers_cmake_then_meson_then_autotools_then_make(tmp_path):
    assert detect(tree(tmp_path, "Makefile")) == "make"
    assert detect(tree(tmp_path, "configure.ac")) == "autotools"
    assert detect(tree(tmp_path, "meson.build")) == "meson"
    assert detect(tree(tmp_path, "CMakeLists.txt")) == "cmake"


def test_detect_unknown(tmp_path):
    assert detect(tmp_path) == "unknown"


def test_cmake_toolchain_uses_qcc_targets_and_sysroot():
    f = qnx.Flags(cflags=["-D_QNX_SOURCE"], libs=["-lsocket"], stub_dir="/w/stubs")
    t = qnx.cmake_toolchain(qnx.ARCHES["x86_64"], ENV, f)
    assert "set(CMAKE_SYSTEM_NAME QNX)" in t
    assert 'CMAKE_C_COMPILER "/q/host/linux/x86_64/usr/bin/qcc"' in t
    assert "CMAKE_C_COMPILER_TARGET gcc_ntox86_64)" in t
    assert "CMAKE_CXX_COMPILER_TARGET gcc_ntox86_64_cxx" in t
    assert 'CMAKE_SYSROOT "/q/target/qnx"' in t
    assert 'CMAKE_C_FLAGS_INIT "-D_QNX_SOURCE"' in t
    assert 'CMAKE_EXE_LINKER_FLAGS_INIT "-L/w/stubs -lsocket"' in t


def test_aarch64_and_meson_cross_file():
    t = qnx.meson_cross(qnx.ARCHES["aarch64le"], ENV, qnx.Flags(), "/w/qnx-run")
    assert "aarch64-unknown-nto-qnx8.0.0-gcc" in t and "system = 'qnx'" in t
    assert "exe_wrapper = ['/w/qnx-run']" in t


def test_autotools_steps_cross_compile_with_host_triplet(tmp_path):
    (tmp_path / "configure").write_text("")
    job = Job(tmp_path, tmp_path / "b", "autotools", qnx.ARCHES["x86_64"], ENV, qnx.Flags())
    cfg = job.steps(tests=True)[0]
    assert "--host=x86_64-pc-nto-qnx8.0.0" in cfg and "--disable-shared" in cfg
    assert "CC=/q/host/linux/x86_64/usr/bin/x86_64-pc-nto-qnx8.0.0-gcc" in cfg


def test_autoreconf_runs_when_only_configure_ac_exists(tmp_path):
    (tmp_path / "configure.ac").write_text("")
    job = Job(tmp_path, tmp_path / "b", "autotools", qnx.ARCHES["x86_64"], ENV, qnx.Flags())
    assert job.steps(tests=True)[0][0] == "autoreconf"


def test_cmake_steps_pass_toolchain_and_emulator(tmp_path):
    job = Job(tmp_path, tmp_path / "b", "cmake", qnx.ARCHES["x86_64"], ENV, qnx.Flags(), emulator="/w/qnx-run")
    cfg = job.steps(tests=True)[0]
    assert f"-DCMAKE_TOOLCHAIN_FILE={tmp_path / 'qnx-toolchain.cmake'}" in cfg
    assert "-DCMAKE_CROSSCOMPILING_EMULATOR=/w/qnx-run" in cfg and "-DBUILD_TESTING=ON" in cfg
    assert job.test_cmd()[0] == "ctest"


def test_sdp_env_uses_existing_variables():
    assert qnx.sdp_env(ENV)["QNX_HOST"] == ENV["QNX_HOST"]


def test_sdp_env_explains_what_to_do_when_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    try:
        qnx.sdp_env({"QNX_SDP": str(tmp_path / "nope")})
    except SystemExit as e:
        assert "SETUP.md" in str(e)
    else:
        raise AssertionError("expected SystemExit")
