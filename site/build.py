"""Build the project website from the repository: results, ports, rules and docs. Nothing is typed twice.

Every number on the site is read from ports/*/report.json (written by the porter on a QNX target), from
results/*.csv (written by scripts/ports_csv.py and the other result scripts), or from the committed logs and
docs the evidence cards quote. Pages: landing, results dashboard, one page per port, the weekly upstream check,
the codelabs, the rule corpus and setup. Output: site/_out/ (published to GitHub Pages by CI).

Usage: python site/build.py   (needs Python-Markdown: pip install markdown)
"""
import csv
import html
import json
import posixpath
import re
import shutil
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "_out"
REPO = "https://github.com/thegoodengineers/qnx-porter"
BLOB = f"{REPO}/blob/main"
ARCH_LABEL = {"x86_64": "x86_64", "aarch64le": "aarch64"}
PORT_DIRS = ["ports", "ports-aarch64le"]  # x86_64 campaign, aarch64 campaign (the latter may not exist yet)
NAV = [("index.html", "Home"), ("evaluate.html", "For evaluators"), ("evidence.html", "Evidence"),
       ("results.html", "Results"), ("docs.html", "Docs"), ("codelab-port-a-library.html", "Codelab"),
       ("paper.html", "Paper"), ("upstream.html", "Weekly check"), ("setup.html", "Run it"),
       ("index.html#team", "Team"), (REPO, "GitHub")]
# The docs section: (group, [markdown files]). Each file becomes a page; a few keep the URL they always had.
DOC_GROUPS = [
    ("Guides", ["docs/codelab/port-a-library.md", "docs/CODELAB.md", "SETUP.md", "docs/ARCHITECTURE.md"]),
    ("Results", ["docs/MODEL_STEP.md", "docs/rust/CRATES.md", "docs/rust/GATE.md", "docs/RT_RESULTS.md",
                 "docs/RT_READINESS.md", "docs/related/qnx-ports-comparison.md", "recipes/BUILD_CHECK.md",
                 "docs/LICENCES.md"]),
    ("Findings", ["docs/LINUX_ISMS.md", "*docs/qnx-reports/*.md", "docs/LEARNINGS.md"]),
    ("Project", ["docs/LIMITATIONS.md", "docs/upstream/README.md", "docs/RELEASE.md"]),
]
FIXED_URLS = {"docs/codelab/port-a-library.md": "codelab-port-a-library.html", "docs/CODELAB.md": "codelab.html",
              "docs/LINUX_ISMS.md": "rules.html", "SETUP.md": "setup.html", "paper/paper.md": "paper.html"}


def doc_files() -> list[tuple[str, list[str]]]:
    return [(g, [p for f in fs for p in (sorted(x.relative_to(ROOT).as_posix() for x in ROOT.glob(f[1:]))
                                         if f.startswith("*") else [f]) if (ROOT / p).exists()]) for g, fs in DOC_GROUPS]


def out_path(src: str) -> str:
    """Where a markdown file is rendered: its fixed URL, or docs/<path-as-slug>.html."""
    return FIXED_URLS.get(src) or "docs/" + re.sub(r"[^a-z0-9]+", "-", src.removeprefix("docs/").removesuffix(".md").lower()) + ".html"


RENDERED = {p: out_path(p) for _, fs in doc_files() for p in fs} | {k: v for k, v in FIXED_URLS.items() if (ROOT / k).exists()}
FONTS = "https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500&display=swap"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")


