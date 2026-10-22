# Validation status · 2026-10-22

Implemented and locally checked:

- 22 standard-library unittest behavioral cases pass on Python 3.14.4/Linux. These analyze fixture source without importing/executing it.
- Three fixed demo evaluations pass; scoped precision/recall and actual timings are recorded in evaluation.json.
- Three real demo scenarios produce standalone HTML, JSON and Markdown under `.change-radar/demo/`.
- Editable install and standard wheel/sdist build succeed. Fresh virtual-environment wheel installation uses `--no-index --no-deps`, and the installed CLI exercises scan, impact, report, HTML template and both agent skill installers.
- The skill-creator validator accepts the canonical SKILL.md. Installer dry-run and preservation behaviors pass tests; real agent behavior is a separate unchecked layer.
- Ruff lint/format pass. Extracted inline report JavaScript passes `node --check`; JSON payload roundtrip and script-boundary escaping are tested.

Not validated here:

- Browser visual/interaction QA, console output, screenshots and real `file://` opening. Browser runtime setup returned “No browser is available” and browser discovery returned an empty list. JavaScript syntax checking is not a substitute for UI testing.
- Codex skill discovery and end-to-end seed selection/report quality. A Codex executable is installed, but no separate agent workflow was run.
- Claude Code end-to-end workflow: its executable is absent.
- Python 3.11/3.12/3.13 local execution. A CI matrix is provided, but no hosted CI run has occurred.
- Running the example FastAPI server or its tests: analysis does not need its dependencies; those were not installed/executed in this validation pass.
- Representative large-repository performance, exact field-level impact and dynamic runtime effects.

No cache is implemented. No cache-invalidation test is claimed: the tests verify that full rescans reflect changed, deleted and renamed files. No source excerpts or target runtime secrets are included in reports, but identifiers and route literals may themselves be sensitive. Review before sharing.

Before public release: owner chooses license/copyright attribution; perform browser QA and actual Codex/Claude Code workflows. No public repository, package publish, deployment or social post has been performed.
