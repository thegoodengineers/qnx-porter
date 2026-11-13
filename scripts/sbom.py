"""Per-port SPDX SBOMs and a copyleft table, from ScanCode Toolkit's licence detection.

For each library in ports/*/report.json: take the upstream checkout at the commit the report names, copy
out only its licence-bearing files (top level and first level: LICENSE*, COPYING*, COPYRIGHT*, NOTICE*,
README*, *.spdx, and the files in a top-level LICENSES/ folder), let ScanCode detect the licence, and write
  ports/<lib>/sbom.spdx.json   SPDX 2.3 JSON, checked with spdx-tools: package, ScanCode's declared licence,
                               qnx.patch with SHA-1 and SHA-256 as PATCH_FOR the package
  results/licences.csv         ScanCode's expression verbatim, and copyleft flags derived from it
  docs/LICENCES.md             the same table
Never edit these by hand. The licence expression is ScanCode's summary; nothing here guesses one.

Run inside the ScanCode venv, niced, in one process (ScanCode's licence index then loads once, in-process):
  nice -n 19 ~/.venv-scancode/bin/python scripts/sbom.py [lib ...]   # no libs: all of them
  python3 scripts/sbom.py --table                                      # only re-derive flags, csv and md
"""
import csv
import datetime
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path.home() / "qnx-porter" / "ports"  # <lib>/work/src: the campaign's upstream checkouts
TOOL = "scancode-toolkit-32.5.0"
PATTERNS = ["license*", "licence*", "copying*", "copyright*", "notice*", "readme*", "*.spdx"]
FIELDS = ["library", "version", "detected_licence", "gpl_family", "lgpl", "copyleft_note"]
# SPDX ids (and ScanCode LicenseRef-scancode-<key> ids) by family, matched on the lower-cased id
COPYLEFT = {"strong copyleft GPL": r"(^|-)gpl-", "strong copyleft AGPL": r"(^|-)agpl-",
            "weak copyleft LGPL": r"(^|-)lgpl-", "weak copyleft MPL": r"(^|-)mpl-", "weak copyleft EPL": r"(^|-)epl-", "weak copyleft CPL": r"(^|-)cpl-",
            "documentation copyleft GFDL": r"(^|-)gfdl-", "documentation share-alike CC-BY-SA": r"(^|-)cc-by-sa-"}


def flags(expr: str) -> dict:
    """gpl_family (GPL or AGPL) / lgpl / copyleft_note from an SPDX licence expression.

    Ids after WITH are exceptions, not licences. GPL in an OR choice still counts; the note says OR is present."""
    toks = re.findall(r"[A-Za-z0-9.+:-]+", expr or "")
    ids = [t.lower() for i, t in enumerate(toks) if t not in ("AND", "OR", "WITH") and (i == 0 or toks[i - 1] != "WITH")]
    if not ids or ids == ["noassertion"]:
        return {"gpl_family": "no", "lgpl": "no", "copyleft_note": "no licence detected in the scanned files"}
    notes = [k for k, p in COPYLEFT.items() if any(re.search(p, i) for i in ids)]
    if notes and "OR" in toks:
        notes.append("expression has OR choices")
    return {"gpl_family": "yes" if {"strong copyleft GPL", "strong copyleft AGPL"} & set(notes) else "no",
            "lgpl": "yes" if "weak copyleft LGPL" in notes else "no", "copyleft_note": "; ".join(notes)}


def git(src, *args) -> str:
    return subprocess.run(["git", "-C", str(src), *args], check=True, capture_output=True, text=True).stdout


