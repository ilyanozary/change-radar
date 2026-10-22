# Analysis contract and architecture

## Supported patterns

| Area | Implemented | Boundary / manual review |
|---|---|---|
| Discovery | Python files; root and src layouts; sorted paths; excludes; Git ignore matcher | Skips all symlink files/directories, even internal ones; no arbitrary language support |
| Ignore matching | Git `check-ignore --no-index` with NUL stdin; nested rules and negation | Outside Git: temporary bare metadata outside target. Without Git: explicitly false `gitignore_applied`; ignores not applied |
| Imports | Module-level absolute, relative, aliases, package __init__, simple chained reexports | Scoped/conditional and wildcard imports unresolved; namespace layout beyond root/src not configured |
| Symbols | Functions, async functions, classes, methods, directly nested definitions; path::qualified name, start/end lines | Conditional definitions and overload/redefinition identity not modeled |
| Calls | Direct lexical names, imported names and module-qualified references; explicit class attributes | No instance dispatch/self inference, inherited dispatch, closures with complex shadowing, globals/nonlocals, monkeypatching, or dataflow analysis |
| FastAPI objects | Imported aliases of FastAPI/APIRouter; direct module assignment | Factories, rebinding, imported decorator routers, class-based routes, add_api_route unsupported |
| Routes | HTTP decorator methods, literal route and router/include prefixes, multiple/nested direct mounts | Unknown prefix/path = null and unresolved_route; unmounted routers show declared paths, not guaranteed deployed endpoints; conditional mounts not evaluated |
| Contracts | References to local classes in parameter/return annotations and response_model, including list subscripts | No field-level rename, inferred dict schema, string annotation resolution, validation aliases, or serialization semantics |
| Dependencies | Direct Depends aliases with resolvable argument, including annotations visited by AST | Dynamic factories and complex dependency overrides unresolved |
| Tests | Graph-connected test modules/functions, separately marked method+URL literal candidates | Heuristic URL match does not prove runtime client identity; no general text/name candidate search |
| Impact | Reverse breadth-first traversal, cycles controlled, depth/node caps, one shortest evidence chain | Does not enumerate every possible path; caps may omit relevant consumers |
| Git | Separate staged, unstaged (+untracked), base-to-working-tree modes | Whole-file seeds, not changed-line attribution; deleted files lack historical AST; rename = delete + add; untracked only unstaged |
| Cache | None; repeated scans reparse current files | No stale cache, no cache-clear command needed. Larger-repository cache evaluation remains future work |

## Relationship semantics

Arrows point from consumer/container to dependency/definition. `defines` identifies containment, `imports` a static import reference, `calls` a resolvable syntactic call, `annotation`/`response_model` contract references, `depends` dependency injection references, and `includes_router` a router mount reference. All use `origin: python-ast` and path:line evidence. `endpoint_literal` is explicitly `heuristic`; other supported relations are `observed` syntactic references. Runtime reachability is never asserted. Reached consumers are inferred; file containers are `containing_scope`.

Unknown imports are labeled external_or_unresolved rather than assuming packages are installed. Ambiguous duplicate root/src modules remain unresolved. Parse errors do not abort the scan; error text/source lines are excluded to avoid leaking source. Coverage includes parsed/skipped counts and review items. External library calls may appear as unresolved calls; this intentionally errs toward review instead of hiding coverage gaps.

## Design decisions

- Standard-library AST avoids executing target code and removes runtime installation dependencies. Installed Python controls the accepted grammar (3.11 cannot parse all newer syntax).
- Plain dictionaries and a versioned JSON boundary keep CLI, reports, skills and evaluation on one graph model. No database/service layer is justified yet.
- Two-pass router collection removes filesystem-order dependence. Imports resolve through module indexing with root/src collisions preserved as ambiguity.
- Standalone inline HTML/CSS/JS avoids Node and offline local-file fetch restrictions. All repository values enter the DOM as text, never innerHTML.
- BFS gives one reproducible explanatory path per result and bounded traversal. Graph rendering caps nodes separately; filtering does not expand analysis depth.
- No cache added: the recorded eight-file baseline does not establish a worthwhile cache benefit. Measure a representative larger workload before adding versioned cache complexity. Cold OS-cache performance is not measured.

IDs are stable for unchanged relative path and qualified symbol name; moving/renaming deliberately changes identity. Graph ordering is deterministic for an unchanged tree, installed Python, exclusions, Git ignore configuration and CLI inputs. Timing data is kept out of graph reports. Git's user/global exclude configuration may affect discovery.
