# Reproducible evaluation

Run from an installed checkout:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/evaluate.py
.venv/bin/python scripts/demo.py
```

[Recorded machine-readable results](evaluation.json) contain the labels, discovered/missed/false-positive sets, outside-ground-truth discoveries and measured timings. The evaluator fails if a labeled expected symbol is missed or a labeled unrelated symbol is included.

The scope is **only the explicitly labeled symbols of examples/shop**, with whole-symbol seeds and depth six. The labels specify 4 relevant/4 unrelated symbols for OTP, 6/3 for response model, and 10/3 for shared normalization. Containers are excluded from symbol metrics. The fixed evaluation yielded precision 1.0 and recall 1.0 in each scenario; this is not a repository-wide or general accuracy claim. The matched HTTP test is included as a heuristic candidate, not a proven test dependency. A test evaluator must inspect evidence types as well as the aggregate numbers.

The response scenario seeds the entire Session class; it does not evaluate exact field access or serialized aliases. Test results report analysis behavior, not application correctness. Expected sets and fixtures live in the same repository and are not an independent external benchmark. Broader real-project ground truth remains needed.

The separate behavioral tests cover relative aliases/reexports, root/src collisions, a module actually named src.py, cycles, depth/node caps, parse errors, conditional definitions, shadowing, scoped imports, Unicode/spaced paths, Git ignore rules inside/outside a repository, excludes/symlinks, FastAPI aliases/prefixes/Depends/shared models, dynamic routes, heuristic HTTP test candidates, Git staged/deleted/renamed/untracked/base states, HTML injection and source-value non-disclosure, installer dry-run/conflicts/symlinks, and content-change/delete/rename rescans.

There is no cache. The benchmark records one initial process scan and the median of five repeated full scans over eight Python files. These are not OS-cache cold/warm claims. The recorded baseline is around 20 ms per scan in this shared Linux/Python 3.14 environment; exact observations are in JSON. CPU allocation and contention are uncontrolled, and no hardware throughput claim is made. This small workload does not justify a cache implementation; larger workloads remain unevaluated.

## Correctness follow-up

The original shop evaluation is retained and was rerun successfully. [Three independently authored fixture sets](independent-evaluation.json) and a [pinned external public-project evaluation](public-evaluation.json) now supplement it. Their labels were written from source before scanning; [CORRECTNESS_REVIEW.md](CORRECTNESS_REVIEW.md) records the protocol, misses, exact relation evidence and reproduction commands. The public evaluation found substantial recall gaps, so the original shop precision/recall must not be generalized.