def load_reports() -> list[dict]:
    reps = []
    for f in sorted(f for d in PORT_DIRS for f in (ROOT / d).glob("*/report.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if r.get("arch") == "host":
            continue
        r["_dir"] = f.parent
        r["_slug"] = f"{r['library']}-{r['arch']}"
        reps.append(r)
    return sorted(reps, key=lambda r: (r["library"].lower(), r["arch"]))


def oss_listed() -> set:
    f = ROOT / "results" / "oss_listed.json"
    return set(json.loads(f.read_text())) if f.exists() else set()


def readme_facts() -> dict:
    """The team, the hackathon category and the quick-start commands, as README.md states them."""
    text = read("README.md")
    m = re.search(r"\(([^()]+)\) by\s+([^()]+?) \(([^()]+)\)\.", text)
    qs = text.split("## Quick start", 1)[1]
    block = qs.split("```bash", 1)[1].split("```", 1)[0]
    cmds = [ln.split("  #")[0].rstrip() for ln in block.splitlines() if ln.startswith(("source", "qnx-porter"))]
    return {"category": m.group(1), "names": re.split(r",\s*|\s+and\s+", m.group(2).strip()), "team": m.group(3),
            "install": re.search(r"Install: `([^`]+)`", qs).group(1), "quick": cmds}


README = readme_facts()

TOC_JS = """<script>
(function () {
  var links = document.querySelectorAll('.here a'); if (!links.length || !('IntersectionObserver' in window)) return;
  var by = {}; links.forEach(function (a) { by[decodeURIComponent(a.hash.slice(1))] = a; });
  var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (!e.isIntersecting) return;
    links.forEach(function (a) { a.removeAttribute('aria-current'); }); by[e.target.id].setAttribute('aria-current', 'location'); });
  }, { rootMargin: '0px 0px -75% 0px' });
  Object.keys(by).forEach(function (id) { var h = document.getElementById(id); if (h) io.observe(h); });
})();
</script>"""


def toc(body: str) -> tuple[str, list[tuple[str, str]]]:
    """Give every h2 an id (unless it has one) and return the page's sections for the rail."""
    seen, items = set(), []

    def one(m):
        attrs, inner = m.group(1), m.group(2)
        text = re.sub(r"<[^>]+>", "", inner).strip()
        found = re.search(r'id="([^"]+)"', attrs)
        hid = found.group(1) if found else (re.sub(r"[^a-z0-9]+", "-", html.unescape(text).lower()).strip("-") or "s")
        base, k = hid, 2
        while hid in seen:
            hid, k = f"{base}-{k}", k + 1
        seen.add(hid)
        items.append((hid, text))
        return f'<h2{attrs if found else attrs + f" id={chr(34)}{hid}{chr(34)}"}>{inner}</h2>'

    return re.sub(r"<h2([^>]*)>(.*?)</h2>", one, body, flags=re.S), items


def page(title: str, body: str, current: str, depth: int = 0, desc: str = "") -> str:
    up = "../" * depth
    doors = "".join(f'<a href="{h if h.startswith("http") else up + h}"'
                    f'{" class=ext" if h.startswith("http") else ""}'
                    f'{" aria-current=page" if h == current else ""}>{esc(t)}</a>' for h, t in NAV)
    body, items = toc(body)
    here = "".join(f'<a href="#{esc(i)}">{t}</a>' for i, t in items)
    run = "\n".join([README["install"]] + README["quick"])
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or 'qnx-porter ports open-source C/C++ libraries to QNX 8.0 and proves each port on a QNX target.')}">
<meta name="color-scheme" content="light">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="{FONTS}"><link rel="stylesheet" href="{up}style.css"></head><body>
<a class="skip" href="#main">Skip to content</a>
<div class="shell">
<aside class="rail">
<a class="brand" href="{up}index.html"><span class="brand-mark" aria-hidden="true"></span>qnx-porter<small>QNX 8.0</small></a>
<nav class="doors" aria-label="Pages">{doors}</nav>
<hr class="rail-rule">
{f'<nav class="here" aria-label="On this page">{here}</nav>' if here else ''}
<div class="runit"><p class="label">Run it</p><pre><code>{esc(run)}</code></pre><a class="section-link" href="{up}setup.html">Full setup &rarr;</a></div>
</aside>
<main class="col" id="main">{body}
<footer><span>Apache-2.0 &middot; built from the repository by CI; every number is read from a file in it</span>
<a href="{REPO}">{REPO.removeprefix('https://')}</a><span>No cookies, no trackers, no scripts from other sites.</span></footer>
</main></div>{TOC_JS if here else ''}
</body></html>
"""


def tests_cell(r: dict) -> str:
    if not r.get("tests_ran"):
        return '<span class="warn">not run</span>' + (f' <span class="label">{esc(r["note"])}</span>' if r.get("note") else "")
    if r["tests_total"] == 0:
        return '<span class="warn">none built</span>'
    cls = "ok" if r["tests_passed"] == r["tests_total"] else "bad"
    extra = f' <span class="label">+{len(r["tests_not_runnable"])} need a tool QNX lacks</span>' \
        if r.get("tests_not_runnable") else ""
    return f'<span class="{cls}">{r["tests_passed"]}/{r["tests_total"]}</span>{extra}'


def totals(reps: list[dict], arch: str) -> dict:
    rs = [r for r in reps if r["arch"] == arch]
    ran = [r for r in rs if r.get("tests_ran") and r["tests_total"]]  # same rule as the README headline
    return {"libs": len(rs), "built": sum(r["build_result"] == "built" for r in rs),
            "passed": sum(r["tests_passed"] for r in ran), "total": sum(r["tests_total"] for r in ran),
            "patches": sum(r["patches_kept"] for r in rs), "by_rule": sum(r["patches_by_rule"] for r in rs),
            "by_model": sum(r["patches_by_model"] for r in rs), "with_tests": len(ran)}


def tile(n, t: str, src: str = "") -> str:
    return (f'<div class="tile"><b>{n}</b><span>{t}</span>' + (f"<small>{esc(src)}</small>" if src else "") + "</div>")


def rows_of(rel: str) -> list[dict]:
    return list(csv.DictReader((ROOT / rel).open(encoding="utf-8")))


def crate_totals(rel: str) -> dict:
    rs = rows_of(rel)
    ran = [r for r in rs if r["build_result"] == "built" and int(r["tests_total"])]
    return {"n": len(rs), "built": sum(r["build_result"] == "built" for r in rs),
            "passed": sum(int(r["tests_passed"]) for r in ran), "total": sum(int(r["tests_total"]) for r in ran)}


# The real flow (docs/ARCHITECTURE.md). Classes are styled in style.css, so the figure follows dark mode.
def _box(x, y, title, *sub, cls="box"):
    lines = "".join(f'<text class="m" x="{x + 12}" y="{y + 42 + 13 * i}">{esc(s)}</text>' for i, s in enumerate(sub))
    return f'<rect class="{cls}" x="{x}" y="{y}" width="136" height="{64 if len(sub) > 1 else 56}"/><text class="t" x="{x + 12}" y="{y + 24}">{esc(title)}</text>{lines}'


PIPELINE_SVG = f"""<svg class="diagram" viewBox="0 0 780 330" role="img" aria-labelledby="pipe-t pipe-d">
<title id="pipe-t">The qnx-porter pipeline</title>
<desc id="pipe-d">Detect the build system, write the QNX toolchain, build with qcc. On errors: parse them, try the
deterministic rules, and only where no rule fits, a language-model step whose diff is kept if the rebuild clears
the error and reverted if not. Each fix becomes a numbered patch and the build runs again. When the build is OK:
sync to the QNX target, run the library's own tests there, triage any crash from its core dump, write the report.</desc>
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path class="head" d="M0 0L10 5L0 10z"/></marker></defs>
{_box(10, 20, "detect", "build system")}{_box(166, 20, "QNX toolchain", "qcc + sysroot")}{_box(322, 20, "build", "configure, make")}
{_box(478, 20, "parse errors", "GCC, ld, CMake")}{_box(634, 20, "rules", "deterministic")}
{_box(478, 130, "patches", "one per change,", "with its reason")}{_box(634, 130, "language model", "verified, or", "reverted", cls="accbox")}
{_box(166, 250, "sync to target", "QNX 8.0 over ssh")}{_box(322, 250, "own tests", "on the target")}
{_box(478, 250, "crash triage", "core dump, gdb")}{_box(634, 250, "report", "REPORT.md, json", cls="soft")}
<path class="line" marker-end="url(#ah)" d="M146 48H164M302 48H320M458 48H476M614 48H632"/>
<path class="line" marker-end="url(#ah)" d="M660 76V100H546V128"/>
<path class="line" marker-end="url(#ah)" d="M722 76V128"/><text class="m" x="716" y="118" text-anchor="end">no rule fits</text><text class="m" x="556" y="94">a rule fits</text>
<path class="line" marker-end="url(#ah)" d="M634 162H616"/>
<path class="dash" marker-end="url(#ah)" d="M478 162H390V78"/><text class="m" x="398" y="156">rebuild</text>
<path class="line" marker-end="url(#ah)" d="M350 76V220H234V248"/><text class="m" x="244" y="214">build OK</text>
<path class="line" marker-end="url(#ah)" d="M302 278H320M458 278H476M614 278H632"/>
<path class="dash" marker-end="url(#ah)" d="M390 306V320H700V308"/><text class="m" x="470" y="317">no crash</text>
</svg>"""


COMPARISON = "docs/related/qnx-ports-comparison.md"


def comparison_summary() -> list[tuple[str, str, int]]:
    """The (outcome, libraries, count) rows of the Summary table in the qnx-ports comparison."""
    summary = read(COMPARISON).split("## Summary", 1)[1].split("\n## ", 1)[0]
    rows = [(o.strip(), libs.strip(), int(n)) for o, libs, n in re.findall(r"^\|([^|]+)\|([^|]+)\|\s*(\d+)\s*\|$", summary, re.M)]
    if not rows:
        raise SystemExit(f"no summary table found in {COMPARISON}")
    return rows


def lib_line(reps: list[dict], name: str) -> str:
    """One line on a campaign library, from its x86_64 report."""
    r = next(r for r in reps if r["library"] == name and r["arch"] == "x86_64")
    link = f'<a href="ports/{esc(r["_slug"])}.html">{esc(name)}</a>'
    if r["build_result"] != "built":
        return f"<li>{link}: {esc(status_text(r))}.</li>"
    if r.get("tests_ran") and r["tests_total"]:
        return f"<li>{link}: built, {r['tests_passed']}/{r['tests_total']} of its own tests pass on QNX 8.0.</li>"
    return f"<li>{link}: built; tests not run{(' (' + esc(r['note']) + ')') if r.get('note') else ''}.</li>"


# ---- evidence cards: excerpts read from committed logs at build time, never typed ----
def elide(s: str) -> str:
    """Shorten the porter's work folder in a path to '…/' so a line fits a card; the rest is verbatim."""
    return re.sub(r"/home/\S*?/work/(?:src|build)/", "…/", s.strip())


