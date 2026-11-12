"""Detect a library's build system and run its configure, build and test steps for QNX."""
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from . import qnx

JOBS = str(os.cpu_count() or 2)


def detect(src: Path) -> str:
    """cmake > meson > autotools > make. Projects that ship several usually treat CMake as the main one."""
    has = lambda *names: any((src / n).is_file() for n in names)  # noqa: E731
    if has("CMakeLists.txt"):
        return "cmake"
    if has("meson.build"):
        return "meson"
    if has("configure", "configure.ac", "configure.in"):
        return "autotools"
    if has("Makefile", "makefile", "GNUmakefile"):
        return "make"
    return "unknown"


@dataclass
class Job:
    src: Path
    build: Path
    system: str
    arch: qnx.Arch | None  # None = host compiler, used by the tests that run without QNX
    env: dict
    flags: qnx.Flags
    emulator: str = ""  # script that runs a target binary on the QNX target
    extra_args: tuple[str, ...] = ()

    def toolchain_text(self) -> str:
        """The generated file whose diffs are recorded when the agent changes a build flag."""
        if self.arch is None:
            return "\n".join(["# host build", *self.flags.cflags, *self.flags.link(), *self.flags.libs]) + "\n"
        if self.system == "meson":
            return qnx.meson_cross(self.arch, self.env, self.flags, "")  # tests run via meson_on_target()
        if self.system == "cmake":
            return qnx.cmake_toolchain(self.arch, self.env, self.flags)
        return "".join(f"{k}={v}\n" for k, v in qnx.gnu_env(self.arch, self.env, self.flags).items())

    def toolchain_path(self) -> Path:
        return self.build.parent / {"cmake": "qnx-toolchain.cmake", "meson": "qnx-cross.ini"}.get(
            self.system, "qnx-env.sh")

    def steps(self, tests: bool) -> list[list[str]]:
        self.build.mkdir(parents=True, exist_ok=True)
        tc = str(self.toolchain_path())
        b, s = str(self.build), str(self.src)
        if self.system == "cmake":
            cfg = ["cmake", "-S", s, "-B", b, "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF",
                   f"-DBUILD_TESTING={'ON' if tests else 'OFF'}"]
            if self.arch:
                cfg.append(f"-DCMAKE_TOOLCHAIN_FILE={tc}")
            else:
                cfg += [f"-DCMAKE_C_FLAGS={' '.join(self.flags.cflags)}",
                        f"-DCMAKE_EXE_LINKER_FLAGS={' '.join(self.flags.link() + self.flags.libs)}"]
            if self.emulator:
                cfg.append(f"-DCMAKE_CROSSCOMPILING_EMULATOR={self.emulator}")
            return [cfg + list(self.extra_args), ["cmake", "--build", b, "-j", JOBS, "--", "-k"]]
        if self.system == "meson":
            wipe = ["--wipe"] if (self.build / "meson-private").exists() else []  # flags may have changed
            cfg = ["meson", "setup", *wipe, b, s, "--default-library=static"]
            if self.arch:
                cfg.append(f"--cross-file={tc}")
            return [cfg + list(self.extra_args), ["meson", "compile", "-C", b]]
        if self.system == "autotools":
            pre = [] if (self.src / "configure").is_file() else [["autoreconf", "-fi", s]]
            host = [f"--host={self.arch.triplet}"] if self.arch else []
            env_args = [f"{k}={v}" for k, v in self.compiler_env().items()]
            return pre + [["env", "-C", b, f"{s}/configure", *host, "--disable-shared", *env_args,
                           *self.extra_args],
                          ["make", "-k", "-j", JOBS, "-C", b]]
        if self.system == "make":
            return [["make", "-k", "-j", JOBS, "-C", s, *[f"{k}={v}" for k, v in self.compiler_env().items()
                                                          if k in ("CC", "CXX", "AR")], *self.extra_args]]
        raise ValueError(f"no build system found in {self.src}")

    def compiler_env(self) -> dict:
        if self.arch:
            return qnx.gnu_env(self.arch, self.env, self.flags)
        return {"CFLAGS": " ".join(["-O2"] + self.flags.cflags), "LDFLAGS": " ".join(self.flags.link()),
                "LIBS": " ".join(self.flags.libs)}

    def test_cmd(self) -> list[str]:
        b = str(self.build)
        return {"cmake": ["ctest", "--test-dir", b, "--output-on-failure", "--timeout", "300"],
                "meson": ["meson", "test", "-C", b, "--print-errorlogs", "-t", "5"],
                "autotools": ["make", "-k", "-C", b, "check",
                              *([f"LOG_COMPILER={self.emulator}", f"SH_LOG_COMPILER={self.emulator}"]
                                if self.emulator else [])]}.get(self.system, [])

    def pretest_cmd(self) -> list[str]:
        """automake builds check_PROGRAMS only during `make check`; TESTS= builds them without running."""
        return ["make", "-k", "-j", JOBS, "-C", str(self.build), "check", "TESTS="] \
            if self.system == "autotools" else []


def run(cmds: list[list[str]], cwd: Path, env: dict, log_path: Path) -> tuple[bool, str]:
    """Run commands in order, stopping at the first failure. Output goes to log_path and is returned."""
    env = {**env, "LC_ALL": "C", "LANG": "C"}
    text = []
    ok = True
    for cmd in cmds:
        text.append("$ " + " ".join(cmd) + "\n")
        r = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, errors="replace")
        text.append(r.stdout + r.stderr)
        if r.returncode != 0:
            text.append(f"[exit {r.returncode}]\n")
            ok = False
            break
    out = "".join(text)
    log_path.write_text(out, encoding="utf-8")
    return ok, out
