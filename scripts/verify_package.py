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
    fixture = base / "inheritance-fixture"
    fixture.mkdir()
    (fixture / "models.py").write_text("class Base: pass\nclass Child(Base): pass\n")
    (fixture / "api.py").write_text(
        "from fastapi import FastAPI\nfrom models import Child\napp = FastAPI()\n@app.get('/items', response_model=Child)\ndef items(): pass\n"
    )
    (fixture / "tests").mkdir()
    (fixture / "tests/test_http.py").write_text(
        "def test_http(): client.get('/items')\n"
    )
    result = json.loads(run("impact", fixture, "--seed", "models.py::Base").stdout)
    inherited = next(e for e in result["edges"] if e["type"] == "inherits")
    assert inherited["source"] == "models.py::Child"
    assert inherited["target"] == "models.py::Base"
    assert inherited["evidence"] == {"path": "models.py", "line": 2}
    candidate = next(
        t for t in result["suggested_tests"] if t["id"].endswith("::test_http")
    )
    assert candidate["evidence"] == "endpoint_literal_candidate"
    (base / "inheritance.json").write_text(json.dumps(result))
    exported = run("report", base / "inheritance.json", "--format", "markdown").stdout
    html = run("report", base / "inheritance.json", "--format", "html").stdout
    assert "`tests/test_http.py::test_http` (endpoint_literal_candidate)" in exported
    assert "const markdownReport = " in html
    assert "__RADAR_MARKDOWN__" not in html
    print(
        "PASS: fresh wheel install, CLI, HTML/Markdown assets, both local skill installers, inherits and test-label exports; no agent runtime invoked."
    )
