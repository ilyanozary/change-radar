# Validation status · correctness follow-up

Local environment: Python 3.14.4/Linux. The initial Git working tree was clean;
changes were initially prepared locally for review. The user subsequently authorized committing and pushing the reviewed changes.

Checked:

- **39 unittest methods pass**, including all 22 previous methods, 16 correctness/export regression methods and one three-fixture integration check. Parameter/scenario subtests are not counted as separate methods.
- Regression tests were run before fixes. The final regression module also runs against the isolated d5b4de8 baseline and fails as documented in regression-baseline.txt.
- The three original shop evaluations pass again. The three independent fixtures have zero missed expected symbols, false positives, missing expected relations, unexpected related-symbol relations, incorrect evidence lines or missing expected endpoints.
- The pinned public fastapi/full-stack-fastapi-template checkout was actually analyzed: 40/40 files parsed, no dependencies installed and no target imports/execution. Its partial-label recall is 0.70 (ItemBase) and 0.125 (CurrentUser); see public-evaluation.json for exact found/missed/false-positive sets and coverage counts.
- Ruff lint and formatting pass over src/tests/scripts. The fixture files are deliberately not autoformatted: manually predeclared evidence line numbers are part of the evaluation contract.
- Standard wheel/sdist build and fresh offline wheel install are checked; packaged CLI/HTML/Markdown and both skill installers are exercised. A separate installed-wheel check covers the new inherits relation and canonical browser Markdown content.
- HTML embeds escaped data and canonical Markdown; injection/marker-shaped strings and evidence labels are tested. Extracted generated inline JavaScript passes node --check. These are content/syntax checks, not browser interactions.
- Three original demos and three independent evaluation reports regenerate as HTML, JSON and Markdown under .change-radar/.

Not checked or still unsupported:

- Real browser search/filter/selection/evidence-panel/download/offline opening: the Browser skill returned “No browser is available”, and discovery returned []. No screenshots or interaction results are claimed.
- End-to-end skill discovery/behavior in Codex or Claude Code remains untested.
- Python 3.11/3.12/3.13 were not locally executed. The CI matrix includes them, but this revision has not been uploaded. The earlier baseline's hosted CI was blocked before any steps by a GitHub account billing issue; it does not establish a code failure or a pass.
- Lambda/comprehension bodies, global/nonlocal resolution, generic type-parameter scopes, arbitrary dataflow, inherited method dispatch, exact field-level effects, class-field composition and shared Annotated/Depends aliases remain unsupported. Relevant coverage entries and limitations are emitted.
- No application server or target tests were run. No representative large-repository performance benchmark or cache was added.

See CORRECTNESS_REVIEW.md for reproduction commands, pre/post behavior and manually
confirmed public source chains. The distribution license/copyright decision remains
with the owner. No merge, package publication or deployment occurred in this phase.