def ev_card(srcs: list[str], tag: str, lines: list[str]) -> str:
    src = " · ".join(f'<a href="{BLOB}/{s}">{esc(s)}</a>' for s in srcs)
    return (f'<figure class="ev"><figcaption><b>{esc(Path(srcs[0]).name)}</b> &middot; {esc(tag)}</figcaption>'
            f'<pre><code>{esc(chr(10).join(lines))}</code></pre><p class="src">{src}</p></figure>')


def evidence() -> str:
    cards = []
    crash = "ports/json-c/logs/crashes.log"
    frames = []
    for ln in read(crash).splitlines():
        m = re.match(r"^(#\d+)\s+(?:0x[0-9a-f]+ in )?(\S+) \(.*\) at (\S+)$", ln)
        if m and (f := f"{m[1]}  {m[2]} () at …/{'/'.join(m[3].split('/')[-2:])}") not in frames:
            frames.append(f)
    sig = next(ln for ln in read(crash).splitlines() if ln.startswith("Program terminated"))
    cards.append(ev_card([crash], "crash triage on QNX", [sig] + frames))
    tests = "ports/json-c/logs/tests.log"
    cards.append(ev_card([tests], "json-c's own tests on QNX", [ln for ln in read(tests).splitlines() if ln.strip()][-4:]))
    patch = "ports/libevent/patches/0001-sa-restart.patch"
    cards.append(ev_card([patch], "rule patch with its reason", [elide(ln) for ln in read(patch).split("\n---\n", 1)[0].splitlines()]))
    model = "docs/MODEL_STEP.md"
    mtext = read(model)
    mrows = ["library        rules    rules + model"] + [f"{lib:<14} {a:<8} {b}"
             for lib, a, b in re.findall(r"^\| \[([^\]]+)\]\([^)]*\) \| (\w+) \| (\w+) \|", mtext, re.M)]
    cards.append(ev_card([model], "language-model step", mrows + [next(ln for ln in mtext.splitlines() if ln.startswith("With the model step"))]))
    rust = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / "results" / "runs").glob("crates-*.log"))
    cards.append(ev_card(rust, "Rust crates on QNX", [next(ln for ln in reversed(read(f).splitlines()) if re.match(r"^\w+: \d+ crates", ln)) for f in rust]))
    a64 = sorted((ROOT / "results" / "runs").glob("campaign-aarch64-*.log"), key=lambda p: int(re.findall(r"\d+", p.stem)[-1]))[-1]
    a64rel, lines = a64.relative_to(ROOT).as_posix(), read(a64.relative_to(ROOT).as_posix()).splitlines()
    t = max(i for i, ln in enumerate(lines) if "tests on target" in ln and "QEMU_virt" in ln)
    head = next(lines[i] for i in range(t, -1, -1) if lines[i].startswith("==="))
    cards.append(ev_card([a64rel], "aarch64 on QEMU", [head, lines[t].strip(), lines[t + 1].strip(),
                                                      next(ln for ln in reversed(lines) if ln.startswith("aarch64le: "))]))
    return "".join(cards)


def status_text(r: dict) -> str:
    """build_result in words; needs-qnx-equivalent is the porting advisor's status (qnx_porter/advisor.py)."""
    return "needs a QNX equivalent" if r["build_result"] == "needs-qnx-equivalent" else r["build_result"]


def outcome(r: dict) -> tuple[str, str]:
    if r["build_result"] == "needs-qnx-equivalent":
        return "equiv", "needs a QNX equivalent"
    if r["build_result"] != "built":
        return "no", esc(r["build_result"])
    if r.get("tests_ran") and r["tests_total"]:
        return ("done" if r["tests_passed"] == r["tests_total"] else "part"), f'{r["tests_passed"]}/{r["tests_total"]}'
    return "built", "tests not run"


OUTCOMES = [("done", "all own tests passed on QNX"), ("part", "some tests failed"),
            ("built", "built, tests not run"), ("equiv", "needs a QNX equivalent"), ("no", "did not build")]


def coverage(reps: list[dict]) -> str:
    rs = [r for r in reps if r["arch"] == "x86_64"]
    got = [(r, *outcome(r)) for r in rs]
    legend = "".join(f'<span><i class="{k}"></i>{esc(t)} &middot; {sum(o == k for _, o, _ in got)}</span>' for k, t in OUTCOMES)
    items = "".join(f'<li class="{o}"><i></i><a href="ports/{esc(r["_slug"])}.html">{esc(r["library"])}</a> <span>{d}</span></li>'
                    for r, o, d in got)
    return f'<div class="legend">{legend}</div><ul class="status">{items}</ul>'


