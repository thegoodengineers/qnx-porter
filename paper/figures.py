"""The paper's figures, drawn from the result files only: paper/fig/*.pdf (for LaTeX) and *.png (for paper.md).

    python3 paper/figures.py      # needs matplotlib (python3 -m pip install --user matplotlib)

Inputs: results/ports.csv, ports*/*/report.json (patches by rule), results/crates*.csv, results/rt.csv.
The pipeline diagram is the one figure that is not data; its boxes name the source files that do each step.
"""
import csv
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / "fig"
ARCH = {"x86_64": "x86_64 (QEMU, KVM)", "aarch64le": "aarch64 on QEMU virt"}
PORT_DIRS = {"x86_64": "ports", "aarch64le": "ports-aarch64le"}
# Categorical slots 1-3 of a palette validated for colour-vision deficiency; text stays in ink colours.
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 8.5, "axes.labelsize": 8,
    "axes.edgecolor": INK2, "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 7.5,
    "pdf.fonttype": 42, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


def read_csv(rel):
    with (ROOT / rel).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{name}.pdf")
    fig.savefig(OUT / f"{name}.png", dpi=200)
    plt.close(fig)
    print(f"paper/fig/{name}.pdf, .png")


def grid(ax, axis="x"):
    ax.grid(axis=axis, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)


def tests_per_library(ports):
    """Share of each library's own tests that passed, per architecture; label = passed/total."""
    by = {}
    for r in ports:
        if r["tests_total"] not in ("", "0"):
            by.setdefault(r["library"], {})[r["arch"]] = (int(r["tests_passed"]), int(r["tests_total"]))
    libs = sorted(by, key=lambda k: (min(p / t for p, t in by[k].values()), k.lower()), reverse=True)
    fig, ax = plt.subplots(figsize=(7.0, 0.15 * len(libs) + 0.7))
    h = 0.38
    for i, (arch, col) in enumerate((("x86_64", C1), ("aarch64le", C2))):
        ys = [k + (i - 0.5) * h for k in range(len(libs))]
        vals = [by[lib][arch][0] / by[lib][arch][1] if arch in by[lib] else 0 for lib in libs]
        ax.barh(ys, vals, height=h * 0.9, color=col, label=ARCH[arch], edgecolor="white", linewidth=0.5)
    for k, lib in enumerate(libs):  # one label per library: passed/total, x86_64 first when they differ
        v = [f"{p}/{t}" for p, t in (by[lib].get(a) for a in ("x86_64", "aarch64le")) if t]
        ax.text(1.01, k, v[0] if len(set(v)) == 1 else " | ".join(v), va="center", fontsize=6, color=INK2)
    ax.set_yticks(range(len(libs)), libs, fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.16)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0], ["0%", "25%", "50%", "75%", "100%"])
    ax.set_xlabel("share of the library's own tests that passed on the QNX 8.0 target")
    grid(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2)
    save(fig, "tests-per-library")


OUTCOMES = [("all of its own tests passed", C3), ("some of its tests failed", C2),
            ("built; build registers no tests", "#a3a29c"), ("built; tests not run on the target", "#cfcec9"),
            ("did not build", INK)]


def outcome(r):
    if r["build_result"] != "built":
        return OUTCOMES[4][0]
    if r["tests_total"] == "":
        return OUTCOMES[3][0]
    if r["tests_total"] == "0":
        return OUTCOMES[2][0]
    return OUTCOMES[0][0] if r["tests_passed"] == r["tests_total"] else OUTCOMES[1][0]


