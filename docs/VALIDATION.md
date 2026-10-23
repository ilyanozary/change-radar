# Current validation · 2026-10-23 · 0.1.0a1

The entry tree at 4e4d15c was clean. The annotation phase covered two annotation patterns, demo/validation and documentation.
The subsequent browser phase adds Playwright checks and two report interaction fixes. Commits/push follow AGENTS.md;
no merge, public release, package upload, deploy or social post is authorized.

- **54 unittest methods pass** on Python 3.14.4/Linux: all 39 baseline methods plus
  15 annotation methods. Subtests are not counted separately. Tests were written
  and failed before implementation (26 initial failing subcases), then passed.
- Shop evaluation and all three independent fixture sets pass with unchanged labels.
- Pinned public repository: 40/40 Python files parsed, same commit and label hash.
  CurrentUser recall 0.125→1.0, zero labeled false positives; ItemBase recall 0.70→1.0,
  with one labeled false positive (precision 10/11). Neither traversal truncated.
  Eight original model edge witnesses and four supplementary alias/composition
  witnesses match expected type/path/line; see preview-comparison.json.
- Wheel and sdist build. The exact 0.1.0a1 wheel is selected by version, avoiding
  accidental verification of a stale wheel. Fresh offline installation verifies
  version, CLI, report/skill assets, installer safeguards, inherits, test evidence
  exports and both new patterns. No target dependencies are installed or executed.
- Project CI lint/format scope (`ruff check src tests scripts` and
  `ruff format --check src tests scripts`) and git diff checks pass. A broader
  `ruff check .` / `ruff format --check .` also inspected fixed source fixtures and
  found pre-existing import/format differences; those evidence fixtures were preserved. Generated HTML data/export escaping
  and JavaScript syntax are checked separately from browser interaction.
- The original three demos plus six preview cases regenerate from actual scans.
  Empty/capped/incomplete/large cases are actual engine outputs from declared or
  temporary source fixtures, not hand-authored graphs.

| Surface | Status | Evidence / limitation |
|---|---|---|
| Standalone engine/CLI/package | Verified locally | Fresh offline wheel, existing evaluations, positive/negative tests |
| Codex skill end-to-end | Verified on one fixture | Real CLI session exit 0; discovery, seeds, engine, source reads and limits reviewed; all 5 source files unchanged |
| Claude Code end-to-end | Not performed | Executable absent; file installation is a separate passing check |
| Real browser interactions | 16/16 Playwright checks pass | Fresh offline file:// headless Chrome 148; downloads and mouse interactions verified; see BROWSER_ACCEPTANCE.md |
| Hosted CI | Not a pass | Last reviewed run 39827651500 stopped before any steps because GitHub reported an account billing lock; no account/payment changes made |
| Python 3.11–3.13 locally | Not performed | Matrix configured, not established by local 3.14 results |

Remaining analysis boundaries: dynamic/rebound/cyclic aliases, complex quoted
annotations, unknown generic containers, dependency overrides, arbitrary dataflow,
instance/inherited dispatch, lambda/comprehension bodies and global/nonlocal names.
Annotation/ORM composition can overapproximate affected consumers, as measured.
No cache or large-repository performance claim is added.

The owner's license/copyright decision remains a gate to
a full public experimental announcement. Missing Claude verification is disclosed;
no universal agent or accuracy claim is made. See PREVIEW.md and AGENT_VALIDATION.md.
