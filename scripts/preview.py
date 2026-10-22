"""Generate real, offline preview reports; never execute the example application."""

import json
import shutil
import sys
import tempfile
from pathlib import Path

from change_radar.core import impact, scan
from change_radar.report import markdown, render

ROOT = Path(__file__).resolve().parents[1]


def generate(out):
    out.mkdir(parents=True, exist_ok=True)

    def write(name, data):
        data["demo"] = True
        for ext, content in [
            ("json", json.dumps(data, sort_keys=True, indent=2)),
            ("md", markdown(data)),
            ("html", render(data)),
        ]:
            (out / (name + "." + ext)).write_text(content)
        print(out / (name + ".html"))

    graph = scan(ROOT / "examples/preview")
    write(
        "auth",
        impact(
            graph,
            ["security.py::read_token"],
            depth=8,
            request="اگر وابستگی احراز هویت را تغییر بدهم، چه endpointهایی تحت‌تأثیر قرار می‌گیرند؟",
        ),
    )
    write(
        "models",
        impact(
            graph,
            ["models.py::Item"],
            depth=8,
            request="Change the nested Item contract",
        ),
    )
    write("empty", impact(graph, [], request="No seeds selected — empty is not safe"))
    write(
        "limited",
        impact(
            graph,
            ["security.py::read_token"],
            depth=8,
            limit=3,
            request="Traversal intentionally capped at three results",
        ),
    )
    with tempfile.TemporaryDirectory(prefix="radar-preview-") as folder:
        target = Path(folder) / "source"
        shutil.copytree(ROOT / "examples/preview", target)
        (target / "broken.py").write_text("def broken(\n")
        write(
            "incomplete",
            impact(
                scan(target),
                ["security.py::read_token"],
                depth=8,
                request="Incomplete scan — intentional parse-error fixture",
            ),
        )
        (target / "broken.py").unlink()
        # Actual Python consumers are generated and scanned; no graph is drawn by hand.
        (target / "bulk.py").write_text(
            "from security import CurrentUser\n"
            + "".join(
                f"def consumer_{i}(user: CurrentUser): return user\n" for i in range(80)
            )
        )
        write(
            "large",
            impact(
                scan(target),
                ["security.py::read_token"],
                depth=8,
                limit=200,
                request="Graph viewport cap — 80 generated source consumers",
            ),
        )


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / ".change-radar/preview")
