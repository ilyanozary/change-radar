# 0.1 experimental preview · 2026-10-23

Local package version: **0.1.0a1** (PEP 440 prerelease). No release, package upload,
deployment or social post is authorized or performed. The two analysis patterns
are implemented and locally validated, but this is **not an unconditional public
launch readiness declaration**. The owner still needs to select a license and
review the recorded browser acceptance before announcing the downloadable open-source preview.

## Reproduce the demo

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python scripts/preview.py
```

Open `.change-radar/preview/auth.html` directly in a browser. No server, Node.js,
CDN, API key or target dependencies are needed for analysis or report generation.
JSON and Markdown accompany every HTML file.

The real source is in `examples/preview`; it is scanned, not imported or executed:

- `security.py:9`: current_user depends on read_token.
- `security.py:13`: CurrentUser uses Annotated and Need(dependency=current_user).
- `routes.py:9` and `routes.py:14`: listing and me consume CurrentUser.
- `models.py:9`: Page.items is list[Item]; listing consumes Page at routes.py:8.
- Effective routes are GET /v1/shop/items, /v1/shop/me and /v1/shop/health.
  Health does not consume the authentication alias.

```bash
.venv/bin/change-radar impact examples/preview --seed security.py::read_token --depth 8
.venv/bin/change-radar impact examples/preview --seed models.py::Item --depth 8
```

A free-text `--request` is only a report label; the agent selects seeds for natural
language. The report arrows are consumer → dependency; reverse impact traversal
explains why a consumer is reached. An annotation is not proof of serialization
behavior, a runtime call or breakage.

## Analysis scope

- Module-level Annotated aliases from typing/typing_extensions, including import
  aliases, direct module imports and supported reexports. Simple alias chains are
  followed; scope-aware rebinding/ambiguity blocks resolution. Alias nodes use
  stable path::name IDs and kind=alias. Endpoint→alias edges are annotation;
  alias→dependency edges are depends; each has an AST path and exact line.
- Depends accepts exactly one positional or dependency= argument. Unpacking,
  conflicting arguments, dynamic factories and unknown callable bindings are
  unresolved. Alias resolution stops at cycles or 64 active levels. Unsupported
  metadata is reported; it is not reinterpreted as a type reference.
- Class fields can refer to local models directly or through list/set/tuple/dict,
  Optional/Union, |, and Annotated's type argument. Imported model aliases and
  composition combined with inheritance work. Recursive model references are
  graph cycles handled by bounded traversal.
- Quoted references are parsed as AST, never evaluated: only a simple identifier
  or dotted name is supported. Complex quoted type expressions remain unresolved.
  Unknown generic containers, shadowed containers/types and executable expressions
  are not traversed to invent relations. Class annotations are syntactic references
  for any class; no Pydantic import or runtime model introspection is performed.
- No local assignment dataflow, inherited dispatch, generic type-parameter scopes,
  lambda/comprehension bodies or global/nonlocal inference has been added. No cache,
  cloud service, account feature or general language support has been added.

## Validation results

54 unittest methods pass, including all 39 baseline methods. The initial 13 new
methods were run before implementation and produced 26 failing subcases. A further
negative test exposed dependency **kwargs ambiguity before its correction. The
final annotation module has 15 methods (subtests are not counted as methods).

The shop evaluation and all three independent source-labeled fixture sets still
pass. Their labels and the public-project ground truth are unchanged. The expected
source lines in the public assessment are still checked exactly.

Pinned project: fastapi/full-stack-fastapi-template at
`b1125d8839482cb7bbae603ddc6d0081bf87532e`, root backend, 40/40 Python files parsed.
No target dependencies were installed; target code and tests were not imported or
run. Same seeds, labels, depth 8 and node limit 1000 as before:

| Seed | Relevant found before → after | Missed | Labeled false positives | Precision | Recall |
|---|---|---|---|---|---|
| ItemBase | 7/10 → 10/10 | 3 → 0 | 0 → 1 | 1.0 → 10/11 | 0.70 → 1.0 |
| get_current_user | 1/8 → 8/8 | 7 → 0 | 0 → 0 | 1.0 → 1.0 | 0.125 → 1.0 |

Neither analysis was truncated. All eight predeclared model edges now match their
expected type/path/line (previously seven). The new composition edge is
ItemsPublic→ItemPublic at app/models.py:104. The dependency path includes
get_current_user ← CurrentUser at app/api/deps.py:49, then endpoint parameter
annotations such as app/api/routes/items.py:49. These paths were inspected in source.

**Do not hide the false positive or change its label:** login_access_token remains
an unrelated label in the existing ground truth. Its reached chain is:
ItemBase ← Item (inherits, models.py:87) ← User (annotation, models.py:55) ←
authenticate (annotation, crud.py:45) ← login_access_token (calls, login.py:30).
All four syntactic relations have genuine source witnesses; propagating the
SQLModel relationship through the entire User type overestimates the intended
change effect. This is a coarse-reference impact limitation, not evidence of a
runtime failure. No special-case exclusion was invented to improve the score.
Broader discoveries outside the labeled universe are recorded separately, not
silently counted as correct or false. Metrics apply only to the selected labels.

Coverage changes: unresolved_class_annotation is replaced with actual per-type
resolution; unresolved annotations still report unsupported/external types.
The three old blanket alias warnings are replaced by supported alias paths, with
an unresolved dependency remaining for the dynamic OAuth bearer instance. Dynamic
runtime router prefixes still leave all 23 mounted route paths unresolved.
See [full before/after results](preview-comparison.json) for exact sets, edge checks,
truncation and coverage counts; [public-evaluation.json](public-evaluation.json)
retains the reviewed baseline unchanged.

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/evaluate.py
.venv/bin/python scripts/evaluate_independent.py
.venv/bin/python scripts/compare_preview.py /tmp/radar-v01-public
.venv/bin/python -m build
.venv/bin/python scripts/verify_package.py
```

To fetch the identical target independently:

```bash
git init /tmp/radar-v01-public
git -C /tmp/radar-v01-public fetch --depth 1 https://github.com/fastapi/full-stack-fastapi-template.git b1125d8839482cb7bbae603ddc6d0081bf87532e
git -C /tmp/radar-v01-public checkout --detach FETCH_HEAD
```

## Readiness and remaining work

| Item | Status | Consequence |
|---|---|---|
| Alias and composition core | Verified locally | Positive/negative evidence tests pass |
| Fresh wheel/CLI/assets/skill installers | Verified locally | 0.1.0a1 installed offline into fresh venv |
| Real Codex skill behavior | Verified on one isolated fixture | Not a guarantee across agents/repos |
| Real Claude Code behavior | Not performed: executable absent | Do not advertise as end-to-end verified |
| Browser interaction/offline downloads | Verified: 16/16 Playwright checks | Headless Chrome/Linux; see BROWSER_ACCEPTANCE.md |
| License and copyright holder | Owner decision open | Blocker to licensed open-source distribution |
| Hosted CI | Previous run stopped before tests: account billing lock | No hosted pass claimed; no billing changes made |
| Coarse ORM composition false positive | Measured limitation | Disclose; no production accuracy claim |

The license gate must be resolved before declaring the public preview
fully ready. Missing Claude verification and the documented analysis boundaries
are acceptable disclosed experimental limitations, not claims of completed support.
