"""QNX SDP 8.0: find the SDP, and write the toolchain files each build system needs.

qcc/q++ select their GCC back end with -V<target> (CMake passes CMAKE_<LANG>_COMPILER_TARGET as that),
and the SDP also ships plain GNU-style drivers named <triplet>-gcc, which autotools and meson prefer.
"""
import os
import re
import shlex
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Arch:
    name: str  # QNX's name for the CPU variant
    qcc_target: str  # value for qcc -V
    triplet: str  # GNU triplet; the SDP's <triplet>-gcc driver
    cpu: str  # CMAKE_SYSTEM_PROCESSOR / meson cpu


ARCHES = {
    "x86_64": Arch("x86_64", "gcc_ntox86_64", "x86_64-pc-nto-qnx8.0.0", "x86_64"),
    "aarch64le": Arch("aarch64le", "gcc_ntoaarch64le", "aarch64-unknown-nto-qnx8.0.0", "aarch64"),
}


@dataclass
class Flags:
    """Build-flag changes the agent makes. Each one is logged with its reason, like a source patch."""
    cflags: list[str] = field(default_factory=list)
    ldflags: list[str] = field(default_factory=list)
    libs: list[str] = field(default_factory=list)
    stub_dir: str = ""  # holds empty archives for libraries whose contents live in QNX's libc

    def link(self) -> list[str]:
        return ([f"-L{self.stub_dir}"] if self.stub_dir else []) + self.ldflags


def sdp_env(environ=None) -> dict:
    """The environment with QNX_HOST/QNX_TARGET set, sourcing qnxsdp-env.sh from ~/qnx800 if needed."""
    env = dict(os.environ if environ is None else environ)
    if env.get("QNX_HOST") and env.get("QNX_TARGET"):
        return env
    for base in [env.get("QNX_SDP", ""), str(Path.home() / "qnx800"), "/opt/qnx800"]:
        script = Path(base) / "qnxsdp-env.sh"
        if base and script.is_file():
            out = subprocess.run(["bash", "-c", f"source {shlex.quote(str(script))} >/dev/null && env -0"],
                                 capture_output=True, check=True).stdout.decode()
            env.update(kv.split("=", 1) for kv in out.split("\0") if "=" in kv)
            return env
    raise SystemExit("QNX SDP 8.0 not found: source qnxsdp-env.sh, or set QNX_SDP to the folder that holds it "
                     "(default ~/qnx800). See SETUP.md.")


def doctor(env: dict) -> list[tuple[str, bool, str]]:
    """Checks for `qnx-porter doctor`: (what, ok, detail)."""
    host, target = env.get("QNX_HOST", ""), env.get("QNX_TARGET", "")
    checks = [("QNX_HOST", Path(host).is_dir(), host), ("QNX_TARGET", Path(target).is_dir(), target)]
    qcc = Path(host) / "usr" / "bin" / "qcc"
    checks.append(("qcc", qcc.exists(), str(qcc)))
    if qcc.exists():
        r = subprocess.run([str(qcc), "-V"], capture_output=True, text=True, env=env)
        checks.append(("qcc targets", "gcc_ntox86_64" in (r.stdout + r.stderr), (r.stdout + r.stderr).strip()[:300]))
    for a in ARCHES.values():
        gcc = Path(gnu_tool(env, a.triplet, "gcc"))
        checks.append((f"{a.name} gcc", gcc.exists(), str(gcc)))
    bad = sdp_damage(env)
    checks.append(("SDP complete", not bad, "no empty compiler or libc files" if not bad else
                   f"{len(bad)} key files are empty or missing, e.g. {bad[0]}: the install did not finish. "
                   "Repair it in the QNX Software Center (SETUP.md step 3)."))
    if qcc.exists() and not bad:
        ok, out = compiles(env)
        checks.append(("qcc builds hello", ok, out))
    for tool_name in ("cmake", "make", "git", "ssh", "tar"):
        p = subprocess.run(["bash", "-c", f"command -v {tool_name}"], capture_output=True, text=True).stdout.strip()
        checks.append((tool_name, bool(p), p or "not on PATH"))
    return checks


def tool(env: dict, name: str) -> str:
    return f"{env['QNX_HOST'].rstrip('/')}/usr/bin/{name}"


def gnu_tool(env: dict, triplet: str, name: str) -> str:
    """The SDP's GNU-style driver. SDP 8.0 ships gcc/g++ only with a version suffix
    (x86_64-pc-nto-qnx8.0.0-gcc-12.2.0) and binutils without one, so prefer the plain name, else the
    newest versioned one."""
    plain = Path(tool(env, f"{triplet}-{name}"))
    if plain.exists():
        return plain.as_posix()
    versioned = sorted(plain.parent.glob(f"{triplet}-{name}-[0-9]*"),
                       key=lambda p: [int(x) for x in re.findall(r"\d+", p.name.rsplit("-", 1)[-1])])
    return (versioned[-1] if versioned else plain).as_posix()


