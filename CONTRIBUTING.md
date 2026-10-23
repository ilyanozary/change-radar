# Contributing

Start with the README and docs/ANALYSIS.md. Run `python -m unittest discover -s tests -v` and `python scripts/evaluate.py` plus `python scripts/evaluate_independent.py` in the installed environment. Add a minimal repository fixture and a behavioral assertion for analyzer changes; preserve the no-target-execution rule. Label heuristics, expose unsupported patterns, and include path/line evidence for new relations.

Keep changes focused, deterministic, and offline. Do not embed secrets or source excerpts in reports. Update documented support boundaries when adding a resolver pattern. Write expected related/unrelated symbols and evidence before the first scan of a new fixture. Preserve scope boundaries when collecting bindings. The fixed fixtures and partial pinned public evaluation are not general accuracy benchmarks.

Change Radar is licensed under the [MIT License](LICENSE). Preserve applicable third-party copyright and license notices.
