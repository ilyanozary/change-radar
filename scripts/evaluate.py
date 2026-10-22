"""Fixed symbol-level ground truth, not a general accuracy claim."""

import json
import platform
import statistics
import time
from pathlib import Path

from change_radar.core import impact, scan

root = Path(__file__).resolve().parents[1]
scenarios = {
    "otp": {
        "seed": "app/services.py::authenticate",
        "expected": [
            "app/services.py::authenticate",
            "app/routes.py::login",
            "tests/test_auth.py::test_login",
            "tests/test_api.py::test_login_contract",
        ],
        "unrelated": [
            "app/routes.py::me",
            "app/routes.py::session",
            "app/services.py::profile",
            "app/services.py::normalize_user",
        ],
    },
    "response": {
        "seed": "app/models.py::Session",
        "expected": [
            "app/models.py::Session",
            "app/services.py::authenticate",
            "app/routes.py::login",
            "app/routes.py::session",
            "tests/test_auth.py::test_login",
            "tests/test_api.py::test_login_contract",
        ],
        "unrelated": [
            "app/routes.py::me",
            "app/services.py::profile",
            "app/services.py::normalize_user",
        ],
    },
    "shared": {
        "seed": "app/services.py::normalize_user",
        "expected": [
            "app/services.py::normalize_user",
            "app/services.py::authenticate",
            "app/services.py::profile",
            "app/dependencies.py::current_user",
            "app/routes.py::login",
            "app/routes.py::me",
            "app/routes.py::session",
            "tests/test_auth.py::test_login",
            "tests/test_auth.py::test_normalize_user",
            "tests/test_api.py::test_login_contract",
        ],
        "unrelated": [
            "app/models.py::Profile",
            "app/models.py::LoginRequest",
            "app/models.py::Session",
        ],
    },
}
times = []
for _ in range(6):
    start = time.perf_counter()
    g = scan(root / "examples/shop")
    times.append(time.perf_counter() - start)
results = {}
for name, s in scenarios.items():
    r = impact(g, [s["seed"]], 6)
    discovered = {i["id"] for i in r["impact"] if "::" in i["id"]}
    expected = set(s["expected"])
    universe = expected | set(s["unrelated"])
    found = discovered & universe
    tp = found & expected
    fp = found - expected
    fn = expected - found
    results[name] = dict(
        **s,
        found=sorted(found),
        missed=sorted(fn),
        false_positive=sorted(fp),
        discovered_outside_ground_truth=sorted(discovered - universe),
        precision=len(tp) / (len(tp) + len(fp)) if tp or fp else None,
        recall=len(tp) / len(expected),
    )
output = dict(
    scope="Only explicitly labeled symbols in examples/shop, whole-symbol seeds, depth 6; field-level reasoning is not evaluated.",
    scenarios=results,
    benchmark=dict(
        files=g["coverage"]["files"],
        first_scan_seconds=times[0],
        repeat_scan_median_seconds=statistics.median(times[1:]),
        cache=False,
        python=platform.python_version(),
        platform=platform.platform(),
        processor=platform.processor(),
        note="First process scan, not an OS page-cache cold measurement; repeat scans reparse all files. Shared container resources; no hardware throughput claim.",
    ),
)
print(json.dumps(output, indent=2, sort_keys=True))
if any(s["missed"] or s["false_positive"] for s in results.values()):
    raise SystemExit(1)
