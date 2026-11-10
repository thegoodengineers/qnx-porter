"""Check each candidate in candidates.json is not already ported: oss.qnx.com packages and the qnx-ports org.

Writes results/candidates_check.csv. Also checks the release tag exists upstream (git ls-remote).
Usage: python scripts/check_candidates.py
"""
import csv
import json
import subprocess
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OSS = "https://5p3b9woc03.execute-api.us-east-1.amazonaws.com/prod-PFQje4ICJpDlAzyUmbTu/packages"  # oss.qnx.com's API


def oss_packages() -> tuple[set, set]:
    names, urls, cursor = set(), set(), ""
    while True:
        with urllib.request.urlopen(f"{OSS}?sort=package_name&size=100&cursor={urllib.parse.quote(cursor)}",
                                    timeout=60) as r:
            items = json.load(r)
            cursor = r.headers.get("x-next-cursor")
        for x in items:
            names.add(x["package_name"].lower())
            urls.add((x.get("repo_url") or "").lower().rstrip("/").removesuffix(".git"))
        if not cursor or not items:
            return names, urls


def qnx_ports_repos() -> set:
    out = subprocess.run(["gh", "api", "--paginate", "orgs/qnx-ports/repos", "--jq", ".[].name"],
                         capture_output=True, text=True, check=True).stdout
    return {n.lower() for n in out.split()}


def main():
    cands = json.loads((ROOT / "candidates.json").read_text())
    names, urls = oss_packages()
    ports = qnx_ports_repos()
    rows = []
    for c in cands:
        n = c["name"].lower()
        url = c["url"].lower().removesuffix(".git")
        on_oss = sorted(x for x in names if x == n or x.startswith(n + "-")) + (["(repo url)"] if url in urls else [])
        tag_ok = bool(subprocess.run(["git", "ls-remote", "--tags", c["url"], c["tag"]], capture_output=True,
                                     text=True, timeout=120).stdout.strip())
        rows.append({"library": c["name"], "url": c["url"], "tag": c["tag"], "tag_exists": tag_ok,
                     "on_oss_qnx_com": ";".join(on_oss) or "no", "in_qnx_ports_org": n in ports,
                     "checked": date.today().isoformat()})
        print(rows[-1])
    out = ROOT / "results" / "candidates_check.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(names)} oss.qnx.com packages, {len(ports)} qnx-ports repos checked -> {out}")


if __name__ == "__main__":
    main()
