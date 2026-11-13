"""Build the project website from the repository: results, ports, rules and docs. Nothing is typed twice.

Every number on the site is read from ports/*/report.json (written by the porter on a QNX target) or from
results/*.csv (written by scripts/ports_csv.py). Pages: landing, results dashboard, one page per port, the
weekly upstream check, the codelabs, the rule corpus and setup. Output: site/_out/ (published to GitHub Pages by CI).

Usage: python site/build.py   (needs Python-Markdown: pip install markdown)
"""
import csv
import html
import json
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
NAV = [("index.html", "Overview"), ("results.html", "Results"), ("upstream.html", "Weekly check"),
       ("rules.html", "Rules"), ("codelab-port-a-library.html", "Codelab"), ("setup.html", "Setup"), (REPO, "GitHub")]


def esc(s) -> str:
    return html.escape(str(s), quote=True)


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


def page(title: str, body: str, current: str, depth: int = 0, desc: str = "") -> str:
    up = "../" * depth
    nav = "".join(f'<a href="{h if h.startswith("http") else up + h}"'
                  f'{" aria-current=page" if h == current else ""}>{esc(t)}</a>' for h, t in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title><meta name="description" content="{esc(desc or 'qnx-porter ports open-source C/C++ libraries to QNX 8.0 and proves each port on a QNX target.')}">
<link rel="stylesheet" href="{up}style.css"></head><body>
<header class="top"><div class="wrap"><a class="brand" href="{up}index.html">qnx-porter</a>
<span class="docno">Porting report · QNX 8.0</span><nav>{nav}</nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap"><span>Apache-2.0 · built from the repository by CI, every number from a run on QNX 8.0</span>
<a href="{REPO}">{REPO.removeprefix('https://')}</a><span>No cookies, no trackers, no external fonts or scripts.</span></div></footer>
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


PIPELINE_SVG = """<svg viewBox="0 0 1060 210" role="img" aria-label="Pipeline: git URL, detect build system, QNX toolchain, build with qcc, read errors, rules then model, rebuild, tests on a QNX target, report">
<style>.b{fill:var(--card);stroke:var(--rule-strong);stroke-width:1.5}.t{font:600 14px var(--sans);fill:var(--ink)}.s{font:12px var(--mono);fill:var(--muted)}.a{stroke:var(--ink);stroke-width:1.5;fill:none;marker-end:url(#h)}.l{stroke:var(--signal);stroke-width:2;fill:none;marker-end:url(#hs)}</style>
<defs><marker id="h" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--ink)"/></marker>
<marker id="hs" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0L10 5L0 10z" fill="var(--signal)"/></marker></defs>
<rect class="b" x="5" y="30" width="140" height="64"/><text class="t" x="18" y="58">git URL + tag</text><text class="s" x="18" y="79">any C/C++ library</text>
<rect class="b" x="185" y="30" width="160" height="64"/><text class="t" x="198" y="58">QNX toolchain</text><text class="s" x="198" y="79">qcc + sysroot</text>
<rect class="b" x="385" y="30" width="150" height="64"/><text class="t" x="398" y="58">build + parse</text><text class="s" x="398" y="79">GCC, ld, CMake</text>
<rect class="b" x="575" y="30" width="160" height="64"/><text class="t" x="588" y="58">tests on QNX 8.0</text><text class="s" x="588" y="79">run on the target</text>
<rect class="b" x="775" y="30" width="130" height="64"/><text class="t" x="788" y="58">core dumps</text><text class="s" x="788" y="79">gdb backtrace</text>
<rect class="b" x="945" y="30" width="110" height="64"/><text class="t" x="958" y="58">report</text><text class="s" x="958" y="79">patches, logs</text>
<path class="a" d="M145 62H183"/><path class="a" d="M345 62H383"/><path class="a" d="M535 62H573"/><path class="a" d="M735 62H773"/><path class="a" d="M905 62H943"/>
<rect class="b" x="385" y="132" width="420" height="56"/><text class="t" x="398" y="157">fix: deterministic rules first, a model for the rest</text><text class="s" x="398" y="176">a patch + reason; kept only if proven</text>
<path class="l" d="M460 94V130"/><path class="l" d="M520 130V96"/><path class="l" d="M655 94V130"/><path class="l" d="M840 94C840 160 830 160 807 160"/>
</svg>"""


COMPARISON = "docs/related/qnx-ports-comparison.md"


def comparison_summary() -> list[tuple[str, str, int]]:
    """The (outcome, libraries, count) rows of the Summary table in the qnx-ports comparison."""
    text = (ROOT / COMPARISON).read_text(encoding="utf-8")
    summary = text.split("## Summary", 1)[1].split("\n## ", 1)[0]
    rows = [(o.strip(), libs.strip(), int(n)) for o, libs, n in re.findall(r"^\|([^|]+)\|([^|]+)\|\s*(\d+)\s*\|$", summary, re.M)]
    if not rows:
        raise SystemExit(f"no summary table found in {COMPARISON}")
    return rows


def lib_line(reps: list[dict], name: str) -> str:
    """One line on a campaign library, from its x86_64 report."""
    r = next(r for r in reps if r["library"] == name and r["arch"] == "x86_64")
    link = f'<a href="ports/{esc(r["_slug"])}.html">{esc(name)}</a>'
    if r["build_result"] != "built":
        return f"<li>{link}: {esc(r['build_result'])}.</li>"
    if r.get("tests_ran") and r["tests_total"]:
        return f"<li>{link}: built, {r['tests_passed']}/{r['tests_total']} of its own tests pass on QNX 8.0.</li>"
    return f"<li>{link}: built; tests not run{(' (' + esc(r['note']) + ')') if r.get('note') else ''}.</li>"


def index(reps: list[dict]) -> str:
    t = totals(reps, "x86_64")
    a64 = totals(reps, "aarch64le")
    rules = len(re.findall(r"^\| \d+[a-z]? \|", (ROOT / "docs" / "LINUX_ISMS.md").read_text(encoding="utf-8"), re.M))
    a64_stat = (f'<div class="stat"><div class="n">{a64["built"]}/{a64["libs"]}</div><div class="t">also built for aarch64; '
                f'{a64["passed"]}/{a64["total"]} of their tests passed</div></div>' if a64["libs"] else "")
    cmp_rows = comparison_summary()
    cmp_table = "".join(f'<tr><td>{esc(o)}</td><td>{esc(libs)}</td><td class="num">{n}</td></tr>' for o, libs, n in cmp_rows)
    cited = "".join(lib_line(reps, n) for n in ("zlib", "libsodium", "sqlite"))
    body = f"""
<p class="label">Developer tool · QNX Global Hackathon 2026</p>
<h1>Port open-source C libraries to QNX 8.0, and prove each port on QNX.</h1>
<p class="lead">qnx-porter builds a library with QNX's own toolchain, fixes what breaks with reviewable patches,
then runs the library's <em>own</em> test suite on a QNX 8.0 target. A port only counts when those tests ran there.</p>
<p><a class="btn" href="results.html">See every port</a> <a class="btn ghost" href="codelab-port-a-library.html">Codelab: port a
CMake C library to QNX 8.0 and run its tests on QEMU</a></p>
<div class="stats">
<div class="stat"><div class="n">{t['built']}/{t['libs']}</div><div class="t">libraries built for QNX 8.0 x86_64</div></div>
<div class="stat"><div class="n">{t['passed']}/{t['total']}</div><div class="t">of their own tests passed on the QNX target ({t['with_tests']} libraries)</div></div>
<div class="stat"><div class="n">{t['patches']}</div><div class="t">patches, {t['by_rule']} by deterministic rules, {t['by_model']} by the model</div></div>
<div class="stat"><div class="n">{rules}</div><div class="t">Linux-isms in the rule corpus, each with a test</div></div>
{a64_stat}</div>
<h2>Why C and C++</h2>
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
<h2>Why a real-time OS needs this</h2>
<div class="cards">
<div class="card"><h3>Nothing builds on the target</h3><p>A QNX system in a car or a robot has no compiler. Every library is cross-compiled with qcc against the SDP sysroot, and most projects ship no QNX toolchain file.</p></div>
<div class="card"><h3>The host cannot run what it built</h3><p>"It compiled" proves little. qnx-porter copies the build to a QNX 8.0 target and runs every test there, with ctest's own pass and fail rules.</p></div>
<div class="card"><h3>POSIX libc, not glibc</h3><p>The same Linux-isms break library after library: epoll, sockets in libc, <code>isinf</code> in libc, <code>printf("%s", NULL)</code>. Those become rules, written once.</p></div>
<div class="card"><h3>Every change is reviewable</h3><p>Automotive, medical and industrial teams review each dependency change. Every fix is a separate patch with its rule, its reason and the error it answers.</p></div>
</div>
<h2>How it works</h2>
<figure>{PIPELINE_SVG}<figcaption>Fig. 1 — The porting loop. Orange: the fix loop; a fix stays only if the rebuild or the test re-run proves it.</figcaption></figure>
<h2>Related work: QNX's own ports</h2>
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
<div class="scroll"><table class="wrap"><thead><tr><th>Outcome</th><th>Libraries</th><th>Count</th></tr></thead>
<tbody>{cmp_table}</tbody></table></div>
<p class="label">Source: the summary table of {COMPARISON}.</p>
<p>For CMake ports that qnx-ports does not have, qnx-porter generates recipes in their layout
(<a href="{REPO}/tree/main/recipes/build-files">recipes/build-files/</a>). The draft pull request text is in
<a href="{BLOB}/docs/upstream/qnx-ports-build-files-PR.md">docs/upstream/</a>; it has not been sent.</p>
<h2>Try it in 60 seconds</h2>
<p>Without QNX: the loop on a deliberately broken library, with your host compiler.</p>
<pre><code>git clone {REPO} &amp;&amp; cd qnx-porter
python3 -m pip install -e .
qnx-porter selftest</code></pre>
<p>With QNX SDP 8.0 and a QEMU target (<a href="setup.html">setup</a>):</p>
<pre><code>source ~/qnx800/qnxsdp-env.sh
qnx-porter port https://github.com/json-c/json-c.git --target root@172.31.1.11</code></pre>
"""
    return page("qnx-porter: port C libraries to QNX 8.0", body, "index.html")


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
        build = '<span class="ok">built</span>' if r["build_result"] == "built" else f'<span class="bad">{esc(r["build_result"])}</span>'
        on = "yes" if r["library"] in listed else "—"
        rows.append(f'<tr data-q="{esc((r["library"] + " " + r["arch"]).lower())}"><td><a href="ports/{esc(r["_slug"])}.html">{esc(r["library"])}</a></td>'
                    f'<td>{esc(r["version"])}</td><td>{ARCH_LABEL.get(r["arch"], r["arch"])}</td><td>{esc(r["build_system"])}</td>'
                    f'<td>{build}</td><td>{tests_cell(r)}</td><td class="num">{r["patches_kept"]}</td>'
                    f'<td class="num">{r["rounds"]}</td><td>{on}</td></tr>')
    arches = sorted({r["arch"] for r in reps}, key=lambda a: (a != "x86_64", a))
    stats = "".join(
        f'<div class="stat"><div class="n">{t["built"]}/{t["libs"]}</div><div class="t">built for QNX 8.0 {ARCH_LABEL.get(a, a)}; '
        f'{t["passed"]}/{t["total"]} of their own tests passed ({t["with_tests"]} libraries with tests that ran)</div></div>'
        for a in arches for t in [totals(reps, a)])
    dirs = [d for d in PORT_DIRS if (ROOT / d).is_dir()]
    body = f"""<h1>Results</h1>
<p class="lead">Every library the campaign ported, read from its <code>report.json</code>. Tests ran on QNX 8.0 in QEMU
(<code>mkqnximage</code>). "On oss.qnx.com" marks libraries QNX's own ports site already lists.</p>
<div class="stats">{stats}</div>
<p><input type="search" id="q" placeholder="Filter by library or arch" aria-label="Filter"></p>
<div class="scroll"><table id="t"><thead><tr><th>Library</th><th>Version</th><th>Arch</th><th>Build system</th><th>Build</th>
<th>Tests on QNX</th><th>Patches</th><th>Rounds</th><th>On oss.qnx.com</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="label">Source: results/ports.csv and {' and '.join(d + '/*/report.json' for d in dirs)} in the repository.</p>{FILTER_JS}"""
    return page("Results · qnx-porter", body, "results.html")


HISTORY = "results/head/history.csv"  # written weekly by scripts/head_history.py on branch data/head-history


def upstream() -> str:
    f = ROOT / HISTORY
    rows = list(csv.DictReader(f.open(encoding="utf-8"))) if f.exists() else []
    intro = f"""<h1>Weekly upstream check</h1>
<p class="lead">Every Monday, <a href="{BLOB}/.github/workflows/weekly-head.yml">a scheduled workflow</a> ports every
library in the campaign again, at its upstream default branch (HEAD) instead of the pinned tag: build only, rules only.
It shows when an upstream change breaks the QNX 8.0 build, and whether the rules still cover it.</p>"""
    if not rows:
        return page("Weekly upstream check · qnx-porter", intro + f"""
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
<div class="stats"><div class="stat"><div class="n">{built}/{len(last)}</div><div class="t">libraries built at upstream HEAD
in the latest run ({esc(rows[0]["run"])})</div></div><div class="stat"><div class="n">{runs}</div><div class="t">run(s) recorded</div></div></div>
<p><input type="search" id="q" placeholder="Filter by library, date or result" aria-label="Filter"></p>
<div class="scroll"><table id="t"><thead><tr><th>Run</th><th>Library</th><th>Branch</th><th>Commit</th><th>Arch</th>
<th>Result</th><th>Patches</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class="label">Source: {HISTORY} on the data/head-history branch.</p>{FILTER_JS}"""
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
                       f'<p class="label">Error: {esc(p["error"][:300])}</p>{diff_html(text.split(chr(10) + "---" + chr(10), 1)[-1][:6000])}')
    tests_log = d / "logs" / "tests.log"
    tail = ""
    if tests_log.exists():
        lines = tests_log.read_text(encoding="utf-8", errors="replace").splitlines()
        tail = "<h2>Tests on the QNX target</h2><pre><code>" + esc("\n".join(lines[:3] + ["…"] + lines[-12:])) + "</code></pre>"
    crashes = "".join(f'<h3>Crash: {esc(c["binary"])}</h3><pre><code>{esc(c["backtrace"])}</code></pre>' for c in r.get("crashes", []))
    blocked = "".join(f"<li><code>{esc(b['error'][:300])}</code>{(' — ' + esc(b['hint'])) if b.get('hint') else ''}</li>"
                      for b in r.get("blocked_on", []))
    body = f"""<p class="label"><a href="../results.html">Results</a> / {esc(r['library'])}</p>
<h1>{esc(r['library'])} <span class="label">{esc(r['version'])} · {ARCH_LABEL.get(r['arch'], r['arch'])}</span></h1>
<div class="stats">
<div class="stat"><div class="n">{'built' if r['build_result'] == 'built' else esc(r['build_result'])}</div><div class="t">after {r['rounds']} round(s), {esc(r['build_system'])}</div></div>
<div class="stat"><div class="n">{tests_cell(r)}</div><div class="t">its own tests on QNX 8.0</div></div>
<div class="stat"><div class="n">{r['patches_kept']}</div><div class="t">patches kept ({r['patches_by_rule']} rule, {r['patches_by_model']} model)</div></div>
<div class="stat"><div class="n">{r['minutes']}</div><div class="t">minutes, end to end</div></div></div>
<p>Upstream: <a href="{esc(r['url'])}">{esc(r['url'])}</a> at <code>{esc(r['version'])}</code> (<code>{esc(r['commit'][:12])}</code>).
Target: <code>{esc(r.get('target') or 'no target')}</code>.
Files: <a href="{BLOB}/{rel}/REPORT.md">REPORT.md</a> · <a href="{BLOB}/{rel}/qnx.patch">qnx.patch</a> ·
<a href="{BLOB}/{rel}/report.json">report.json</a> · <a href="{REPO}/tree/main/{rel}/logs">logs</a></p>
<h2>Patches</h2>{''.join(patches) or '<p>No changes needed: the library built for QNX as it is.</p>'}
{tail}{crashes}{('<h2>Still failing</h2><ul>' + blocked + '</ul>') if blocked else ''}"""
    return page(f"{r['library']} on QNX 8.0 · qnx-porter", body, "results.html", depth=1)


def md_page(src: str, title: str, current: str, desc: str = "") -> str:
    text = (ROOT / src).read_text(encoding="utf-8")
    facts = ""
    if text.startswith("id: "):  # a QNX codelab (claat format): metadata lines, then the H1
        meta, text = text.split("\n# ", 1)
        meta, text = dict(re.findall(r"^(\w+): (.*)$", meta, re.M)), "# " + text
        mins = sum(int(m) * 60 + int(s) for m, s in re.findall(r"^Duration: (\d+):(\d\d)$", text, re.M)) // 60
        facts = (f'<p class="label">QNX codelab · {mins} minutes in all (the sum of the steps) · '
                 f'{esc(meta.get("tags", ""))}</p>')
        desc = desc or meta.get("summary", "")
    text = text.replace(f"{BLOB}/docs/CODELAB.md", "codelab.html").replace(f"{BLOB}/SETUP.md", "setup.html")
    text = re.sub(r"\]\(\.\./SETUP\.md\)", "](setup.html)", text)
    text = re.sub(r"\]\((?:docs/)?codelab/port-a-library\.md\)", "](codelab-port-a-library.html)", text)
    text = re.sub(r"\]\((?:docs/)?LINUX_ISMS\.md\)", "](rules.html)", text)
    text = re.sub(r"\]\((?:docs/)?CODELAB\.md\)", "](codelab.html)", text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    body = body.replace("<table>", '<div class="scroll"><table>').replace("</table>", "</table></div>")
    body = re.sub(r"<p>Duration: ([\d:]+)</p>", r'<p class="label">Duration: \1</p>', body).replace("</h1>", "</h1>" + facts, 1)
    return page(f"{title} · qnx-porter", f'<div class="prose">{body}</div>', current, desc=desc)


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
    (OUT / "codelab.html").write_text(md_page("docs/CODELAB.md", "Codelab (full reference)", "codelab-port-a-library.html"), encoding="utf-8")
    (OUT / "codelab-port-a-library.html").write_text(md_page(
        "docs/codelab/port-a-library.md", "Codelab: port a CMake C library to QNX 8.0", "codelab-port-a-library.html"), encoding="utf-8")
    (OUT / "rules.html").write_text(md_page("docs/LINUX_ISMS.md", "Rules", "rules.html"), encoding="utf-8")
    (OUT / "setup.html").write_text(md_page("SETUP.md", "Setup", "setup.html"), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    t = totals(reps, "x86_64")
    print(f"site: {len(reps)} ports, {t['built']}/{t['libs']} built, {t['passed']}/{t['total']} tests -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
