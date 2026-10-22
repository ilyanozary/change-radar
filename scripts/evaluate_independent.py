"""Compare prewritten labels with analysis; never execute/import fixture code."""

import ast
import hashlib
import json
from pathlib import Path

from change_radar.core import impact, scan
from change_radar.report import markdown, render

ROOT = Path(__file__).resolve().parents[1]


def evaluate(output=None):
    labels_path = ROOT / "evaluation/expectations.json"
    labels = json.loads(labels_path.read_text())
    results = {}
    for name, expected in labels.items():
        if name == "provenance":
            continue
        fixture = ROOT / "evaluation/fixtures" / name
        graph = scan(fixture)
        report = impact(graph, [expected["seed"]], depth=8)
        found = {x["id"] for x in report["impact"] if "::" in x["id"]}
        related, unrelated = set(expected["related"]), set(expected["unrelated"])
        declared = {n["id"] for n in graph["nodes"] if n["kind"] != "file"}
        missing, false = related - found, found - related
        actual_edges = {
            (
                e["source"],
                e["target"],
                e["type"],
                e["evidence"]["path"],
                e["evidence"]["line"],
            )
            for e in graph["edges"]
        }
        missing_edges = [e for e in expected["edges"] if tuple(e) not in actual_edges]
        expected_symbol_edges = {
            tuple(e) for e in expected["edges"] if "::" in e[0] and "::" in e[1]
        }
        actual_symbol_edges = {
            e for e in actual_edges if e[0] in related and e[1] in related
        }
        unexpected_edges = sorted(actual_symbol_edges - expected_symbol_edges)
        # Verify evidence using a separate AST check, not merely edge line bounds.
        invalid_evidence = []
        for source, target, kind, path, line in expected["edges"]:
            tree = ast.parse((fixture / path).read_text())
            node_type = {
                "calls": ast.Call,
                "depends": ast.Call,
                "includes_router": ast.Call,
                "inherits": (ast.Name, ast.Attribute),
                "annotation": (ast.Name, ast.Attribute),
                "response_model": (ast.Name, ast.Attribute),
            }[kind]
            if not any(
                isinstance(n, node_type) and getattr(n, "lineno", None) == line
                for n in ast.walk(tree)
            ):
                invalid_evidence.append([source, target, kind, path, line])
        endpoints = {(e["symbol"], e["method"], e["path"]) for e in graph["endpoints"]}
        missing_endpoints = [
            e for e in expected["endpoints"] if tuple(e) not in endpoints
        ]
        tp = len(found & related)
        results[name] = dict(
            found=sorted(found),
            missed=sorted(missing),
            false_positive=sorted(false),
            unrelated_found=sorted(found & unrelated),
            unlabeled_symbols=sorted(declared - related - unrelated),
            missing_edges=missing_edges,
            unexpected_edges=unexpected_edges,
            invalid_evidence=invalid_evidence,
            missing_endpoints=missing_endpoints,
            precision=tp / len(found) if found else None,
            recall=tp / len(related),
            expected_relations=expected["edges"],
        )
        if output:
            output.mkdir(parents=True, exist_ok=True)
            for ext, content in [
                ("json", json.dumps(report, sort_keys=True, indent=2)),
                ("md", markdown(report)),
                ("html", render(report)),
            ]:
                (output / (name + "." + ext)).write_text(content)
    return dict(
        expectations_sha256=hashlib.sha256(labels_path.read_bytes()).hexdigest(),
        scope=labels["provenance"],
        scenarios=results,
    )


def passed(result):
    return all(
        not any(
            s[k]
            for k in (
                "missed",
                "false_positive",
                "unlabeled_symbols",
                "missing_edges",
                "unexpected_edges",
                "invalid_evidence",
                "missing_endpoints",
            )
        )
        for s in result["scenarios"].values()
    )


if __name__ == "__main__":
    result = evaluate(ROOT / ".change-radar/independent")
    print(json.dumps(result, sort_keys=True, indent=2))
    raise SystemExit(0 if passed(result) else 1)
