"""Install the built wheel offline into a fresh environment and exercise packaged assets."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
wheel = next((root / "dist").glob("change_radar-*.whl"))
with tempfile.TemporaryDirectory(prefix="radar-wheel-") as folder:
    base = Path(folder)
    subprocess.run(["python3", "-m", "venv", str(base / "env")], check=True)
    python = base / "env/bin/python"
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    subprocess.run(
        [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheel)],
        check=True,
        env=env,
        cwd=base,
    )
    cli = base / "env/bin/change-radar"

    def run(*args):
        return subprocess.run(
            [str(cli), *map(str, args)],
            check=True,
            capture_output=True,
            text=True,
            env=env,
            cwd=base,
        )

    doctor = json.loads(run("doctor").stdout)
    assert doctor["network_required"] is False
    report = base / "report.html"
    run(
        "impact",
        root / "examples/shop",
        "--seed",
        "app/services.py::normalize_user",
        "--format",
        "html",
        "--output",
        report,
    )
    assert "__RADAR_DATA__" not in report.read_text()
    assert "app/services.py::normalize_user" in report.read_text()
    for agent, folder in [("codex", ".agents"), ("claude", ".claude")]:
        dest = base / agent
        dest.mkdir()
        run(
            "install-skill",
            "--agent",
            agent,
            "--scope",
            "project",
            "--root",
            dest,
            "--dry-run",
        )
        assert not (dest / folder).exists()
        run("install-skill", "--agent", agent, "--scope", "project", "--root", dest)
        assert (
            (dest / folder / "skills/change-radar/SKILL.md")
            .read_text()
            .startswith("---")
        )
    (base / "report.json").write_text(run("scan", root / "examples/shop").stdout)
    run(
        "report",
        base / "report.json",
        "--format",
        "markdown",
        "--output",
        base / "report.md",
    )
    assert (base / "report.md").read_text().startswith("# Change Radar")
    print(
        "PASS: fresh wheel install, CLI, HTML/Markdown assets, both local skill installers; no agent runtime invoked."
    )