def measured(reps: list[dict], cmp_rows) -> str:
    rows = []
    for a in sorted({r["arch"] for r in reps}, key=lambda a: (a != "x86_64", a)):
        t = totals(reps, a)
        where = "x86_64 under KVM" if a == "x86_64" else f"{ARCH_LABEL.get(a, a)} on QEMU virt"
        rows.append((f"C/C++ libraries, QNX 8.0 {where}", f"{t['built']}/{t['libs']} built · {t['passed']}/{t['total']} tests passed",
                     "results/ports.csv"))
    for f, label in (("results/crates.csv", "x86_64"), ("results/crates-aarch64le.csv", "aarch64 on QEMU")):
        if (ROOT / f).exists():
            c = crate_totals(f)
            rows.append((f"Rust crates, {label}", f"{c['built']}/{c['n']} built · {c['passed']}/{c['total']} tests passed", f))
    me = rows_of("results/model_eval.csv")
    failed = [r for r in me if r["rules_only_build"] != "built"]
    rows.append(("Language-model step, where no rule could build",
                 f"{sum(r['rules_model_build'] == 'built' for r in failed)}/{len(failed)} built · "
                 f"{sum(int(r['model_patches_kept']) for r in me)} kept, {sum(int(r['model_patches_reverted']) for r in me)} reverted",
                 "results/model_eval.csv"))
    total = sum(n for _, _, n in cmp_rows)
    rows.append(("Against QNX's own qnx-ports recipes", f"{cmp_rows[0][2]}/{total} " + cmp_rows[0][0], COMPARISON))
    bc = re.search(r"^(\d+) of (\d+) built\.", read("recipes/BUILD_CHECK.md"), re.M)
    rows.append(("Recipes in qnx-ports/build-files layout, QNX recursive make", f"{bc[1]}/{bc[2]} built", "recipes/BUILD_CHECK.md"))
    lic = rows_of("results/licences.csv")
    sboms = sum(1 for d in PORT_DIRS[:1] for _ in (ROOT / d).glob("*/sbom.spdx.json"))
    rows.append(("SPDX SBOM and licence check per port", f"{sboms} SBOMs · {sum('yes' in (r['gpl_family'], r['lgpl']) for r in lic)}/{len(lic)} flagged copyleft",
                 "results/licences.csv"))
    rt = rows_of("results/rt.csv")
    rows.append(("Latency of one call, idle and under load (QEMU: ranks, guarantees nothing)",
                 f"{len({r['library'] for r in rt if r['arch'] == 'x86_64'})} libraries timed", "results/rt.csv"))
    h = ROOT / HISTORY
    if h.exists() and (hist := rows_of(HISTORY)):
        last = [r for r in hist if r["run"] == max(r["run"] for r in hist)]
        rows.append(("Weekly re-port at upstream HEAD", f"{sum(r['build_result'] == 'built' for r in last)}/{len(last)} built, run {esc(last[0]['run'])}", HISTORY))
    else:
        rows.append(("Weekly re-port at upstream HEAD", "no run recorded in this build", HISTORY))
    trs = "".join(f'<tr><td class="k">{esc(c)}</td><td class="n">{esc(v)}<a class="src" href="{REPO + "/blob/data/head-history" if s == HISTORY else BLOB}/{s}">{esc(s)}</a></td></tr>'
                  for c, v, s in rows)
    return f'<div class="table-wrap"><table class="table stack"><thead><tr><th>Claim</th><th>Result and source</th></tr></thead><tbody>{trs}</tbody></table></div>'


def index(reps: list[dict]) -> str:
    t = totals(reps, "x86_64")
    a64 = totals(reps, "aarch64le")
    rules = len(re.findall(r"^\| \d+[a-z]? \|", read("docs/LINUX_ISMS.md"), re.M))
    cmp_rows = comparison_summary()
    cmp_table = "".join(f'<tr><td>{esc(o)}</td><td>{esc(libs)}</td><td class="n">{n}</td></tr>' for o, libs, n in cmp_rows)
    cited = "".join(lib_line(reps, n) for n in ("zlib", "libsodium", "sqlite"))
    tiles = (tile(f"{t['built']}/{t['libs']}", "libraries built for QNX 8.0 x86_64", "results/ports.csv")
             + tile(f"{t['passed']}/{t['total']}", f"of their own tests passed on the QNX target ({t['with_tests']} libraries)", "ports/*/logs/tests.log")
             + (tile(f"{a64['built']}/{a64['libs']}", f"built for aarch64 on QEMU; {a64['passed']}/{a64['total']} tests passed",
                     "ports-aarch64le/*/report.json") if a64["libs"] else "")
             + tile(t["patches"], f"patches, {t['by_rule']} by deterministic rules, {t['by_model']} by the model", "ports/*/patches/")
             + tile(rules, "Linux-isms in the rule corpus, each with a test", "docs/LINUX_ISMS.md"))
    team = "".join(f"<li>{esc(n)}</li>" for n in README["names"])
    body = f"""
<header class="hero">
<p class="pill">QNX Global Hackathon 2026 &middot; <span>{esc(README['category'])}</span></p>
<h1>Port open-source C libraries to QNX&nbsp;8.0, <em>and prove each port on QNX.</em></h1>
<p class="lede">qnx-porter builds a library with QNX's own toolchain, fixes what breaks with reviewable patches,
then runs the library's <em>own</em> test suite on a QNX 8.0 target: x86_64 under KVM, and aarch64 on QEMU.
A port only counts when those tests ran there.</p>
<p class="cta"><a class="btn primary" href="codelab-port-a-library.html">Try the codelab</a>
<a class="btn ghost" href="evidence.html">See the evidence</a></p>
</header>
<div class="tiles">{tiles}</div>

{EVIDENCE_SECTION.format(cards=evidence())}

<section>
<p class="label">Pipeline</p>
<h2 id="how-it-works">How it works</h2>
<p class="intro">The loop for one library, as <a href="{BLOB}/docs/ARCHITECTURE.md">docs/ARCHITECTURE.md</a> walks
through it file by file. A fix stays only if the rebuild or the test re-run proves it.</p>
<figure class="figure"><div class="figscroll">{PIPELINE_SVG}</div>
<figcaption class="cap">Figure 2 &middot; Rules first; the language-model step only where no rule fits, and its diff
is reverted unless the rebuild clears the error. With no usable diff the port stops and reports what is left.</figcaption></figure>
</section>

<section>
<p class="label">Measured against</p>
<h2 id="measured-against">What each claim is checked against</h2>
{measured(reps, cmp_rows)}
<p class="small">Every library with its own result: <a href="evidence.html#coverage">coverage</a>. How to check
these yourself: <a href="evaluate.html">for evaluators</a>.</p>
</section>

<section>
<p class="label">Why</p>
<h2 id="why-c-and-c">Why C and C++</h2>
<div class="prose">
<p><strong>QNX itself is built for C and C++.</strong> QNX OS for Safety 8.0 comes with C and C++ toolchains classified
for ISO 26262 and IEC 61508, and with a certified C library and C++ library
(<a href="https://qnx.software/en/software/products-and-solutions/qnx-os-and-os-for-safety">QNX OS for Safety 8.0</a>,
<a href="https://qnx.software/en/software/technologies/safety-certified/certified-tools">certified tools</a>,
<a href="https://qnx.software/content/dam/qnx-xwalk/pdf/product-briefs/qnx-os-for-safety-product-brief.pdf">product brief</a>).
The OS's own interfaces, such as the C library, resource managers and message passing, are C APIs.</p>
<p><strong>Other languages stand on C libraries.</strong> Python's <a href="https://docs.python.org/3/library/zlib.html"><code>zlib</code></a>
and <a href="https://docs.python.org/3/library/sqlite3.html"><code>sqlite3</code></a> modules use the zlib and SQLite C libraries,
and <a href="https://pypi.org/project/PyNaCl/">PyNaCl</a> wraps libsodium. In Rust,
<a href="https://crates.io/crates/rusqlite"><code>rusqlite</code></a> links SQLite through
<a href="https://crates.io/crates/libsqlite3-sys"><code>libsqlite3-sys</code></a>, and
<a href="https://crates.io/crates/flate2"><code>flate2</code></a> can use zlib through
<a href="https://crates.io/crates/libz-sys"><code>libz-sys</code></a>. When the C library does not build for QNX,
nothing built on it does. All three are in the campaign:</p>
<ul>{cited}</ul>
</div>
<h2 id="why-a-real-time-os">Why a real-time OS needs this</h2>
<div class="cols">
<div><h3>Nothing builds on the target</h3><p>A QNX system in a car or a robot has no compiler. Every library is cross-compiled with qcc against the SDP sysroot, and most projects ship no QNX toolchain file.</p></div>
<div><h3>The host cannot run what it built</h3><p>"It compiled" proves little. qnx-porter copies the build to a QNX 8.0 target and runs every test there, with ctest's own pass and fail rules.</p></div>
<div><h3>POSIX libc, not glibc</h3><p>The same Linux-isms break library after library: epoll, sockets in libc, <code>isinf</code> in libc, <code>printf("%s", NULL)</code>. Those become rules, written once.</p></div>
<div><h3>Every change is reviewable</h3><p>Automotive, medical and industrial teams review each dependency change. Every fix is a separate patch with its rule, its reason and the error it answers.</p></div>
</div>
</section>

<section>
<p class="label">Related work</p>
<h2 id="related-work">QNX's own ports</h2>
<div class="prose">
<p>QNX keeps hand-made build recipes in <a href="https://github.com/qnx-ports">qnx-ports</a>
(<a href="https://github.com/qnx-ports/build-files">build-files</a>): a person adapts each library and writes its recipe.
qnx-porter generates the port and then tests it. It applies documented rules to the compiler's errors, every change
is a patch with its reason, and a library counts as ported only when its own tests run on a QNX target.</p>
<p>{sum(n for _, _, n in cmp_rows)} of our {t['libs']} libraries also have a qnx-ports recipe, and we compared them
library by library in <a href="{BLOB}/{COMPARISON}">{COMPARISON}</a>. The two sides are not the same experiment:
versions, targets and test coverage differ, so agreement means the same QNX difference was found at the same place,
independently.</p>
</div>
<div class="table-wrap"><table class="table stack"><thead><tr><th>Outcome</th><th>Libraries</th><th>Count</th></tr></thead>
<tbody>{cmp_table}</tbody></table></div>
<p class="small">Source: the summary table of {COMPARISON}. For CMake ports that qnx-ports does not have, qnx-porter
generates recipes in their layout (<a href="{REPO}/tree/main/recipes/build-files">recipes/build-files/</a>). The draft
pull request text is in <a href="{BLOB}/docs/upstream/qnx-ports-build-files-PR.md">docs/upstream/</a>; it has not been sent.</p>
</section>

<section>
<p class="label">Run it</p>
<h2 id="run-it">Try it in 60 seconds</h2>
<p>Without QNX: the loop on a deliberately broken library, with your host compiler.</p>
<pre><code>{esc(README['install'])}
qnx-porter selftest</code></pre>
<p>With QNX SDP 8.0 and a QEMU target (<a href="setup.html">setup</a>, or the <a href="codelab-port-a-library.html">codelab</a>):</p>
<pre><code>{esc(chr(10).join(README['quick']))}</code></pre>
</section>

<section>
<p class="label">Team</p>
<h2 id="team">{esc(README['team'])}</h2>
<ul class="team">{team}</ul>
</section>
"""
    return page("qnx-porter: port C libraries to QNX 8.0", body, "index.html")


