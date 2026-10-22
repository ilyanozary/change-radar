# Contributing

Start with the README and docs/ANALYSIS.md. Run `python -m unittest discover -s tests -v` and `python scripts/evaluate.py` in the installed environment. Add a minimal repository fixture and a behavioral assertion for analyzer changes; preserve the no-target-execution rule. Label heuristics, expose unsupported patterns, and include path/line evidence for new relations.

Keep changes focused, deterministic, and offline. Do not embed secrets or source excerpts in reports. Update documented support boundaries when adding a resolver pattern. The evaluation is a small labeled demo, not a general benchmark.

The project owner still needs to select a license and copyright holder before public distribution; no license grant is implied by this checkout.
