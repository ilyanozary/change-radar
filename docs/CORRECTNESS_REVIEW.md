# Correctness review (historical baseline)

Base: `d5b4de86da019403bb28431abd211f73d635cbaf`. The working tree was clean at
entry; no pre-existing local edits were replaced. Changes were initially prepared
locally for review; the user subsequently authorized committing and pushing them.
No package publication or deployment is included.

## Reproduce the four bugs and the corrections

The current regression module is `tests/test_correctness.py`. It was first run
against the unmodified analyzer, before implementation. The initial ten methods
produced twenty failing subcases. Additional tests preceded corrections for
shadowed Depends aliases, conditional imports, function-attribute lookups and browser Markdown export.
The final regression module was also run against an isolated archive of the
baseline; see [baseline results](regression-baseline.txt). Counts there are failing
subcases, not the number of test methods.

Use the installed environment:

```bash
.venv/bin/python -m unittest discover -s tests -p test_correctness.py -v
```

To run the current regression tests against the old implementation without
modifying this working tree (the final command intentionally fails):

```bash
RADAR_BASELINE=$(mktemp -d)
git archive d5b4de8 | tar -x -C "$RADAR_BASELINE"
PYTHONPATH="$RADAR_BASELINE/src" .venv/bin/python -m unittest discover -s tests -p test_correctness.py -v
```

| Issue | Before | After | Focused test |
|---|---|---|---|
| Parameters | `*f` and `**f`, including async variants, falsely called global f. Ordinary, positional-only and keyword-only parameters already blocked it. | All parameter categories block callable resolution; unresolved calls remain visible. | `test_parameter_kinds` |
| Nested scopes | Assignments/imports in inner bodies polluted outer bindings; closures could incorrectly fall back to module names. | Scope-bounded collection; nearest lexical binding wins; class namespaces are skipped when resolving method/closure bodies. | `test_nested_bindings_do_not_pollute_outer`, `test_closure_bindings_and_local_definition_shadow_module` |
| Inheritance | No Base→Child impact path existed. | Child→Base `inherits` reference with exact base-expression line. Aliased, multiple and transitive bases are supported. Dynamic, generic and external bases are unresolved. | `test_inheritance_alias_multiple_and_transitive`, `test_unresolved_bases_are_coverage` |
| Test labels | Markdown hardcoded “graph reference”; browser Markdown download omitted the suggested-test section. | JSON, HTML display, CLI Markdown and browser Markdown export preserve `graph_reference` versus `endpoint_literal_candidate`; both exports use the same Markdown generator. | `test_test_labels_survive_all_reports`, `test_browser_markdown_export_keeps_test_labels` |

For a single focused reproduction, add tests to the module search path, e.g.:

```bash
PYTHONPATH=tests .venv/bin/python -m unittest test_correctness.CorrectnessTests.test_parameter_kinds -v
PYTHONPATH=tests .venv/bin/python -m unittest test_correctness.CorrectnessTests.test_nested_bindings_do_not_pollute_outer -v
PYTHONPATH=tests .venv/bin/python -m unittest test_correctness.CorrectnessTests.test_inheritance_alias_multiple_and_transitive -v
PYTHONPATH=tests .venv/bin/python -m unittest test_correctness.CorrectnessTests.test_test_labels_survive_all_reports -v
```

## Lexical scope boundaries

`src/change_radar/scopes.py` indexes only the current scope's bindings, with explicit
stops at function/class/lambda/comprehension boundaries. It knows all parameter
forms, assignments/deletes, imports, direct definitions, exception and match
bindings. Direct local imports stay unresolved rather than being executed or
inferred. A closure encountering an unknown outer binding does not continue to a
same-named global. Conditional imports cannot borrow another import's binding.
A nested function is not treated as an attribute of its defining function;
`factory.inner()` is unresolved unless an actual supported class-member path exists.

Definition defaults, decorators, bases and annotations resolve in the enclosing
scope; their relations remain attributed to the definition using them. Thus
`def use(f=f()): ...` has a reference at the default expression but no invented
body call. Class member lookup and method dispatch are different: bare `f()` in a
method does not resolve to `C.f` just because that member exists.