EVIDENCE_SECTION = """<section>
<p class="label">Evidence</p>
<h2 id="evidence">Every claim is a line in a committed log</h2>
<p class="intro">Each box is an excerpt read from the file named under it when this site was built. Long paths
are shortened to <code>…/</code> and a backtrace frame drops its address and arguments; nothing else is changed.</p>
<p class="label fig">Figure 1 &middot; one crash, one rule, one model fix, Rust, and aarch64 on QEMU</p>
<div class="evidence">{cards}</div>
</section>"""


def evidence_page(reps: list[dict]) -> str:
    body = f"""<header class="page"><p class="label">Evidence</p><h1>What ran on QNX, and where it is written down</h1>
<p class="lede">Excerpts of the committed logs, the claims with the file behind each, and every library's own
result. All of it is read from the repository when the site is built.</p></header>
{EVIDENCE_SECTION.format(cards=evidence())}
<section>
<p class="label">Measured against</p>
<h2 id="measured-against">What each claim is checked against</h2>
{measured(reps, comparison_summary())}
</section>
<section>
<p class="label">Coverage</p>
<h2 id="coverage">Every library in the campaign, x86_64</h2>
<p class="intro">One square per library, from its <code>report.json</code>. The numbers are its own tests that passed
on QNX 8.0. aarch64 and every patch are on the <a href="results.html">results page</a>.</p>
{coverage(reps)}
</section>"""
    return page("Evidence · qnx-porter", body, "evidence.html")


