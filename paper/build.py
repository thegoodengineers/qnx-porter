"""Every number in the paper, read from the repository's result files; and paper.md rendered from the .tex.

    python3 paper/build.py            # writes paper/numbers.tex and paper/paper.md
    tectonic paper/qnx-porter.tex     # then the PDF

The paper never types a number: qnx-porter.tex writes \\N{key}, and this script defines every key from
results/*.csv, ports*/*/report.json, results/runs/*.log and the generated docs. Re-run it after a campaign.
Standard library only, so it runs in CI next to the tests.
"""
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ARCHES = {"x": "x86_64", "a": "aarch64le"}
PORT_DIRS = {"x86_64": "ports", "aarch64le": "ports-aarch64le"}


def read_csv(rel: str) -> list[dict]:
    with (ROOT / rel).open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def find(pattern: str, rel: str, group=1, flags=0) -> str:
    m = re.search(pattern, text(rel), flags)
    if not m:
        raise SystemExit(f"build.py: {rel} no longer says /{pattern}/; update the pattern or the paper")
    return m.group(group)


def names(xs) -> str:
    xs = sorted(xs, key=str.lower)
    return "none" if not xs else xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def pct(a: int, b: int) -> str:
    return f"{100 * a / b:.1f}" if b else "0.0"


def campaign_tags(rel: str) -> dict:
    """name -> tag from a campaign YAML file (a regex, so the script needs no PyYAML)."""
    s = text(rel)  # block style (`- name: x` / `tag: y` lines) and flow style (`- {name: x, tag: y}`) both occur
    heads = list(re.finditer(r"\bname:\s*([^\s,}]+)", s))
    out = {}
    for m, nxt in zip(heads, heads[1:] + [None]):
        tag = re.search(r"\btag:\s*([^\s,}]+)", s[m.end():nxt.start() if nxt else len(s)])
        out[m[1]] = tag[1] if tag else ""
    return out


def rule_counts(arch: str) -> dict:
    """Kept patches per rule, from each port's report.json (printf-null-<file> folds into printf-null)."""
    out: dict[str, int] = {}
    for f in sorted((ROOT / PORT_DIRS[arch]).glob("*/report.json")):
        for p in json.loads(f.read_text(encoding="utf-8"))["patches"]:
            if p["kept"]:
                out[p["rule"]] = out.get(p["rule"], 0) + 1
    return out


