"""Analyze an already fetched pinned checkout; never fetch/install/execute target code."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from change_radar.core import impact, scan

parser = argparse.ArgumentParser()
parser.add_argument("checkout", type=Path)
args = parser.parse_args()
label_path = Path(__file__).resolve().parents[1] / "evaluation/public-expectations.json"
labels = json.loads(label_path.read_text())
commit = subprocess.run(
    ["git", "-C", str(args.checkout), "rev-parse", "HEAD"],
    check=True,
    capture_output=True,
    text=True,
).stdout.strip()
if commit != labels["commit"]:
    raise SystemExit("Wrong commit; expected " + labels["commit"])
changes = subprocess.run(
    ["git", "-C", str(args.checkout), "status", "--porcelain"],
    check=True,
    capture_output=True,
    text=True,
).stdout
if changes:
    raise SystemExit("Target checkout must be clean")
g = scan(args.checkout / labels["root"])
results = {}
for name, label in labels["scenarios"].items():
    r = impact(g, [label["seed"]], depth=8, limit=1000)
    found = {i["id"] for i in r["impact"] if "::" in i["id"]}
    expected, negative = set(label["related"]), set(label["unrelated"])
    universe = expected | negative
    tp = found & expected
    fp = found & negative
    actual_edges = {
        (
            e["source"],
            e["target"],
            e["type"],
            e["evidence"]["path"],
            e["evidence"]["line"],
        )
        for e in g["edges"]
    }
    results[name] = dict(
        found=sorted(found & universe),
        missed=sorted(expected - found),
        false_positive=sorted(fp),
        outside_labeled_universe=sorted(found - universe),
        precision=len(tp) / (len(tp) + len(fp)) if tp or fp else None,
        recall=len(tp) / len(expected),
        matched_edges=[e for e in label["edges"] if tuple(e) in actual_edges],
        missing_edges=[e for e in label["edges"] if tuple(e) not in actual_edges],
        truncated=r["truncated"],
    )
print(
    json.dumps(
        dict(
            repository=labels["repository"],
            commit=commit,
            expectations_sha256=hashlib.sha256(label_path.read_bytes()).hexdigest(),
            provenance=labels["provenance"],
            files=g["coverage"]["files"],
            parsed=g["coverage"]["parsed"],
            issue_counts={
                category: sum(
                    i["category"] == category for i in g["coverage"]["issues"]
                )
                for category in sorted({i["category"] for i in g["coverage"]["issues"]})
            },
            scenarios=results,
        ),
        indent=2,
        sort_keys=True,
    )
)