def evaluate_page(reps: list[dict]) -> str:
    body = f"""<header class="page"><p class="label">For evaluators</p><h1>Check the claims in 15 minutes, without QNX</h1>
<p class="lede">You do not need the QNX SDP to check what this project says. Install it, run its self-test, run its
tests, and recompute every number on this site from the reports in the repository. Reproducing a port on QNX
needs the SDP and a target; that is the <a href="codelab-port-a-library.html">codelab</a>.</p></header>

<section>
<p class="label">Step 1</p>
<h2 id="install">Install and run the self-test</h2>
<pre><code>{esc(README['install'])}
qnx-porter selftest</code></pre>
<p><code>selftest</code> copies a deliberately broken C library that ships inside the package, ports it with your host
compiler instead of QNX's, and exits with 0 only if the library builds and the porter kept the patches it should.
The port it wrote, with its numbered patches, reasons and logs, is in <code>ports-selftest/</code>. Needs Python, git,
CMake and a C compiler.</p>
</section>

<section>
<p class="label">Step 2</p>
<h2 id="tests">Clone it and run its tests</h2>
<pre><code>git clone {REPO} &amp;&amp; cd qnx-porter
python3 -m pip install --user -e ".[test]"
python3 -m pytest -q</code></pre>
<p>The tests need no QNX. Among them, <code>tests/test_codelab.py</code> checks that every output block in the
codelab is a line copied from a committed log.</p>
</section>

<section>
<p class="label">Step 3</p>
<h2 id="recompute">Recompute the numbers from the reports</h2>
<pre><code>python3 scripts/ports_csv.py
git diff --stat results/ports.csv README.md</code></pre>
<p><code>scripts/ports_csv.py</code> reads every <code>ports/*/report.json</code> and <code>ports-aarch64le/*/report.json</code>
(written by the porter on the QNX target) and rewrites <code>results/ports.csv</code> and the README's headline and
table. If the committed files are what the reports say, <code>git diff</code> prints nothing.</p>
<pre><code>python3 -m pip install --user markdown
python3 site/build.py</code></pre>
<p>Builds this site into <code>site/_out/</code>. It reads the same files; no number on it is typed.</p>
</section>

<section>
<p class="label">Step 4</p>
<h2 id="which-file">Which file backs each claim</h2>
{measured(reps, comparison_summary())}
<ul class="files">
<li><b>Every patch:</b> <code>ports/&lt;library&gt;/patches/*.patch</code>, each with its rule, its reason and the compiler error it answers.</li>
<li><b>Tests on QNX:</b> <code>ports/&lt;library&gt;/logs/tests.log</code>, as the target printed them.</li>
<li><b>Crashes:</b> <code>ports/&lt;library&gt;/logs/crashes.log</code>, the gdb backtrace from the core dump.</li>
<li><b>Campaign runs:</b> <a href="{REPO}/tree/main/results/runs">results/runs/</a>, the console log of every campaign.</li>
<li><b>Excerpts of all of these:</b> the <a href="evidence.html">evidence</a> page.</li>
</ul>
</section>

<section>
<p class="label">On QNX</p>
<h2 id="reproduce">Reproduce a port with the SDP</h2>
<p>With QNX SDP 8.0 installed and a QNX 8.0 target in QEMU (<code>scripts/qemu_target.sh</code> builds one with
QNX's <code>mkqnximage</code>; see <a href="setup.html">setup</a>):</p>
<pre><code>{esc(chr(10).join(README['quick']))}
python3 scripts/run_campaign.py</code></pre>
<p>The <a href="codelab-port-a-library.html">codelab</a> walks through one port step by step, with the output you
should see. Both targets are QEMU: x86_64 under KVM, and aarch64 on QEMU <code>virt</code>. No hardware was used;
what is missing is in <a href="{RENDERED.get('docs/LIMITATIONS.md', BLOB + '/docs/LIMITATIONS.md')}">limitations</a>.</p>
</section>"""
    return page("For evaluators · qnx-porter", body, "evaluate.html")


def paper_page() -> str:
    pdf = ROOT / "paper" / "qnx-porter.pdf"
    link = ""
    if pdf.exists():
        (OUT / "paper").mkdir(exist_ok=True)
        shutil.copy(pdf, OUT / "paper" / pdf.name)
        link = f'<p class="cta"><a class="btn primary" href="paper/{pdf.name}">Download the PDF</a></p>'
    if (ROOT / "paper" / "paper.md").exists():
        title, body, desc = md_html("paper/paper.md")
        return page(f"{title} · qnx-porter", f'<p class="label">Paper</p>{link}<div class="prose doc">{body}</div>',
                    "paper.html", desc=desc[:300])
    body = f"""<header class="page"><p class="label">Paper</p><h1>The paper is in preparation</h1>
<p class="lede">A write-up of the method and the results is being written. Until it is published here, the
<a href="evidence.html">evidence</a>, the <a href="docs.html">docs</a> and the <a href="results.html">results</a>
hold everything it will draw on.</p>{link}</header>"""
    return page("Paper · qnx-porter", body, "paper.html")


FILTER_JS = """
<script>
document.getElementById('q').addEventListener('input', function (e) {
  var q = e.target.value.toLowerCase();
  document.querySelectorAll('#t tbody tr').forEach(function (tr) { tr.hidden = tr.dataset.q.indexOf(q) < 0; });
});
</script>"""


def results(reps: list[dict]) -> str:
    listed = oss_listed()
    rows = []
    for r in reps:
        build = ('<span class="ok">built</span>' if r["build_result"] == "built" else
                 f'<span class="{"warn" if r["build_result"] == "needs-qnx-equivalent" else "bad"}">{esc(status_text(r))}</span>')
        on = "yes" if r["library"] in listed else "—"
        rows.append(f'<tr data-q="{esc((r["library"] + " " + r["arch"]).lower())}"><td><a href="ports/{esc(r["_slug"])}.html">{esc(r["library"])}</a></td>'
                    f'<td>{esc(r["version"])}</td><td>{ARCH_LABEL.get(r["arch"], r["arch"])}</td><td>{esc(r["build_system"])}</td>'
                    f'<td>{build}</td><td>{tests_cell(r)}</td><td class="num">{r["patches_kept"]}</td>'
                    f'<td class="num">{r["rounds"]}</td><td>{on}</td></tr>')
    arches = sorted({r["arch"] for r in reps}, key=lambda a: (a != "x86_64", a))
    stats = "".join(
        tile(f'{t["built"]}/{t["libs"]}', f'built for QNX 8.0 {ARCH_LABEL.get(a, a)}', f"{d}/*/report.json")
        + tile(f'{t["passed"]}/{t["total"]}', f'of their own tests passed on {ARCH_LABEL.get(a, a)} ({t["with_tests"]} libraries with tests that ran)')
        for a in arches for t in [totals(reps, a)] for d in [PORT_DIRS[0] if a == "x86_64" else f"ports-{a}"])
    dirs = [d for d in PORT_DIRS if (ROOT / d).is_dir()]
    body = f"""<header class="page"><p class="label">Results</p><h1>Every port, read from its report</h1>
<p class="lede">Every library the campaign ported, read from its <code>report.json</code>. Tests ran on QNX 8.0 in QEMU
(<code>mkqnximage</code>): x86_64 under KVM, and aarch64 on QEMU <code>virt</code>. "On oss.qnx.com" marks libraries
QNX's own ports site already lists.</p></header>
<div class="tiles">{stats}</div>
<h2 id="all-ports">All ports</h2>
<p><input type="search" id="q" placeholder="Filter by library or arch" aria-label="Filter by library or arch"></p>
<div class="table-wrap scroll"><table class="table data" id="t"><thead><tr><th>Library</th><th>Version</th><th>Arch</th><th>Build system</th><th>Build</th>
<th>Tests on QNX</th><th>Patches</th><th>Rounds</th><th>On oss.qnx.com</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="small">Source: results/ports.csv and {' and '.join(d + '/*/report.json' for d in dirs)} in the repository.</p>{FILTER_JS}"""
    return page("Results · qnx-porter", body, "results.html")


HISTORY = "results/head/history.csv"  # written weekly by scripts/head_history.py on branch data/head-history