def checkout(lib: dict, tmp: Path) -> Path:
    """The campaign checkout if it has the report's commit (the port's own commits sit on top of it), else a
    shallow clone of the tag, which must be that commit too. Files are read at the commit, never the work tree."""
    src = SRC / lib["name"] / "work" / "src"
    if src.is_dir() and subprocess.run(["git", "-C", str(src), "cat-file", "-e", lib["commit"] + "^{commit}"],
                                       capture_output=True).returncode == 0:
        return src
    src = tmp / "clone"
    for _ in range(3):  # the network drops now and then
        r = subprocess.run(["git", "clone", "-q", "--depth", "1", "--branch", lib["tag"], lib["url"], str(src)])
        if r.returncode == 0:
            break
        subprocess.run(["rm", "-rf", str(src)])
    head = git(src, "rev-parse", "HEAD").strip()
    if head != lib["commit"]:
        sys.exit(f"{lib['name']}: tag {lib['tag']} is {head}, report.json says {lib['commit']}")
    return src


def licence_files(src: Path, commit: str, dst: Path) -> list[str]:
    """Copy the licence-bearing files at commit (committed content, not the build tree) into dst."""
    out = []
    for line in git(src, "ls-tree", "-r", commit).splitlines():
        meta, path = line.split("\t", 1)
        parts = path.split("/")
        if meta.split()[0] == "120000" or len(parts) > 2:  # symlinks, deeper than first level
            continue
        if not any(fnmatch.fnmatch(p.lower(), pat) for p in (parts[-1], parts[0]) for pat in PATTERNS):
            continue
        (dst / path).parent.mkdir(parents=True, exist_ok=True)
        (dst / path).write_bytes(subprocess.run(["git", "-C", str(src), "show", f"{commit}:{path}"], check=True,
                                                capture_output=True).stdout)
        out.append(path)
    return sorted(out)


def scan(d: Path) -> tuple[str, list[str]]:
    """ScanCode's declared licence (its summary over key files) as SPDX, plus each file's detection."""
    from licensedcode.cache import build_spdx_license_expression
    from scancode.cli import run_scan
    ok, res = run_scan(str(d), processes=0, quiet=True, info=True, license=True, classify=True, summary=True,
                       return_results=True)
    if not ok:
        sys.exit(f"scancode failed on {d}: {res['headers'][0]['errors']}")
    declared = res["summary"]["declared_license_expression"]
    per_file = [f"{Path(f['path']).relative_to(d.name)}: {f['detected_license_expression_spdx']}"
                for f in res["files"] if f["type"] == "file" and f["detected_license_expression_spdx"]]
    return (build_spdx_license_expression(declared) if declared else "NOASSERTION"), per_file


def licence_refs(expr: str) -> list[dict]:
    """SPDX needs every LicenseRef- defined in the document; same text and link ScanCode's own SPDX writer uses."""
    from licensedcode.cache import get_licenses_db
    by_spdx = {lic.spdx_license_key: lic for lic in get_licenses_db().values()}
    out = []
    for ref in sorted(set(re.findall(r"LicenseRef-[A-Za-z0-9.-]+", expr))):
        lic = by_spdx.get(ref)
        key = lic.key if lic else ref.removeprefix("LicenseRef-scancode-")
        link = f"See details at https://github.com/nexB/scancode-toolkit/blob/develop/src/licensedcode/data/licenses/{key}.LICENSE"
        out.append({"licenseId": ref, "name": lic.name if lic else key, "extractedText": (lic.text if lic else "") or link,
                    "comment": link})
    return out


