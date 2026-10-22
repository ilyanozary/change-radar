import json
from pathlib import Path


def markdown(data):
    # Inline code cannot contain raw newlines/backticks from repository names.
    def safe(s):
        return (
            str(s)
            .replace("`", "\\`")
            .replace("\n", " ")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    lines = [
        "# Change Radar",
        "",
        "Static evidence; potential impact is inferred, not proven breakage.",
        "",
        "## Seeds",
    ]
    lines += ["- `" + safe(s) + "`" for s in data.get("seeds", [])]
    lines += [
        "",
        "## Change request",
        safe(data.get("request", "")),
        "",
        "## Potential impact",
    ]
    for item in data.get("impact", []):
        lines.append(f"- `{safe(item['id'])}` · depth {item['depth']} · {item['role']}")
        for e in item["chain"]:
            ev = e["evidence"]
            lines.append(
                f"  - {e['type']}: `{safe(e['source'])}` → `{safe(e['target'])}` ({safe(ev['path'])}:{ev['line']}; {e['certainty']})"
            )
    lines += [
        "",
        "## Coverage",
        f"Parsed {data['coverage']['parsed']}/{data['coverage']['files']} files; {len(data['coverage']['issues'])} review items.",
        "Traversal truncated: " + str(data.get("truncated", False)),
        "",
        "## Manual review",
    ]
    lines += [
        "- " + safe(json.dumps(i, ensure_ascii=False))
        for i in data["coverage"]["issues"]
    ]
    lines += ["", "## Limitations"] + ["- " + s for s in data["limitations"]]
    lines += ["", "## Suggested existing tests"] + [
        "- `" + safe(t["id"]) + "` (graph reference)"
        for t in data.get("suggested_tests", [])
    ]
    lines += ["", "## Related endpoints"] + [
        f"- {e['method']} `{safe(e['path'] if e['path'] is not None else 'UNRESOLVED')}` · `{safe(e['symbol'])}` · {safe(e['evidence']['path'])}:{e['evidence']['line']}"
        for e in data.get("endpoints", [])
        if "impact" not in data or e["symbol"] in {x["id"] for x in data["impact"]}
    ]
    lines += ["", "## Suggested change order"] + [
        "- " + safe(x) for x in data.get("implementation_order", [])
    ]
    lines += ["", "## New regression scenarios"] + [
        "- " + s for s in data.get("new_test_scenarios", [])
    ]
    return "\n".join(lines) + "\n"


def render(data):
    payload = (
        json.dumps(data, ensure_ascii=True, sort_keys=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return (
        Path(__file__)
        .with_name("template.html")
        .read_text()
        .replace("__RADAR_DATA__", payload)
    )