def upstream() -> str:
    f = ROOT / HISTORY
    rows = list(csv.DictReader(f.open(encoding="utf-8"))) if f.exists() else []
    intro = f"""<header class="page"><p class="label">Weekly check</p><h1>Weekly upstream check</h1>
<p class="lede">Every Monday, <a href="{BLOB}/.github/workflows/weekly-head.yml">a scheduled workflow</a> ports every
library in the campaign again, at its upstream default branch (HEAD) instead of the pinned tag: build only, rules only.
It shows when an upstream change breaks the QNX 8.0 build, and whether the rules still cover it.</p></header>"""
    if not rows:
        return page("Weekly upstream check · qnx-porter", intro + f"""
<h2 id="history">History</h2>
<p>No weekly run is recorded yet. The workflow appends to <code>{HISTORY}</code> on the
<a href="{REPO}/tree/data/head-history"><code>data/head-history</code></a> branch, and this page shows it from the next
site build on.</p>""", "upstream.html")
    rows.sort(key=lambda r: r["library"].lower())
    rows.sort(key=lambda r: r["run"], reverse=True)  # newest run first, libraries A to Z within a run
    last = [r for r in rows if r["run"] == rows[0]["run"]]
    built = sum(r["build_result"] == "built" for r in last)
    trs = "".join(
        f'<tr data-q="{esc((r["library"] + " " + r["run"] + " " + r["build_result"]).lower())}"><td>{esc(r["run"])}</td>'
        f'<td>{esc(r["library"])}</td><td>{esc(r["branch"])}</td><td><code>{esc(r["commit"])}</code></td>'
        f'<td>{ARCH_LABEL.get(r["arch"], esc(r["arch"]))}</td>'
        f'<td><span class="{"ok" if r["build_result"] == "built" else "bad"}">{esc(r["build_result"])}</span></td>'
        f'<td class="num">{esc(r["patches"])}</td></tr>' for r in rows)
    runs = len({r["run"] for r in rows})
    body = intro + f"""
<div class="tiles">{tile(f"{built}/{len(last)}", f"libraries built at upstream HEAD in the latest run ({esc(rows[0]['run'])})", HISTORY)}
{tile(runs, "run(s) recorded")}</div>
<h2 id="history">History</h2>
<p><input type="search" id="q" placeholder="Filter by library, date or result" aria-label="Filter by library, date or result"></p>
<div class="table-wrap scroll"><table class="table data" id="t"><thead><tr><th>Run</th><th>Library</th><th>Branch</th><th>Commit</th><th>Arch</th>
<th>Result</th><th>Patches</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class="small">Source: {HISTORY} on the data/head-history branch.</p>{FILTER_JS}"""
    return page("Weekly upstream check · qnx-porter", body, "upstream.html")


def diff_html(text: str) -> str:
    out = []
    for ln in text.splitlines():
        cls = "add" if ln.startswith("+") and not ln.startswith("+++") else \
            "del" if ln.startswith("-") and not ln.startswith("---") else "hunk" if ln.startswith("@@") else ""
        out.append(f'<span class="{cls}">{esc(ln)}</span>' if cls else esc(ln))
    return '<pre class="diff"><code>' + "\n".join(out) + "</code></pre>"


def port_page(r: dict) -> str:
    d: Path = r["_dir"]
    rel = d.relative_to(ROOT).as_posix()
    patches = []
    for p in r["patches"]:
        f = d / p["path"]
        text = f.read_text(encoding="utf-8", errors="replace") if f.exists() else ""
        status = '<span class="ok badge">kept</span>' if p["kept"] else '<span class="bad badge">reverted</span>'
        patches.append(f'<h3>{p["number"]:04d} · {esc(p["rule"])} {status}</h3><p>{esc(p["reason"])}</p>'
                       f'<p class="small mono">Error: {esc(p["error"][:300])}</p>{diff_html(text.split(chr(10) + "---" + chr(10), 1)[-1][:6000])}')
    tests_log = d / "logs" / "tests.log"
    tail = ""
    if tests_log.exists():
        lines = tests_log.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = (f'<h2>Tests on the QNX target</h2><pre><code>{esc(chr(10).join(lines[:3] + ["…"] + lines[-12:]))}</code></pre>'
                f'<p class="small mono"><a href="{BLOB}/{rel}/logs/tests.log">{rel}/logs/tests.log</a></p>')
    crashes = "".join(f'<h3>Crash: {esc(c["binary"])}</h3><pre><code>{esc(c["backtrace"])}</code></pre>' for c in r.get("crashes", []))
    blocked = "".join(f"<li><code>{esc(b['error'][:300])}</code>{(' — ' + esc(b['hint'])) if b.get('hint') else ''}</li>"
                      for b in r.get("blocked_on", []))
    body = f"""<header class="page"><p class="label"><a href="../results.html">Results</a> / {esc(r['library'])}</p>
<h1>{esc(r['library'])} <span class="label">{esc(r['version'])} · {ARCH_LABEL.get(r['arch'], r['arch'])}</span></h1></header>
<div class="tiles metrics">
{tile('built' if r['build_result'] == 'built' else 'Linux-only' if r.get('linux_interfaces') else esc(r['build_result']),
       ('needs a QNX equivalent (below); ' if r.get('linux_interfaces') else '') + f"after {r['rounds']} round(s), {esc(r['build_system'])}")}
{tile(tests_cell(r), "its own tests on QNX 8.0")}
{tile(r['patches_kept'], f"patches kept ({r['patches_by_rule']} rule, {r['patches_by_model']} model)")}
{tile(r['minutes'], "minutes, end to end")}</div>
<p>Upstream: <a href="{esc(r['url'])}">{esc(r['url'])}</a> at <code>{esc(r['version'])}</code> (<code>{esc(r['commit'][:12])}</code>).
Target: <code>{esc(r.get('target') or 'no target')}</code>.
Files: <a href="{BLOB}/{rel}/REPORT.md">REPORT.md</a> · <a href="{BLOB}/{rel}/qnx.patch">qnx.patch</a> ·
<a href="{BLOB}/{rel}/report.json">report.json</a> · <a href="{REPO}/tree/main/{rel}/logs">logs</a></p>
{advice(r)}<h2>Patches</h2>{''.join(patches) or '<p>No changes needed: the library built for QNX as it is.</p>'}
{tail}{('<h2>Crashes</h2>' + crashes) if crashes else ''}{('<h2>Still failing</h2><ul>' + blocked + '</ul>') if blocked else ''}"""
    return page(f"{r['library']} on QNX 8.0 · qnx-porter", body, "results.html", depth=1)


def advice(r: dict) -> str:
    """The porting advisor's table: each Linux-only interface the library uses and QNX's equivalent."""
    a = r.get("linux_interfaces")
    if not a:
        return ""
    rows = "".join(f"<tr><td>{esc(u['interface'])}</td><td>{u['files']} (first: <code>{esc(u['first'])}</code>)</td>"
                   f"<td>{esc(u['qnx'])}</td><td><a href=\"{esc(u['docs'])}\">QNX docs</a></td></tr>" for u in a["interfaces"])
    return (f"<h2>Not portable as-is: needs a QNX equivalent</h2><p>The build stopped on <code>&lt;{esc(a['stopped_on'])}&gt;</code>, "
            "a Linux kernel header. The sources use Linux-only kernel interfaces that QNX 8.0 provides differently; the code "
            "that uses them needs a QNX back end.</p><div class=\"table-wrap\"><table class=\"table\"><thead><tr><th>Linux interface</th>"
            f"<th>Files</th><th>QNX equivalent</th><th></th></tr></thead><tbody>{rows}</tbody></table></div>")