def document(lib: dict, expr: str, per_file: list[str], scanned: list[str], declared: str) -> dict:
    """declared is expr, or NOASSERTION when ScanCode's expression is not valid SPDX (the comment then keeps it)."""
    patch = ROOT / "ports" / lib["name"] / "qnx.patch"
    data = patch.read_bytes()
    pkg = "SPDXRef-Package-" + re.sub(r"[^A-Za-z0-9.-]", "-", lib["name"])
    epoch = os.environ.get("SOURCE_DATE_EPOCH")  # set it for byte-identical regeneration
    when = datetime.datetime.fromtimestamp(int(epoch), datetime.timezone.utc) if epoch else \
        datetime.datetime.now(datetime.timezone.utc)
    return {
        "spdxVersion": "SPDX-2.3", "dataLicense": "CC0-1.0", "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{lib['name']}-{lib['tag']}-qnx8",
        "documentNamespace": f"https://github.com/thegoodengineers/qnx-porter/spdx/{lib['name']}-{lib['commit']}",
        "creationInfo": {"created": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "creators": [f"Tool: {TOOL}", "Organization: The Good Engineers"]},
        "packages": [{
            "SPDXID": pkg, "name": lib["name"], "versionInfo": lib["tag"],
            "downloadLocation": f"git+{lib['url']}@{lib['commit']}", "filesAnalyzed": False,
            "licenseConcluded": "NOASSERTION", "licenseDeclared": declared, "copyrightText": "NOASSERTION",
            "licenseComments": f"ScanCode summary declared licence over {', '.join(scanned) or 'no files'}: {expr}"
                               + ("" if declared == expr else " (not a valid SPDX expression, so licenseDeclared is NOASSERTION)")
                               + f". Per-file detections: {'; '.join(per_file) or 'none'}.",
        }],
        **({"hasExtractedLicensingInfos": licence_refs(declared)} if "LicenseRef-" in declared else {}),
        "files": [{
            "SPDXID": "SPDXRef-File-qnx.patch", "fileName": f"./ports/{lib['name']}/qnx.patch",
            "checksums": [{"algorithm": a.upper(), "checksumValue": hashlib.new(a, data).hexdigest()}
                          for a in ("sha1", "sha256")],
            "licenseConcluded": "NOASSERTION", "copyrightText": "NOASSERTION",
            "comment": "QNX 8.0 port changes, apply with git apply"
                       + ("; empty: the port needed no source change" if not data else ""),
        }],
        "relationships": [
            {"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": pkg},
            {"spdxElementId": "SPDXRef-File-qnx.patch", "relationshipType": "PATCH_FOR", "relatedSpdxElement": pkg},
        ],
    }


def write_sbom(lib: dict, expr: str, per_file: list[str], scanned: list[str]):
    """Write and validate with spdx-tools; fall back to NOASSERTION only if ScanCode's expression is what fails."""
    from spdx_tools.spdx.parser.parse_anything import parse_file
    from spdx_tools.spdx.validation.document_validator import validate_full_spdx_document
    dest = ROOT / "ports" / lib["name"] / "sbom.spdx.json"
    for declared in (expr, "NOASSERTION"):
        dest.write_text(json.dumps(document(lib, expr, per_file, scanned, declared), indent=2) + "\n", encoding="utf-8")
        try:
            errors = [e.validation_message for e in validate_full_spdx_document(parse_file(str(dest)))]
        except Exception as e:  # spdx-tools raises on an unparsable licence expression
            errors = [str(e)]
        if not errors:
            return
        print(f"{lib['name']}: licenseDeclared {declared!r} rejected by spdx-tools: {errors}", flush=True)
    sys.exit(f"{dest}: invalid SPDX")


