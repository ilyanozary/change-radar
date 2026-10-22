"""Compare unchanged public ground truth across the reviewed baseline and preview."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

from change_radar.core import impact, scan

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("checkout", type=Path)
args = parser.parse_args()
before = json.loads((root / "docs/public-evaluation.json").read_text())
run = subprocess.run(
    [sys.executable, str(root / "scripts/evaluate_public.py"), str(args.checkout)],
    check=True,
    capture_output=True,
    text=True,
)
after = json.loads(run.stdout)
if (
    before["commit"] != after["commit"]
    or before["expectations_sha256"] != after["expectations_sha256"]
):
    raise SystemExit("Comparison requires identical target commit and ground truth")
graph = scan(args.checkout / "backend")
expected_evidence = [
    (
        "app/api/deps.py::CurrentUser",
        "app/api/deps.py::get_current_user",
        "depends",
        "app/api/deps.py",
        49,
    ),
    (
        "app/api/deps.py::get_current_active_superuser",
        "app/api/deps.py::CurrentUser",
        "annotation",
        "app/api/deps.py",
        52,
    ),
    (
        "app/api/routes/items.py::read_item",
        "app/api/deps.py::CurrentUser",
        "annotation",
        "app/api/routes/items.py",
        49,
    ),
    (
        "app/models.py::ItemsPublic",
        "app/models.py::ItemPublic",
        "annotation",
        "app/models.py",
        104,
    ),
]
audit = []
for source, target, kind, path, line in expected_evidence:
    matches = [
        e
        for e in graph["edges"]
        if (
            e["source"],
            e["target"],
            e["type"],
            e["evidence"]["path"],
            e["evidence"]["line"],
        )
        == (source, target, kind, path, line)
    ]
    audit.append(
        dict(
            source=source,
            target=target,
            type=kind,
            path=path,
            line=line,
            matched=len(matches) == 1
            and matches[0]["certainty"] == "observed"
            and matches[0]["origin"] == "python-ast",
        )
    )
report = impact(graph, ["app/models.py::ItemBase"], depth=8, limit=1000)
false_chain = next(
    (
        i["chain"]
        for i in report["impact"]
        if i["id"] == "app/api/routes/login.py::login_access_token"
    ),
    [],
)
print(
    json.dumps(
        dict(
            baseline_commit="4e4d15c6db1720df14c5299f33f325dcfa147760",
            before=before,
            after=after,
            supplementary_evidence_audit=audit,
            labeled_false_positive_chain=false_chain,
        ),
        indent=2,
        sort_keys=True,
    )
)
if not all(item["matched"] for item in audit):
    raise SystemExit("Supplementary alias/composition evidence audit failed")
