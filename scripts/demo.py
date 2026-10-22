"""Generate genuine static-analysis demo reports; does not run the demo app."""

import json
import sys
from pathlib import Path

from change_radar.core import impact, scan
from change_radar.report import markdown, render

out = Path(sys.argv[1] if len(sys.argv) > 1 else ".change-radar/demo")
out.mkdir(parents=True, exist_ok=True)
root = Path(__file__).resolve().parents[1]
graph = scan(root / "examples/shop")
for name, seed, request in [
    ("otp", "app/services.py::authenticate", "Replace password login with OTP"),
    ("response", "app/models.py::Session", "Rename access_token response field"),
    (
        "shared",
        "app/services.py::normalize_user",
        "Change shared username normalization",
    ),
]:
    result = impact(graph, [seed], depth=6, request=request)
    result["demo"] = True
    for ext, content in [
        ("json", json.dumps(result, indent=2, sort_keys=True)),
        ("md", markdown(result)),
        ("html", render(result)),
    ]:
        (out / (name + "." + ext)).write_text(content)
    print(name, len(result["impact"]), "nodes", out / (name + ".html"))