def libraries() -> list[dict]:
    import yaml
    tags = {x["name"]: x for x in yaml.safe_load((ROOT / "campaign.yaml").read_text(encoding="utf-8"))["libraries"]}
    out = []
    for f in sorted((ROOT / "ports").glob("*/report.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        c = tags[r["library"]]
        out.append({"name": r["library"], "url": c["url"], "tag": str(c["tag"]), "commit": r["commit"]})
    return out


def table(scanned: dict):
    """results/licences.csv keeps ScanCode's expressions verbatim; rows of libraries not rescanned now are kept."""
    dest = ROOT / "results" / "licences.csv"
    old = {r["library"]: r for r in csv.DictReader(dest.open(encoding="utf-8"))} if dest.exists() else {}
    rows = [{**r, **flags(r["detected_licence"])} for _, r in sorted({**old, **scanned}.items(), key=lambda kv: kv[0].lower())]
    with dest.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    n = len(rows)
    gpl, lgpl = sum(r["gpl_family"] == "yes" for r in rows), sum(r["lgpl"] == "yes" for r in rows)
    weak = sum("weak copyleft" in r["copyleft_note"] for r in rows)
    none = sum(r["detected_licence"] == "NOASSERTION" for r in rows)
    md = [
        "# Licences of the ported libraries",
        "",
        "Generated by `scripts/sbom.py`; do not edit. Each `ports/<lib>/sbom.spdx.json` is an SPDX 2.3 document for the "
        "upstream package at the commit we ported, with our `qnx.patch` and its SHA-256. The licence is the declared "
        f"licence that ScanCode Toolkit ({TOOL}) reports in its summary over the library's top-level and first-level "
        "licence, copying, copyright, notice and README files. Only those files were scanned, not the source tree, so "
        "a licence stated only in source headers is not seen here. `NOASSERTION` means ScanCode detected nothing. "
        "Where ScanCode's expression is not valid SPDX (for example a bare exception such as `LLVM-exception`), the "
        "SBOM's `licenseDeclared` is `NOASSERTION` and its `licenseComments` and this table keep the expression as found.",
        "",
        "Read the expressions as scanner findings. ScanCode joins licences it finds in one file with `AND`, also when "
        "the file offers a choice: Mbed TLS's LICENSE says Apache-2.0 OR GPL-2.0-or-later, and the table shows `AND`. "
        "README files add licences they merely mention. A flag means a copyleft licence was detected, so check that "
        "library's licence files before deciding anything from it.",
        "",
        f"Of {n} libraries: {gpl} have a GPL or AGPL licence in their expression (GPL family), {lgpl} an LGPL licence, "
        f"{weak} a weak copyleft licence (LGPL, MPL, EPL or CPL), and {none} with no detected licence.",
        "",
        "Why this matters on QNX. QNX products are commonly shipped as one system image in which libraries are linked "
        "statically or delivered as shared objects alongside proprietary code. The GPL applies its terms to a "
        "distributed work based on the GPL-licensed code, which then has to be offered with its corresponding source "
        "under the GPL. The LGPL allows linking from code under other terms but requires that recipients can replace "
        "the LGPL library with a modified version; with static linking that usually means also providing the object "
        "files needed to relink. MPL and EPL obligations apply to the licensed files themselves, so changes to those "
        "files, including our `qnx.patch`, are distributed as source. An expression with `OR` offers a choice of "
        "licence; `AND` means all listed terms apply, often to different parts of the package, such as a library and "
        "its command-line tools. This page is scanner output for engineering triage, not a legal review.",
        "",
        "| Library | Version | Detected licence (SPDX) | GPL family | LGPL | Copyleft note |",
        "|---|---|---|---|---|---|",
    ]
    md += [f"| {r['library']} | {r['version']} | `{r['detected_licence']}` | {r['gpl_family']} | {r['lgpl']} "
           f"| {r['copyleft_note']} |" for r in rows]
    (ROOT / "docs" / "LICENCES.md").write_text("\n".join(md) + "\n", encoding="utf-8", newline="\n")
    print(f"{n} libraries: {gpl} GPL family, {lgpl} LGPL, {weak} weak copyleft, {none} NOASSERTION")


def main():
    done = {}
    if sys.argv[1:] != ["--table"]:
        only = set(sys.argv[1:])
        for lib in libraries():
            if only and lib["name"] not in only:
                continue
            with tempfile.TemporaryDirectory() as t:
                tmp = Path(t)
                src = checkout(lib, tmp)
                (tmp / lib["name"]).mkdir()
                scanned = licence_files(src, lib["commit"], tmp / lib["name"])
                expr, per_file = scan(tmp / lib["name"])
            write_sbom(lib, expr, per_file, scanned)
            done[lib["name"]] = {"library": lib["name"], "version": lib["tag"], "detected_licence": expr}
            print(f"{lib['name']} {lib['tag']}: {expr}", flush=True)
    table(done)


if __name__ == "__main__":
    main()