def gh_slug(value: str, separator: str = "-") -> str:
    """Heading ids as GitHub makes them, so the docs' own #anchors keep working."""
    return re.sub(r"[^\w\- ]", "", html.unescape(value).strip().lower()).replace(" ", separator)


def relink(body: str, src: str, out: str) -> str:
    """Repo-relative links: to the rendered page if there is one, else to GitHub at main. Local images are copied."""
    up, base = "../" * out.count("/"), posixpath.dirname(src)

    def fix(m):
        attr, url = m[1], html.unescape(m[2])
        if url.startswith(BLOB + "/"):
            path, _, frag = url[len(BLOB) + 1:].partition("#")
        elif re.match(r"^([a-z][a-z0-9+.-]*:|#|//)", url) or not url:
            return m[0]
        else:
            rel, _, frag = url.partition("#")
            path = posixpath.normpath(posixpath.join(base, rel)) if rel else src
        if path.startswith(".."):
            return m[0]
        if path == src and frag:
            new = "#" + frag
        elif path in RENDERED:
            new = up + RENDERED[path] + (f"#{frag}" if frag else "")
        elif attr == "src" and (ROOT / path).is_file():
            (OUT / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / path, OUT / path)
            new = up + path
        else:
            new = f"{REPO}/{'tree' if (ROOT / path).is_dir() else 'blob'}/main/{path}" + (f"#{frag}" if frag else "")
        return f'{attr}="{esc(new)}"'

    return re.sub(r'\b(href|src)="([^"]*)"', fix, body)


def md_html(src: str) -> tuple[str, str, str]:
    """(title, body html, description) of a markdown file, links fixed for where it is rendered."""
    text = read(src)
    facts, desc = "", ""
    if text.startswith("id: "):  # a QNX codelab (claat format): metadata lines, then the H1
        meta, text = text.split("\n# ", 1)
        meta, text = dict(re.findall(r"^(\w+): (.*)$", meta, re.M)), "# " + text
        mins = sum(int(m) * 60 + int(s) for m, s in re.findall(r"^Duration: (\d+):(\d\d)$", text, re.M)) // 60
        facts = (f'<p class="label">QNX codelab · {mins} minutes in all (the sum of the steps) · '
                 f'{esc(meta.get("tags", ""))}</p>')
        desc = meta.get("summary", "")
    m = re.search(r"^# (.+)$", text, re.M)
    title = re.sub(r"[`*]", "", m[1]).strip() if m else Path(src).stem
    if not desc:  # the first paragraph after the title, as plain text
        para = next((p for p in re.split(r"\n\s*\n", text.split(m[0], 1)[-1] if m else text)
                     if p.strip() and not p.lstrip().startswith(("#", "|", "```", "-", "<", "!"))), "")
        desc = re.sub(r"\s+", " ", re.sub(r"\[([^\]]*)\]\([^)]*\)|[`*]", lambda x: x[1] or "", para)).strip()
    body = markdown.markdown(text, extensions=["tables", "fenced_code", "toc"],
                             extension_configs={"toc": {"slugify": gh_slug}})
    body = body.replace("<table>", '<div class="table-wrap scroll"><table class="table">').replace("</table>", "</table></div>")
    body = re.sub(r"<p>Duration: ([\d:]+)</p>", r'<p class="label">Duration: \1</p>', body)
    body = re.sub(r"(<h1[^>]*>.*?</h1>)", lambda x: x[1] + facts, body, count=1, flags=re.S)
    return title, relink(body, src, out_path(src)), desc


def md_page(src: str, current: str = "docs.html") -> str:
    title, body, desc = md_html(src)
    out = out_path(src)
    crumb = f'<p class="label"><a href="{"../" * out.count("/")}docs.html">Docs</a> / <a href="{BLOB}/{src}">{esc(src)}</a></p>'
    return page(f"{title} · qnx-porter", f'{crumb}<div class="prose doc">{body}</div>', current,
                depth=out.count("/"), desc=desc[:300])


def docs_index() -> str:
    groups = []
    for g, files in doc_files():
        cards = []
        for f in files:
            title, _, desc = md_html(f)
            short = desc if len(desc) <= 180 else desc[:180].rsplit(" ", 1)[0] + " …"
            cards.append(f'<a class="doc-card" href="{RENDERED[f]}"><span class="label">{esc(f)}</span>'
                         f'<h3>{esc(title)}</h3><p>{esc(short)}</p></a>')
        groups.append(f'<section><h2>{esc(g)}</h2><div class="doc-cards">{"".join(cards)}</div></section>')
    body = f"""<header class="page"><p class="label">Docs</p><h1>Documentation</h1>
<p class="lede">Every page here is rendered from a markdown file in the repository when the site is built, so it
says what the repository says. The file's path is above each title.</p></header>{''.join(groups)}"""
    return page("Docs · qnx-porter", body, "docs.html")


def main() -> int:
    reps = load_reports()
    if not reps:
        print("no ports/*/report.json found", file=sys.stderr)
        return 1
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "ports").mkdir(parents=True)
    shutil.copy(ROOT / "site" / "style.css", OUT / "style.css")
    (OUT / "index.html").write_text(index(reps), encoding="utf-8")
    (OUT / "results.html").write_text(results(reps), encoding="utf-8")
    for r in reps:
        (OUT / "ports" / f"{r['_slug']}.html").write_text(port_page(r), encoding="utf-8")
    (OUT / "upstream.html").write_text(upstream(), encoding="utf-8")
    (OUT / "evidence.html").write_text(evidence_page(reps), encoding="utf-8")
    (OUT / "evaluate.html").write_text(evaluate_page(reps), encoding="utf-8")
    (OUT / "paper.html").write_text(paper_page(), encoding="utf-8")
    (OUT / "docs.html").write_text(docs_index(), encoding="utf-8")
    current = {"codelab-port-a-library.html": "codelab-port-a-library.html", "setup.html": "setup.html"}
    for src, out in RENDERED.items():
        if src != "paper/paper.md":
            (OUT / out).parent.mkdir(parents=True, exist_ok=True)
            (OUT / out).write_text(md_page(src, current.get(out, "docs.html")), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    t = totals(reps, "x86_64")
    print(f"site: {len(reps)} ports, {t['built']}/{t['libs']} built, {t['passed']}/{t['total']} tests -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