def sdp_damage(env: dict) -> list[str]:
    """Key SDP files that are missing or 0 bytes. An interrupted Software Center install leaves
    placeholder files of size 0, and qcc then fails with "cc1: Exec format error"."""
    host, target = Path(env.get("QNX_HOST", "")), Path(env.get("QNX_TARGET", ""))
    bad = [str(p) for p in sorted(host.glob("usr/lib/gcc/*/*/cc1*")) if p.stat().st_size == 0]
    for arch in ("x86_64", "aarch64le"):
        for lib in ("libc.so", "libsocket.so"):
            found = [p for p in (target / arch / "lib" / lib, target / arch / "usr" / "lib" / lib) if p.exists()]
            if not found or all(p.stat().st_size == 0 for p in found):
                bad.append(str(target / arch / "lib" / lib))
    return bad


def compiles(env: dict) -> tuple[bool, str]:
    """Compile and link a socket program with qcc: the end-to-end check that the SDP really works."""
    with tempfile.TemporaryDirectory() as d:
        c = Path(d) / "hello.c"
        c.write_text("#include <stdio.h>\n#include <sys/socket.h>\n"
                     "int main(void) { return socket(AF_INET, SOCK_STREAM, 0) < 0; }\n")
        r = subprocess.run([tool(env, "qcc"), "-Vgcc_ntox86_64", str(c), "-o", str(Path(d) / "hello"),
                            "-lsocket"], capture_output=True, text=True, env=env)
        return r.returncode == 0, (r.stdout + r.stderr).strip()[:300] or "ok"


def cmake_toolchain(arch: Arch, env: dict, flags: Flags) -> str:
    c, ld, libs = " ".join(flags.cflags), " ".join(flags.link()), " ".join(flags.libs)
    return f"""# Generated by qnx-porter for QNX SDP 8.0, {arch.name}.
set(CMAKE_SYSTEM_NAME QNX)
set(CMAKE_SYSTEM_VERSION 8.0.0)
set(CMAKE_SYSTEM_PROCESSOR {arch.cpu})
set(CMAKE_C_COMPILER "{tool(env, 'qcc')}")
set(CMAKE_C_COMPILER_TARGET {arch.qcc_target})
set(CMAKE_CXX_COMPILER "{tool(env, 'q++')}")
set(CMAKE_CXX_COMPILER_TARGET {arch.qcc_target}_cxx)
set(CMAKE_SYSROOT "{env['QNX_TARGET']}")
set(CMAKE_FIND_ROOT_PATH "{env['QNX_TARGET']}" "{env['QNX_TARGET']}/{arch.name}")
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
# -g: debug info only (same code), so a crash on the target gives file:line in its backtrace
set(CMAKE_C_FLAGS_INIT "-g {c}")
set(CMAKE_CXX_FLAGS_INIT "-g {c}")
set(CMAKE_EXE_LINKER_FLAGS_INIT "{ld}")
set(CMAKE_SHARED_LINKER_FLAGS_INIT "{ld}")
# Libraries the agent adds go at the end of every link line, after the objects that need them.
set(CMAKE_C_STANDARD_LIBRARIES "{libs}")
set(CMAKE_CXX_STANDARD_LIBRARIES "{libs}")
"""


def meson_cross(arch: Arch, env: dict, flags: Flags, emulator: str) -> str:
    q = lambda xs: "[" + ", ".join(repr(x) for x in xs) + "]"  # noqa: E731
    wrapper = f"exe_wrapper = {q([emulator])}\n" if emulator else ""
    return f"""# Generated by qnx-porter for QNX SDP 8.0, {arch.name}.
[binaries]
c = '{gnu_tool(env, arch.triplet, "gcc")}'
cpp = '{gnu_tool(env, arch.triplet, "g++")}'
ar = '{gnu_tool(env, arch.triplet, "ar")}'
strip = '{gnu_tool(env, arch.triplet, "strip")}'
{wrapper}
[built-in options]
c_args = {q(['-g'] + flags.cflags)}
cpp_args = {q(['-g'] + flags.cflags)}
c_link_args = {q(flags.link() + flags.libs)}
cpp_link_args = {q(flags.link() + flags.libs)}

[host_machine]
system = 'qnx'
cpu_family = '{arch.cpu}'
cpu = '{arch.cpu}'
endian = 'little'
"""


def gnu_env(arch: Arch, env: dict, flags: Flags) -> dict:
    """CC/CXX/... for autotools configure and plain Makefiles."""
    return {
        "CC": gnu_tool(env, arch.triplet, "gcc"),
        "CXX": gnu_tool(env, arch.triplet, "g++"),
        "AR": gnu_tool(env, arch.triplet, "ar"),
        "RANLIB": gnu_tool(env, arch.triplet, "ranlib"),
        "CFLAGS": " ".join(["-O2", "-g"] + flags.cflags),
        "CXXFLAGS": " ".join(["-O2", "-g"] + flags.cflags),
        "LDFLAGS": " ".join(flags.link()),
        "LIBS": " ".join(flags.libs),
    }
