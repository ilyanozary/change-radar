"""Install the built wheel offline into a fresh environment and exercise packaged assets."""

import json
import os
import subprocess
import tempfile
import tomllib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
wheel = root / "dist" / f"change_radar-{version}-py3-none-any.whl"
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
    auth = json.loads(
        run(
            "impact",
            root / "examples/preview",
            "--seed",
            "security.py::read_token",
            "--depth",
            "8",
        ).stdout
    )
    assert {"routes.py::listing", "routes.py::me"} <= {i["id"] for i in auth["impact"]}
    assert any(
        e["source"] == "security.py::CurrentUser"
        and e["target"] == "security.py::current_user"
        and e["type"] == "depends"
        for e in auth["edges"]
    )
    models = json.loads(
        run(
            "impact",
            root / "examples/preview",
            "--seed",
            "models.py::Item",
            "--depth",
            "8",
        ).stdout
    )
    assert {"models.py::Page", "routes.py::listing"} <= {
        i["id"] for i in models["impact"]
    }
    assert any(
        e["source"] == "models.py::Page"
        and e["target"] == "models.py::Item"
        and e["evidence"]["line"] == 9
        for e in models["edges"]
    )
    installed_version = subprocess.run(
        [str(python), "-c", "import change_radar; print(change_radar.__version__)"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
        cwd=base,
    ).stdout.strip()
    assert installed_version == version
    print(
        "PASS: fresh wheel install, CLI, HTML/Markdown assets, both local skill installers, inherits and test-label exports; no agent runtime invoked."
    )
