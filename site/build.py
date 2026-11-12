"""Build the project website from the repository: results, ports, rules and docs. Nothing is typed twice.

Every number on the site is read from ports/*/report.json (written by the porter on a QNX target) or from
results/*.csv (written by scripts/ports_csv.py). Pages: landing, results dashboard, one page per port, the
codelab, the rule corpus and setup. Output: site/_out/ (published to GitHub Pages by CI).

Usage: python site/build.py   (needs Python-Markdown: pip install markdown)
"""
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
NAV = [("index.html", "Overview"), ("results.html", "Results"), ("rules.html", "Rules"),
       ("codelab.html", "Codelab"), ("setup.html", "Setup"), (REPO, "GitHub")]


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def load_reports() -> list[dict]:
    reps = []
    for f in sorted(ROOT.glob("ports*/*/report.json")):
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
    ran = [r for r in rs if r.get("tests_ran")]
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
<rect class="b" x="385" y="132" width="350" height="56"/><text class="t" x="398" y="157">fix: deterministic rules first, a model for the rest</text><text class="s" x="398" y="176">a patch + reason; kept only if proven</text>
<path class="l" d="M460 94V130"/><path class="l" d="M520 130V96"/><path class="l" d="M655 94V130"/><path class="l" d="M840 94C840 160 760 160 737 160"/>
</svg>"""


def index(reps: list[dict]) -> str:
    t = totals(reps, "x86_64")
    a64 = totals(reps, "aarch64le")
    rules = len(re.findall(r"^\| \d+[a-z]? \|", (ROOT / "docs" / "LINUX_ISMS.md").read_text(encoding="utf-8"), re.M))
    a64_stat = (f'<div class="stat"><div class="n">{a64["built"]}/{a64["libs"]}</div><div class="t">also built for aarch64</div></div>'
                if a64["libs"] else "")
    body = f"""
<p class="label">Developer tool · QNX Global Hackathon 2026</p>
<h1>Port open-source C libraries to QNX 8.0, and prove each port on QNX.</h1>
<p class="lead">qnx-porter builds a library with QNX's own toolchain, fixes what breaks with reviewable patches,
then runs the library's <em>own</em> test suite on a QNX 8.0 target. A port only counts when those tests ran there.</p>
<p><a class="btn" href="results.html">See every port</a> <a class="btn ghost" href="codelab.html">Try the codelab</a></p>
<div class="stats">
<div class="stat"><div class="n">{t['built']}/{t['libs']}</div><div class="t">libraries built for QNX 8.0 x86_64</div></div>
<div class="stat"><div class="n">{t['passed']}/{t['total']}</div><div class="t">of their own tests passed on the QNX target ({t['with_tests']} libraries)</div></div>
<div class="stat"><div class="n">{t['patches']}</div><div class="t">patches, {t['by_rule']} by deterministic rules, {t['by_model']} by the model</div></div>
<div class="stat"><div class="n">{rules}</div><div class="t">Linux-isms in the rule corpus, each with a test</div></div>
{a64_stat}</div>
<h2>Why a real-time OS needs this</h2>
<div class="cards">
<div class="card"><h3>Nothing builds on the target</h3><p>A QNX system in a car or a robot has no compiler. Every library is cross-compiled with qcc against the SDP sysroot, and most projects ship no QNX toolchain file.</p></div>
<div class="card"><h3>The host cannot run what it built</h3><p>"It compiled" proves little. qnx-porter copies the build to a QNX 8.0 target and runs every test there, with ctest's own pass and fail rules.</p></div>
<div class="card"><h3>POSIX libc, not glibc</h3><p>The same Linux-isms break library after library: epoll, sockets in libc, <code>isinf</code> in libc, <code>printf("%s", NULL)</code>. Those become rules, written once.</p></div>
<div class="card"><h3>Every change is reviewable</h3><p>Automotive, medical and industrial teams review each dependency change. Every fix is a separate patch with its rule, its reason and the error it answers.</p></div>
</div>
<h2>How it works</h2>
<figure>{PIPELINE_SVG}<figcaption>Fig. 1 — The porting loop. Orange: the fix loop; a fix stays only if the rebuild or the test re-run proves it.</figcaption></figure>
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
    body = f"""<h1>Results</h1>
<p class="lead">Every library the campaign ported, read from its <code>report.json</code>. Tests ran on QNX 8.0 in QEMU
(<code>mkqnximage</code>). "On oss.qnx.com" marks libraries QNX's own ports site already lists.</p>
<p><input type="search" id="q" placeholder="Filter by library or arch" aria-label="Filter"></p>
<div class="scroll"><table id="t"><thead><tr><th>Library</th><th>Version</th><th>Arch</th><th>Build system</th><th>Build</th>
<th>Tests on QNX</th><th>Patches</th><th>Rounds</th><th>On oss.qnx.com</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="label">Source: results/ports.csv and ports/*/report.json in the repository.</p>
<script>
document.getElementById('q').addEventListener('input', function (e) {{
  var q = e.target.value.toLowerCase();
  document.querySelectorAll('#t tbody tr').forEach(function (tr) {{ tr.hidden = tr.dataset.q.indexOf(q) < 0; }});
}});
</script>"""
    return page("Results · qnx-porter", body, "results.html")


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


def md_page(src: str, title: str, current: str) -> str:
    text = (ROOT / src).read_text(encoding="utf-8")
    text = re.sub(r"\]\(\.\./SETUP\.md\)", "](setup.html)", text)
    text = re.sub(r"\]\((?:docs/)?LINUX_ISMS\.md\)", "](rules.html)", text)
    text = re.sub(r"\]\((?:docs/)?CODELAB\.md\)", "](codelab.html)", text)
    body = markdown.markdown(text, extensions=["tables", "fenced_code"])
    body = body.replace("<table>", '<div class="scroll"><table>').replace("</table>", "</table></div>")
    return page(f"{title} · qnx-porter", f'<div class="prose">{body}</div>', current)


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
    (OUT / "codelab.html").write_text(md_page("docs/CODELAB.md", "Codelab", "codelab.html"), encoding="utf-8")
    (OUT / "rules.html").write_text(md_page("docs/LINUX_ISMS.md", "Rules", "rules.html"), encoding="utf-8")
    (OUT / "setup.html").write_text(md_page("SETUP.md", "Setup", "setup.html"), encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    t = totals(reps, "x86_64")
    print(f"site: {len(reps)} ports, {t['built']}/{t['libs']} built, {t['passed']}/{t['total']} tests -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