def printf_null_libs(arch: str) -> list[str]:
    libs = []
    for f in sorted((ROOT / PORT_DIRS[arch]).glob("*/report.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if any(p["kept"] and p["rule"] == "printf-null" for p in r["patches"]):
            libs.append(r["library"])
    return libs


def campaign(n: dict) -> None:
    ports = read_csv("results/ports.csv")
    for p, arch in ARCHES.items():
        rs = [r for r in ports if r["arch"] == arch]
        built = [r for r in rs if r["build_result"] == "built"]
        tested = [r for r in built if r["tests_total"] not in ("", "0")]
        tp = sum(int(r["tests_passed"]) for r in tested)
        tt = sum(int(r["tests_total"]) for r in tested)
        failed = [r for r in rs if r["build_result"] != "built"]
        new = [r for r in rs if r["on_oss_qnx_com"] == "no"]
        n |= {
            f"{p}-libs": len(rs), f"{p}-built": len(built), f"{p}-failed": len(failed),
            f"{p}-tested-libs": len(tested), f"{p}-tests-passed": tp, f"{p}-tests-total": tt,
            f"{p}-tests-failed": tt - tp, f"{p}-pass-pct": pct(tp, tt),
            f"{p}-allpass-libs": sum(r["tests_passed"] == r["tests_total"] for r in tested),
            f"{p}-somefail-libs": sum(r["tests_passed"] != r["tests_total"] for r in tested),
            f"{p}-notests-libs": sum(r["tests_total"] == "0" for r in built),
            f"{p}-notrun-libs": sum(r["tests_total"] == "" for r in built),
            f"{p}-patches": sum(int(r["patches"]) for r in rs),
            f"{p}-rule-patches": sum(int(r["patches_by_rule"]) for r in rs),
            f"{p}-model-patches": sum(int(r["patches_by_model"]) for r in rs),
            f"{p}-patched-libs": sum(int(r["patches"]) > 0 for r in built),
            f"{p}-unpatched-libs": sum(int(r["patches"]) == 0 for r in built),
            f"{p}-failed-list": names(r["library"] + (f" ({r['note']})" if r["note"] else "") for r in failed),
            f"{p}-hours": f"{sum(float(r['minutes']) for r in rs) / 60:.1f}",
            f"{p}-first-day": min(r["finished"][:10] for r in rs) if rs else "none",
            f"{p}-last-day": max(r["finished"][:10] for r in rs) if rs else "none",
            f"{p}-target": rs[0]["target"] if rs else "none",
            f"{p}-new-libs": len(new), f"{p}-new-built": sum(r["build_result"] == "built" for r in new),
            f"{p}-oss-libs": sum(r["on_oss_qnx_com"] == "yes" for r in rs),
        }
        rules = rule_counts(arch)
        top = max(rules.items(), key=lambda kv: kv[1]) if rules else ("none", 0)
        n |= {f"{p}-distinct-rules": len(rules), f"{p}-top-rule": top[0], f"{p}-top-rule-count": top[1],
              f"{p}-printf-null-libs": names(printf_null_libs(arch)),
              f"{p}-printf-null-count": len(printf_null_libs(arch))}
    xb = {r["library"] for r in ports if r["arch"] == "x86_64" and r["build_result"] == "built"}
    ab = {r["library"] for r in ports if r["arch"] == "aarch64le" and r["build_result"] == "built"}
    n["built-same"] = (f"the same {len(xb)} libraries built on both architectures" if xb == ab else
                       f"{len(xb & ab)} libraries built on both architectures, "
                       f"{len(xb ^ ab)} on only one ({names(xb ^ ab)})")
    xf, af = n["x-failed-list"], n["a-failed-list"]
    n["failed-sentence"] = (f"The libraries that did not build were {xf} on both architectures." if xf == af else
                            f"The libraries that did not build were {xf} on x86_64, and {af} on aarch64.")
    n["all-libs"] = len({r["library"] for r in ports})
    n["tests-passed-both"] = n["x-tests-passed"] + n["a-tests-passed"]
    n["aarch-only-rules"] = names(set(rule_counts("aarch64le")) - set(rule_counts("x86_64")))

    # Which campaign file the published rows come from: the 2024 pins or the latest releases.
    old, new = campaign_tags("campaign-2024.yaml"), campaign_tags("campaign.yaml")

    def tags(arch):
        vers = {r["library"]: r["version"] for r in ports if r["arch"] == arch}
        m_old = sum(vers.get(k) == v for k, v in old.items())
        m_new = sum(vers.get(k) == v for k, v in new.items())
        if m_old == len(vers):
            return "the 2024 release pins in campaign-2024.yaml"
        if m_new == len(vers):
            return "the latest upstream releases in campaign.yaml"
        return (f"a mix of release tags ({m_old} libraries at their 2024 pins, "
                f"{m_new} at the latest releases in campaign.yaml)")
    xt, at = tags("x86_64"), tags("aarch64le")
    n["campaign-file"] = xt if xt == at else f"{xt} on x86_64 and {at} on aarch64"
    n["latest-differs"] = sum(old.get(k) != v for k, v in new.items())
    n["sdp-build"] = find(r"QNX SDP 8\.0 \(build (\d+), qcc ([\d.]+)\)", "README.md")
    n["qcc-version"] = find(r"QNX SDP 8\.0 \(build (\d+), qcc ([\d.]+)\)", "README.md", 2)


def runs(n: dict) -> None:
    """The campaign script's own summary line, last one in each log."""
    pat = re.compile(r"(\d+) libraries, (\d+) built for QNX 8\.0; tests ran for (\d+)[^:]*: (\d+)/(\d+) passed")
    rows = []
    for i in range(1, 100):
        f = ROOT / f"results/runs/campaign-{i}.log"
        if not f.exists():
            break
        m = pat.findall(f.read_text(encoding="utf-8", errors="replace"))
        if m:
            rows.append((i, *m[-1]))
    n["x-runs"] = len(rows)
    n["small-runs"] = sum(1 for r in rows if r[1] == rows[0][1])  # leading runs with the first run's library count
    n["runs-table"] = rows  # rendered as a table row list, not a scalar
    for i, libs, built, tested, passed, total in rows:
        n[f"run{i}-libs"], n[f"run{i}-built"] = int(libs), int(built)
        n[f"run{i}-passed"], n[f"run{i}-total"] = int(passed), int(total)

    def dns(rel):
        return len(set(re.findall(r"unable to access '([^']+)': Could not resolve host", text(rel))))

    n["dns-x86"] = dns("results/runs/campaign-7.log")
    n["dns-aarch"] = dns("results/runs/campaign-aarch64-2.log")
    n["aarch-hang-seconds"] = round(float(find(r"timed out after ([\d.]+) seconds",
                                               "results/runs/campaign-aarch64-1.log")))
    n["sleep-hours"] = find(r"(\d+) hours were lost overnight", "docs/LEARNINGS.md")
    n["final-run-time"] = find(r"The final run \(`results/runs/campaign-7\.log`[^)]*\) took ([\dh min]+)\.",
                               "docs/LEARNINGS.md").strip()


def model(n: dict) -> None:
    rs = read_csv("results/model_eval.csv")
    n |= {"model-libs": len(rs), "model-built": sum(r["rules_model_build"] == "built" for r in rs),
          "model-kept": sum(int(r["model_patches_kept"]) for r in rs),
          "model-reverted": sum(int(r["model_patches_reverted"]) for r in rs),
          "model-calls": sum(int(r["model_calls"]) for r in rs),
          "model-failed-calls": sum(int(r["model_failed_calls"]) for r in rs),
          "model-tokens-in": sum(int(r["tokens_in"]) for r in rs),
          "model-tokens-out": sum(int(r["tokens_out"]) for r in rs),
          "model-seconds": f"{sum(float(r['model_seconds']) for r in rs):.1f}",
          "model-lib-list": names(r["library"] for r in rs)}
    for r in rs:
        k = re.sub(r"[^a-z0-9]", "", r["library"].lower())
        n[f"model-{k}-tests"] = r["rules_model_tests"]
        n[f"model-{k}-seconds"] = r["model_seconds"]
        n[f"model-{k}-tokens-in"], n[f"model-{k}-tokens-out"] = r["tokens_in"], r["tokens_out"]
    m = re.search(r"subtests: (\d+) ok, (\d+) not ok, (\d+) skipped", text("docs/MODEL_STEP.md"))
    n["libuv-tap-ok"], n["libuv-tap-notok"], n["libuv-tap-skip"] = m.groups()
    n["model-tries"] = find(r"MODEL_TRIES = (\d+)", "qnx_porter/agent.py")


def crates(n: dict) -> None:
    for p, rel in (("x", "results/crates.csv"), ("a", "results/crates-aarch64le.csv")):
        rs = read_csv(rel)
        tested = [r for r in rs if int(r["tests_total"] or 0) > 0]
        tp, tt = sum(int(r["tests_passed"]) for r in tested), sum(int(r["tests_total"]) for r in tested)
        n |= {f"{p}-crates": len(rs), f"{p}-crates-built": sum(r["build_result"] == "built" for r in rs),
              f"{p}-crates-tested": len(tested), f"{p}-crate-tests-passed": tp, f"{p}-crate-tests-total": tt,
              f"{p}-crate-pass-pct": pct(tp, tt),
              f"{p}-crates-failed-list": names(r["crate"] for r in rs if r["build_result"] != "built"),
              f"{p}-crates-allpass": sum(r["tests_passed"] == r["tests_total"] for r in tested)}
    n["rust-nightly"] = find(r"`rustc ([^ ]+-nightly)", "docs/rust/GATE.md")
    n["rust-gate-checks"] = find(r"`stdcheck` makes (\d+) checks", "docs/rust/GATE.md")


def realtime(n: dict) -> None:
    rs = read_csv("results/rt.csv")
    ok = [r for r in rs if not r["error"].strip() and r["loaded_p99_us"]]
    bad = [r for r in rs if r["error"].strip()]
    best = min(ok, key=lambda r: float(r["loaded_isolated_p99_us"]) / float(r["loaded_p99_us"]))
    noisy = [r["library"] for r in ok if float(r["idle_p99_us"]) > float(r["loaded_p99_us"])]
    worse = [r["library"] for r in ok if float(r["loaded_p99_us"]) > float(r["idle_p99_us"])]
    n |= {"rt-measured": len(ok), "rt-specs": len(ok) + len(bad), "rt-not-measured": names(r["library"] for r in bad),
          "rt-iterations": ok[0]["iterations"], "rt-cpus": ok[0]["cpus"],
          "rt-best-lib": best["library"], "rt-best-loaded": best["loaded_p99_us"],
          "rt-best-isolated": best["loaded_isolated_p99_us"],
          "rt-best-ratio": f"{float(best['loaded_p99_us']) / float(best['loaded_isolated_p99_us']):.1f}",
          "rt-noisy-count": len(noisy), "rt-noisy-list": names(noisy), "rt-worse-count": len(worse),
          "rt-halved": sum(float(r["loaded_isolated_p99_us"]) * 2 <= float(r["loaded_p99_us"]) for r in ok)}
    n["rt-priority"] = find(r"SCHED_FIFO priority (\d+)", "docs/RT_RESULTS.md")
    scan = read_csv("results/rt_scan.csv")
    scanned = [r for r in scan if r["sources"] == "scanned"]
    scores = [int(r["static_score"]) for r in scanned]
    n |= {"rt-scan-libs": len(scanned), "rt-scan-min": min(scores), "rt-scan-max": max(scores),
          "rt-scan-heap": sum(int(r["heap"]) > 0 for r in scanned),
          "rt-scan-locks": sum(int(r["locks"]) > 0 for r in scanned),
          "rt-scan-threads": sum(int(r["threads"]) > 0 for r in scanned)}


def evidence(n: dict) -> None:
    lic = read_csv("results/licences.csv")
    n |= {"lic-libs": len(lic), "lic-gpl": sum(r["gpl_family"] == "yes" for r in lic),
          "lic-lgpl": sum(r["lgpl"] == "yes" for r in lic),
          "lic-weak": sum("weak copyleft" in r["copyleft_note"] for r in lic),
          "lic-none": sum(r["detected_licence"] == "NOASSERTION" for r in lic),
          "scancode-version": find(r"ScanCode Toolkit \((scancode-toolkit-[\d.]+)\)", "docs/LICENCES.md")}
    m = re.search(r"(\d+) of (\d+) built\.", text("recipes/BUILD_CHECK.md"))
    n["recipes-built"], n["recipes-total"] = int(m[1]), int(m[2])
    earlier = text("recipes/BUILD_CHECK.md").split("## Earlier run", 1)[1]
    n["recipes-early-failed"] = len(re.findall(r"^\| [^|]+ \| failed", earlier, re.M))
    n["recipes-aarch"] = find(r"(\w+, \w+ and \w+) were built for it earlier", "recipes/BUILD_CHECK.md")

    comp = text("docs/related/qnx-ports-comparison.md")
    rows = re.findall(r"^\| ([^|]+?) \| ([^|]+) \| (\d+) \|$", comp.split("## Library by library")[0], re.M)
    keys = ["cmp-same-change", "cmp-same-problem", "cmp-no-change", "cmp-different"]
    if len(rows) != 4:
        raise SystemExit("build.py: the comparison summary table changed shape")
    for k, (_, _libs, count) in zip(keys, rows):
        n[k] = int(count)
        n[k + "-libs"] = _libs.strip()
    n["cmp-total"] = int(find(r"(\d+) of the \d+ libraries in our campaign have a recipe there",
                              "docs/related/qnx-ports-comparison.md"))
    n["cmp-versions-differ"] = int(find(r"Versions differ\*\* for (\d+) of the", "docs/related/qnx-ports-comparison.md"))
    n["cmp-builtfiles-commit"] = find(r"build-files commit `([0-9a-f]+)`", "docs/related/qnx-ports-comparison.md")

    s = "docs/qnx-reports/strtod-rounding.md"
    m = re.search(r"QNX 8\.0 x86_64 target:\n```\n(\d+) random doubles: (\d+) \(([\d.]+)%\) parse back wrong; "
                  r"worst (\d+) ulp", text(s))
    n["strtod-n"], n["strtod-wrong"], n["strtod-pct"], n["strtod-worst"] = m.groups()
    q = "docs/qnx-reports/qsort-inconsistent-comparator.md"
    n["qsort-bad"], n["qsort-calls"] = re.search(r"QNX 8\.0 x86_64:\s+(\d+) of (\d+) qsort calls", text(q)).groups()
    n["qsort-glibc-bad"] = find(r"Linux \(glibc\):\s+(\d+) of", q)
    n["fchdir-death-tests"] = find(r"passes (\d+) of \d+ tests", "docs/qnx-reports/fchdir-o-rdonly.md")
    n["strftime-assertions"] = find(r"\((\d+ \+ \d+) assertions\)", "docs/qnx-reports/strftime-E-modifier.md")
    n["pugixml-strtod-fail"], n["pugixml-tests"] = re.search(
        r"(\d+) of pugixml 1\.14's (\d+) tests", text(s)).groups()

    cand = read_csv("results/candidates_check.csv")
    n["cand-libs"] = len(cand)
    n["cand-new"] = sum(r["on_oss_qnx_com"] == "no" and r["in_qnx_ports_org"] == "False" for r in cand)
    n["linuxisms"] = len(re.findall(r"^\| \d+[a-z]? \|", text("docs/LINUX_ISMS.md"), re.M))
    n["pytest-count"] = sum(len(re.findall(r"^def test_", f.read_text(encoding="utf-8"), re.M))
                            for f in sorted((ROOT / "tests").glob("test_*.py")))
    n["py-lines"] = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in (ROOT / "qnx_porter").glob("*.py"))
    n["upstream-drafts"] = len([d for d in (ROOT / "docs/upstream").iterdir() if d.is_dir()])
    n["timeout-cap"] = find(r"QNX's own `timeout -s KILL` \((\d+) s cap\)", "docs/LEARNINGS.md")


def collect() -> dict:
    n: dict = {}
    for step in (campaign, runs, model, crates, realtime, evidence):
        step(n)
    return n


# ---------------------------------------------------------------- LaTeX macros

TEX_ESC = {"\\": r"\textbackslash{}", "_": r"\_", "&": r"\&", "%": r"\%", "#": r"\#", "$": r"\$",
           "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\^{}"}


def tex_escape(s) -> str:
    return "".join(TEX_ESC.get(c, c) for c in str(s))


def write_numbers(n: dict) -> None:
    lines = ["% Generated by paper/build.py from the repository's result files. Do not edit.",
             r"\makeatletter",
             r"\newcommand{\N}[1]{\@ifundefined{num@#1}{\errmessage{paper/build.py defines no number #1}}"
             r"{\csname num@#1\endcsname}}"]
    for k, v in sorted(n.items()):
        if k == "runs-table":
            body = " ".join(rf"{i} & {libs} & {built} & {tested} & {passed}/{total} \\"
                            for i, libs, built, tested, passed, total in v)
            v = body
            lines.append(rf"\expandafter\def\csname num@{k}\endcsname{{{v}}}")
            continue
        lines.append(rf"\expandafter\def\csname num@{k}\endcsname{{{tex_escape(v)}}}")
    lines.append(r"\makeatother")
    (HERE / "numbers.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- tex -> markdown

def arg(s: str, i: int) -> tuple[str, int]:
    """The balanced {...} group starting at s[i] == '{': its content and the index after it."""
    assert s[i] == "{", s[i:i + 40]
    depth = 0
    for j in range(i, len(s)):
        depth += {"{": 1, "}": -1}.get(s[j], 0)
        if depth == 0:
            return s[i + 1:j], j + 1
    raise ValueError("unbalanced braces near: " + s[i:i + 60])


def sub_cmd(s: str, name: str, nargs: int, fn) -> str:
    pat = re.compile(r"\\" + name + r"(?![A-Za-z])\s*(\[[^\]]*\])?")
    out, pos = [], 0
    while m := pat.search(s, pos):
        i, args = m.end(), []
        for _ in range(nargs):
            a, i = arg(s, i)
            args.append(a)
        out.append(s[pos:m.start()] + fn(*args))
        pos = i
    return "".join(out) + s[pos:]


class Md:
    def __init__(self, n: dict, tex: str):
        self.n, self.tex = n, tex
        self.labels, self.cites = {}, {}
        self.number()

    def number(self):
        """Section, figure and table numbers in document order, as LaTeX will number them."""
        sec = sub = fig = tab = 0
        appendix = False
        cur = ""
        for m in re.finditer(r"\\(section|subsection|appendix|label|bibitem|begin\{(figure\*?|table\*?)\})"
                             r"(\*?)(\{([^}]*)\})?", self.tex):
            kind = m[1]
            if kind == "appendix":
                appendix, sec = True, 0
            elif kind == "section" and not m[3]:
                sec, sub = sec + 1, 0
                cur = chr(64 + sec) if appendix else str(sec)
            elif kind == "subsection" and not m[3]:
                sub += 1
                cur = f"{chr(64 + sec) if appendix else sec}.{sub}"
            elif kind.startswith("begin{figure"):
                fig += 1
                cur = str(fig)
            elif kind.startswith("begin{table"):
                tab += 1
                cur = str(tab)
            elif kind == "label":
                self.labels[m[5]] = cur
            elif kind == "bibitem":
                self.cites[m[5]] = str(len(self.cites) + 1)

    def value(self, k):
        if k not in self.n:
            raise SystemExit(f"build.py: the paper uses \\N{{{k}}}, which build.py does not define")
        return str(self.n[k])

    def inline(self, s: str) -> str:
        kept: list[str] = []  # code and URLs are set aside so the typography rules below leave them alone

        def keep(t: str) -> str:
            kept.append(t)
            return f"\x02{len(kept) - 1}\x02"

        def code(a: str) -> str:
            a = a.replace("-{}-", "--").replace(r"\textasciitilde{}", "~").replace(r"\textbackslash{}", "\x03")
            return keep("`" + a.replace("\\", "").replace("\x03", "\\") + "`")

        s = sub_cmd(s, "N", 1, lambda k: self.value(k))
        s = sub_cmd(s, "texttt", 1, code)
        s = sub_cmd(s, "url", 1, lambda a: keep(f"<{a}>"))
        s = sub_cmd(s, "href", 2, lambda u, t: f"[{t}]({keep(u)})")
        s = sub_cmd(s, "cite", 1, lambda a: "[" + ", ".join(self.cites[k.strip()] for k in a.split(",")) + "]")
        s = sub_cmd(s, "ref", 1, lambda a: self.labels[a])
        s = sub_cmd(s, "label", 1, lambda a: "")
        s = sub_cmd(s, "textbf", 1, lambda a: f"**{a}**")
        s = sub_cmd(s, "emph", 1, lambda a: f"*{a}*")
        s = sub_cmd(s, "textit", 1, lambda a: f"*{a}*")
        s = sub_cmd(s, "mbox", 1, lambda a: a)
        s = sub_cmd(s, "footnote", 1, lambda a: f" ({a})")
        for a, b in ((r"\%", "%"), (r"\_", "_"), (r"\&", "&"), (r"\#", "#"), (r"\$", "$"), ("~", " "),
                     ("---", "\u2014"), ("--", "\u2013"), ("``", "\u201c"), ("''", "\u201d"), (r"\ldots", "\u2026"),
                     (r"\textasciitilde{}", "~"), (r"\textbackslash{}", "\\"), (r"\^{}", "^"),
                     (r"$\times$", "\u00d7"), (r"$\mu$", "\u00b5"), (r"\,", " "), (r"\@", ""), (r"\{", "{"),
                     (r"\}", "}"), (r"\ ", " "), (r"\noindent", ""), (r"\centering", ""), (r"\small", ""),
                     (r"\footnotesize", "")):
            s = s.replace(a, b)
        return re.sub("\x02(\\d+)\x02", lambda m: kept[int(m[1])], s)

    def table(self, body: str) -> str:
        body = re.sub(r"\\(toprule|midrule|bottomrule|hline)", "", body)
        body = body.strip()
        if body.startswith("{"):
            body = body[arg(body, 0)[1]:]  # drop the column spec
        rows = [r.strip() for r in body.split(r"\\") if r.strip()]
        cells = [[self.inline(c.strip()) for c in r.split("&")] for r in rows]
        out = ["| " + " | ".join(cells[0]) + " |", "|" + "---|" * len(cells[0])]
        out += ["| " + " | ".join(c) + " |" for c in cells[1:]]
        return "\n".join(out)

    def render(self) -> str:
        t = self.tex
        def flat(x: str) -> str:
            return " ".join(self.inline(x.replace("\\\\", " ")).split())

        title = flat(arg(t, t.index(r"\title{") + 6)[0])
        who = flat(arg(t, t.index(r"\IEEEauthorblockN{") + 17)[0])
        where = flat(arg(t, t.index(r"\IEEEauthorblockA{") + 17)[0])
        abstract = flat(re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", t, re.S)[1])
        body = t.split(r"\end{abstract}", 1)[1].split(r"\end{document}")[0]
        body = re.sub(r"(?<!\\)%[^\n]*", "", body)  # comments
        out = [f"# {title}", "", f"**{who}**", "", where, "",
               "> The PDF, `paper/qnx-porter.pdf`, is built from `paper/qnx-porter.tex`; this page is generated from "
               "the same source by `paper/build.py`, and every number in it comes from the repository's result files.",
               "", "## Abstract", "", abstract, ""]
        # environments first, so their insides are not treated as paragraphs
        figs = {}

        def env(m):
            kind, inner = m[1], m[2]
            key = f"\x00{len(figs)}\x00"
            if kind.startswith("figure"):
                img = re.search(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", inner)[1]
                cap = arg(inner, inner.index(r"\caption{") + 8)[0]
                lab = re.search(r"\\label\{([^}]+)\}", inner)[1]
                num = self.labels[lab]
                cap = " ".join(self.inline(cap).split())
                img = img if "/" in img else "fig/" + img  # \graphicspath{{fig/}} in the .tex
                figs[key] = f"![Figure {num}: {cap}]({img}.png)\n\n*Figure {num}. {cap}*"
            elif kind.startswith("table"):
                cap = " ".join(self.inline(arg(inner, inner.index(r"\caption{") + 8)[0]).split())
                lab = re.search(r"\\label\{([^}]+)\}", inner)[1]
                tab = re.search(r"\\begin\{tabular\*?\}(.*?)\\end\{tabular\*?\}", inner, re.S)[1]
                tab = tab.replace(r"\N{runs-table}", self.runs_rows())
                figs[key] = f"*Table {self.labels[lab]}. {cap}*\n\n{self.table(tab)}"
            elif kind in ("verbatim", "lstlisting"):
                figs[key] = "```\n" + inner.strip("\n") + "\n```"
            elif kind in ("itemize", "enumerate"):
                items = [i.strip() for i in re.split(r"\\item\s*", inner) if i.strip()]
                mark = (lambda k: "- ") if kind == "itemize" else (lambda k: f"{k + 1}. ")
                figs[key] = "\n".join(mark(k) + " ".join(self.inline(i).split()) for k, i in enumerate(items))
            elif kind == "thebibliography":
                items = re.findall(r"\\bibitem\{([^}]+)\}(.*?)(?=\\bibitem|\Z)", inner, re.S)
                figs[key] = "\n\n".join(f"[{self.cites[k]}] " + " ".join(self.inline(v).split()) for k, v in items)
            return f"\n\n{key}\n\n"

        envs = r"(figure\*?|table\*?|verbatim|lstlisting|itemize|enumerate|thebibliography)"
        body = re.sub(r"\\begin\{" + envs + r"\}(?:\{[^}]*\})?(?:\[[^\]]*\])?(.*?)\\end\{\1\}", env, body, flags=re.S)
        body = body.replace(r"\appendix", "")
        heads = {}

        parts, pos = [], 0  # headings: titles can hold braces (\texttt{...}), so take the balanced group
        while m := re.compile(r"\\(section|subsection)(\*?)(?=\{)").search(body, pos):
            title, end = arg(body, m.end())
            lab = re.match(r"\s*\\label\{([^}]+)\}", body[end:])
            num = self.labels.get(lab[1], "") if lab and not m[2] else ""
            key = f"\x01{len(heads)}\x01"
            heads[key] = f"{'##' if m[1] == 'section' else '###'} {num + ' ' if num else ''}{self.inline(title)}"
            parts.append(body[pos:m.start()] + f"\n\n{key}\n\n")
            pos = end + (lab.end() if lab else 0)
        body = "".join(parts) + body[pos:]
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if not para or para in (r"\maketitle", r"\bibliographystyle{IEEEtran}"):
                continue
            if para in figs:
                out += [figs[para], ""]
            elif para in heads:
                out += [heads[para], ""]
            else:
                p = " ".join(self.inline(para).split())
                p = re.sub(r"\\paragraph\{([^}]*)\}", r"**\1.**", p)
                if p:
                    out += [p, ""]
        md = "\n".join(out).rstrip() + "\n"
        left = re.findall(r"\\[A-Za-z]+", md.replace("\\\\", ""))
        left = [x for x in left if x not in ("\\n",)]
        if left:
            raise SystemExit(f"build.py: paper.md still has LaTeX commands: {sorted(set(left))[:12]}")
        return md

    def runs_rows(self) -> str:
        return " ".join(rf"{i} & {libs} & {built} & {tested} & {passed}/{total} \\"
                        for i, libs, built, tested, passed, total in self.n["runs-table"])


def main() -> int:
    n = collect()
    write_numbers(n)
    tex = (HERE / "qnx-porter.tex").read_text(encoding="utf-8")
    used = set(re.findall(r"\\N\{([^}]+)\}", re.sub(r"(?<!\\)%[^\n]*", "", tex)))
    missing = sorted(used - set(n))
    if missing:
        raise SystemExit(f"build.py: the paper uses numbers nobody defines: {missing}")
    (HERE / "paper.md").write_text(Md(n, tex).render(), encoding="utf-8", newline="\n")
    print(f"paper/numbers.tex: {len(n)} values; paper/paper.md written; the paper uses {len(used)} of them")
    return 0


if __name__ == "__main__":
    sys.exit(main())
