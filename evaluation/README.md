# Independent fixture evaluation

These three small repositories are separate from examples/shop. Expectations in
expectations.json were written by reading fixture source before the first scan;
no analyzer output was used to generate the labels. All declared symbols are
labeled relevant or unrelated; file containers are excluded from metrics.

Edge expectations specify consumer, dependency, type, source path and exact AST
line. The evaluator also checks the expected endpoint methods and mounted paths.
These examples are independently authored fixtures, not an external benchmark.
They are analysis targets: do not import or run them to perform evaluation.

Run `python scripts/evaluate_independent.py` after installing Change Radar.

The evaluator also checks unexpected relations among labeled related symbols.
A separate AST pass checks syntax categories on expected evidence lines; manual
source review determines actual target/alias meaning. See docs/CORRECTNESS_REVIEW.md
for the independently fetched public project and its measured misses.