This is deliberately not full Python dataflow or execution-order analysis.
Assignments/redefinitions are conservative unknowns. Global/nonlocal directives
make the affected name unresolved in that scope (with the directive's own line).
Lambda bodies and comprehension bodies are not analyzed; coverage says so. Lambda
defaults and the first comprehension iterable use the enclosing scope. Comprehension
iteration targets do not leak; walrus bindings conservatively block the containing
name. Generic type-parameter scopes, dynamic rebinding and inherited dispatch
remain unsupported.

## Independent fixture evaluation

The three fixture sets under `evaluation/fixtures` were authored independently of
examples/shop. `evaluation/expectations.json` was written from source before the
first scan. Its unchanged SHA-256 is recorded in the results. Labels cover every
fixture symbol; containers are excluded. Expected edges explicitly list source,
target, type, file and line; the evaluator also detects unexpected edges among
related symbols and checks endpoint methods/mounted paths. A separate AST pass
checks that the expected line contains the appropriate syntax category. Manual
source review establishes the alias meanings and symbol ownership; the AST check
alone would not prove semantic correctness.

| Fixture | Relevant | Unrelated | Found relevant | Missed | False positives | Edge checks |
|---|---:|---:|---:|---:|---:|---:|
| Orders/shared pricing | 4 | 2 | 4 | 0 | 0 | 3 |
| Inherited request/response models | 8 | 2 | 8 | 0 | 0 | 8 |
| Depends + aliases + nested prefixes | 4 | 2 | 4 | 0 | 0 | 5 |

Precision and recall are 1.0 **only for these labeled fixtures**. There are no
missing expected relations, unexpected related-symbol relations, incorrect evidence
lines or missing expected endpoints. Labels are human-authored in this repository,
not independently audited external ground truth.

```bash
.venv/bin/python scripts/evaluate_independent.py
```

This generates `.change-radar/independent/{orders,inheritance,auth}.{html,json,md}`.
[Machine-readable results](independent-evaluation.json).

## Public repository evaluation

The independent public project was actually fetched and scanned, without dependency
installation, imports or target execution:

- Repository: [fastapi/full-stack-fastapi-template](https://github.com/fastapi/full-stack-fastapi-template)
- Commit: `b1125d8839482cb7bbae603ddc6d0081bf87532e`
- Root: `backend`; 40 Python files, all 40 parsed with Python 3.14.4.
- Source was read and `evaluation/public-expectations.json` written before the scan.
  This is a **partial labeled universe**, with outside-universe discoveries reported
  separately; they are not automatically called false positives.

Manually confirmed chains, with pinned source evidence:

1. [ItemCreate inherits ItemBase (models.py:76)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/models.py#L76)
   → [create_item consumes ItemCreate (items.py:63)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/api/routes/items.py#L63).
   Both relations were found with the expected type, path and exact line.
2. [ItemPublic inherits ItemBase (models.py:97)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/models.py#L97)
   → [read_item response_model (items.py:48)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/api/routes/items.py#L48).
   Both relations were found; the same model also reaches create/update response contracts.
3. [ItemsPublic contains list[ItemPublic] (models.py:104)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/models.py#L104)
   → [read_items response_model (items.py:13)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/api/routes/items.py#L13).
   The composition edge is missing, so ItemBase does not reach this collection endpoint.
4. [CurrentUser alias with Depends (deps.py:49)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/api/deps.py#L49)
   → [read_item parameter (items.py:49)](https://github.com/fastapi/full-stack-fastapi-template/blob/b1125d8839482cb7bbae603ddc6d0081bf87532e/backend/app/api/routes/items.py#L49).
   The alias chain is not expanded; this is a demonstrated miss, not a safety result.

| Seed | Labeled relevant found | Missed | Labeled false positives | Scoped precision | Scoped recall |
|---|---:|---:|---:|---:|---:|
| ItemBase | 7/10 | 3 | 0 | 1.0 | 0.70 |
| get_current_user | 1/8 (seed only) | 7 | 0 | 1.0 | 0.125 |

Seven of eight predeclared model edges were found, all at the expected source lines.
The missing edge is ItemsPublic→ItemPublic composition. ItemBase also misses the
session.get(Item, ...) consumer delete_item because arbitrary argument references
and instance dispatch are not resolved. The dependency-alias scenario demonstrates
that direct Depends support is not general FastAPI dependency resolution.
The runtime API prefix is settings.API_V1_STR; all 23 extracted routes report an
unknown mounted path, rather than guessing it. Coverage explicitly identifies
unresolved bases, Annotated aliases, class field annotations and comprehensions.
[Full measured results](public-evaluation.json).

To reproduce (network is used only to fetch source; Python 3.14 is needed for this
pinned upstream syntax):

```bash
git clone https://github.com/fastapi/full-stack-fastapi-template.git /tmp/radar-public-checkout
git -C /tmp/radar-public-checkout checkout --detach b1125d8839482cb7bbae603ddc6d0081bf87532e
.venv/bin/python scripts/evaluate_public.py /tmp/radar-public-checkout
```

The evaluator refuses another commit or a dirty checkout. It reports misses without
failing the process: it is a measurement of known limitations, not an all-supported
fixture gate. Public source is not copied into this project.

## Browser and hosted CI limitations

Browser setup was attempted through the Browser skill. It returned “No browser is
available”; discovery returned `[]`. Search/filter/selection/evidence/download/
offline file-opening interaction tests therefore **were not run**. JavaScript
syntax, embedded export content and injection boundaries are checked separately;
these do not establish visual or interactive correctness.

The prior published baseline's [hosted CI run](https://github.com/ilyanozary/change-radar/actions/runs/39814520481)
failed before any steps ran. GitHub's annotation says the account is locked due to
a billing issue. It is not a test failure in the analyzer. The hosted result for the revised workflow must be checked separately; the earlier
run does not validate this revision. Local validation is recorded in
[VALIDATION.md](VALIDATION.md).

The metrics and unsupported-pattern descriptions above record the 4e4d15c review. The current experimental candidate adds two patterns; see [PREVIEW.md](PREVIEW.md) for updated support and the same-ground-truth comparison.