def outcomes(ports):
    fig, ax = plt.subplots(figsize=(3.4, 1.55))
    arches = ["x86_64", "aarch64le"]
    for y, arch in enumerate(arches):
        rs = [r for r in ports if r["arch"] == arch]
        left = 0
        for name, col in OUTCOMES:
            n = sum(outcome(r) == name for r in rs)
            if n:
                ax.barh(y, n, left=left, color=col, edgecolor="white", linewidth=1.5, height=0.6,
                        label=name if y == 0 else None)
                ax.text(left + n / 2, y, str(n), ha="center", va="center", fontsize=7,
                        color="white" if col in (INK, C1, C2, C3) else INK)
                left += n
    ax.set_yticks(range(2), [ARCH[a] for a in arches], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("libraries")
    ax.legend(loc="upper center", bbox_to_anchor=(0.4, -0.42), ncol=2, fontsize=6.5, handlelength=1)
    save(fig, "outcomes")


def rules():
    counts = {}
    for arch, d in PORT_DIRS.items():
        for f in sorted((ROOT / d).glob("*/report.json")):
            for p in json.loads(f.read_text(encoding="utf-8"))["patches"]:
                if p["kept"]:
                    counts.setdefault(p["rule"], {}).setdefault(arch, 0)
                    counts[p["rule"]][arch] += 1
    names = sorted(counts, key=lambda k: (-sum(counts[k].values()), k))
    fig, ax = plt.subplots(figsize=(3.4, 0.2 * len(names) + 0.6))
    h = 0.4
    for i, (arch, col) in enumerate((("x86_64", C1), ("aarch64le", C2))):
        ys = [k + (i - 0.5) * h for k in range(len(names))]
        ax.barh(ys, [counts[n].get(arch, 0) for n in names], height=h * 0.9, color=col, label=ARCH[arch],
                edgecolor="white", linewidth=0.5)
    ax.set_yticks(range(len(names)), names, fontsize=6.5, family="DejaVu Sans Mono")
    ax.invert_yaxis()
    ax.xaxis.get_major_locator().set_params(integer=True)
    ax.set_xlabel("kept patches (one per change)")
    grid(ax)
    ax.legend(loc="lower right")
    save(fig, "rules")


def crates():
    rows = {a: {r["crate"]: r for r in read_csv(f)} for a, f in
            (("x86_64", "results/crates.csv"), ("aarch64le", "results/crates-aarch64le.csv"))}
    names = sorted(rows["x86_64"], key=str.lower)
    fig, ax = plt.subplots(figsize=(3.4, 0.17 * len(names) + 0.7))
    h = 0.4
    for i, (arch, col) in enumerate((("x86_64", C1), ("aarch64le", C2))):
        ys = [k + (i - 0.5) * h for k in range(len(names))]
        vals = [int(rows[arch][n]["tests_passed"]) if n in rows[arch] else 0 for n in names]
        ax.barh(ys, [max(v, 0) for v in vals], height=h * 0.9, color=col, label=ARCH[arch],
                edgecolor="white", linewidth=0.5)
    for k, n in enumerate(names):
        r = rows["x86_64"][n]
        if r["build_result"] != "built":
            tag = "did not build"
        elif int(r["tests_total"] or 0) == 0:
            tag = "built; no tests ran"
        else:
            v = [f"{rows[a][n]['tests_passed']}/{rows[a][n]['tests_total']}" for a in rows]
            tag = "" if all(rows[a][n]["tests_passed"] == rows[a][n]["tests_total"] for a in rows) else (
                v[0] if len(set(v)) == 1 else " | ".join(v))
        if tag:
            ax.text(1.02, k, tag, va="center", fontsize=5.8, color=INK2, transform=ax.get_yaxis_transform())
    ax.set_xscale("log")
    ax.set_xlim(1, 4000)
    ax.set_yticks(range(len(names)), names, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlabel("tests passed on QNX 8.0 (log scale)")
    grid(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=6.5)
    save(fig, "crates")


def realtime():
    rs = [r for r in read_csv("results/rt.csv") if not r["error"].strip() and r["loaded_p99_us"]]
    rs.sort(key=lambda r: float(r["loaded_p99_us"]))
    fig, ax = plt.subplots(figsize=(3.4, 0.27 * len(rs) + 0.7))
    h = 0.27
    for i, (key, label, col) in enumerate((("idle_p99_us", "idle", C1), ("loaded_p99_us", "under load", C2),
                                          ("loaded_isolated_p99_us", "under load, runmask-isolated", C3))):
        ys = [k + (i - 1) * h for k in range(len(rs))]
        ax.barh(ys, [float(r[key]) for r in rs], height=h * 0.9, color=col, label=label,
                edgecolor="white", linewidth=0.4)
    ax.set_xscale("log")
    ax.set_yticks(range(len(rs)), [r["library"] for r in rs], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlabel("p99 latency of one call, microseconds (log scale)")
    grid(ax)
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, fontsize=6.5)
    save(fig, "rt-p99")


def pipeline():
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    ax.set_xlim(0, 100)
    ax.set_ylim(-0.5, 45.5)
    ax.axis("off")

    def box(x, y, w, h, title, sub, col=C1):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.2,rounding_size=1.0",
                                    facecolor="white", edgecolor=col, linewidth=1.0))
        ax.text(x + w / 2, y + h - 1.4, title, ha="center", va="top", fontsize=6.4, color=INK, weight="bold")
        ax.text(x + w / 2, y + h - 4.3, sub, ha="center", va="top", fontsize=5.2, color=INK2, linespacing=1.3)

    def arrow(a, b, text="", rad=0.0, tx=0.0, ty=0.0):
        ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color=INK2, lw=0.8, shrinkA=0,
                                                        shrinkB=0, connectionstyle=f"arc3,rad={rad}"))
        if text:
            ax.text((a[0] + b[0]) / 2 + tx, (a[1] + b[1]) / 2 + ty, text, fontsize=5.2, color=INK2,
                    ha="center", va="center", style="italic")

    top, mid, bot = 33, 17, 0
    box(0, top, 20, 12, "Fetch and detect", "shallow clone at the tag;\nCMake, Meson, autotools\nor Make\nagent.py, build.py")
    box(25, top, 20, 12, "QNX toolchain, build", "qcc -V<arch>, SDP sysroot,\nflags the rules added;\nconfigure + build\nqnx.py, build.py")
    box(50, top, 18, 12, "Parse errors", "GCC, ld, CMake,\nconfigure, Meson\nerrors.py")
    box(73, top, 27, 12, "Rule from a QNX fact", "a documented QNX 8.0 fact;\nnumbered patch with rule,\nreason and error\nfixes.py, linuxisms.py", C3)
    box(73, mid, 27, 11.5, "Language model (optional)", "only when no rule fits;\nunified diff + one-line reason;\ngit apply --check\nllm.py", C2)
    box(40, mid, 28, 11.5, "Rebuild on probation", "a model patch, or a rule that\nneeds proof, is reverted unless\nits error is gone\nagent.py, patches.py", C2)
    box(0, bot, 21, 13, "Sync to QNX target", "tar over ssh into /data;\nln -sP path-space link\nputs trees at host paths\ntarget.py")
    box(26, bot, 24, 13, "Run the library's own tests", "ctest, meson test, make check:\neach command on QNX under\ntimeout -s KILL; on -u (run_as);\nTAP subtests counted")
    box(55, bot, 21, 13, "Crash triage", "core from dumper, SDP gdb\nbacktrace; printf-null\npatch kept only if more\ntests pass; crash.py", C2)
    box(81, bot, 19, 13, "Port folder", "REPORT.md, report.json,\npatches/, qnx.patch,\ntoolchain, logs, SBOM")

    y = top + 6
    arrow((20.2, y), (24.8, y))
    arrow((45.2, y), (49.8, y), "errors", ty=1.8)
    arrow((68.2, y), (72.8, y))
    arrow((86.5, top - 0.2), (86.5, mid + 11.7), "no rule", tx=4.0)
    arrow((72.8, mid + 5.75), (68.2, mid + 5.75))
    arrow((54, mid + 11.7), (40, top - 0.2), "rebuild", tx=-5.5, ty=-0.8)
    arrow((30, top - 0.2), (12, bot + 13.2), "build OK", tx=-4.5)
    arrow((21.2, bot + 6.5), (25.8, bot + 6.5))
    arrow((50.2, bot + 4), (54.8, bot + 4), "core", ty=-1.8)
    arrow((60, bot + 13.2), (44, bot + 13.2), "re-run", rad=0.45, ty=1.3)
    arrow((76.2, bot + 6.5), (80.8, bot + 6.5))
    save(fig, "pipeline")


def main():
    ports = read_csv("results/ports.csv")
    pipeline()
    tests_per_library(ports)
    outcomes(ports)
    rules()
    crates()
    realtime()


if __name__ == "__main__":
    main()
