# Browser acceptance · verified with Playwright

On 2026-10-23, 16/16 real browser checks passed using Playwright 1.64.1 and
Chrome 148.0.7778.215 on Linux. A fresh headless context opened file:// reports
with offline=True. No page network requests, console errors or uncaught page errors
were observed. Downloads were saved and their actual JSON/Markdown contents checked.
This is browser interaction testing, separate from JavaScript syntax validation.

The connected Browser runtime had no browser available. This run instead launched
installed Chrome directly through Playwright, without a personal browser profile.

## Reproduce

```bash
python -m pip install -e '.[browser-test]'
python scripts/browser_smoke.py --browser-executable /usr/bin/google-chrome
```

Results, failure screenshots, desktop/evidence/mobile screenshots and downloaded
exports are written to `.change-radar/browser/`. The script regenerates all six
preview reports from source before testing. See [recorded results](browser-validation.json).
The browser executable must already be installed. The optional dependency is for
testing only; the application still has no runtime dependencies.

## Failures reproduced and corrected

With the final assertions against the original template, 12/16 checks passed
([recorded baseline](browser-baseline.json)).
Edge selection and composition witness checks failed because background pointer
capture stole clicks on SVG edges. Stopping pointerdown propagation on edges fixes
actual mouse selection and opens the correct evidence inspector.

Large-graph and narrow-screen checks failed because filters retained the previous
scale, making a single search result tiny. Filters and focus now refit the visible
nodes using their bounds. Tests require a single filtered node to render at least
150 pixels wide. Run the command above against the original template at 7344e47
to reproduce these failures; the corrected template passes all 16 checks.

## Exercised behavior

| Report/action | Expected acceptance observation |
|---|---|
| auth.html | DEMO badge; read_token seed; /v1/shop/items and /v1/shop/me affected; health absent |
| Search CurrentUser | Only matching alias node(s) remain; clear search to restore |
| Node type alias; relation annotation/depends | Actual alias/consumer/dependency edges filter correctly |
| Select alias and endpoint nodes | Inspector shows kind/path/line and the reached evidence chain |
| Select an edge | Inspector shows source→target, observed, python-ast and exact path:line |
| models.html | Item → Page → listing impact, with Page.items line 9 evidence |
| Pan background; wheel zoom; drag node; reset/focus | Graph remains usable, arrows point consumer→dependency; labels stay readable |
| Certainty observed/heuristic | HTTP literal candidate remains heuristic; annotation/depends edges remain observed |
| Export JSON | Download parses as JSON; suggested_tests evidence is endpoint_literal_candidate for HTTP match |
| Export Markdown | Same evidence label and evidence locations as CLI Markdown; no invented graph_reference label |
| empty.html | Clear empty state; no assertion that change is safe |
| limited.html | Analysis cap=3 and traversal incomplete warning; no full-coverage claim |
| incomplete.html | Intentional broken.py parse error, parsed<files and partial coverage warning |
| large.html | Actual generated-source consumers; viewport displays at most 70 nodes; search narrows remaining results |
| Console and narrow screen | No uncaught errors; inspector and controls usable; no unintended network requests |


The model check inspects Page's annotation witness and the response_model edge.
Listing also directly calls Item, so its shortest impact chain need not pass Page.
Actual pointer clicks, wheel/drag interactions and browser download events are used.

Only headless Chrome/Linux was tested, at desktop 1440×1000 and narrow 390×844
viewports. Firefox, Safari, headed human usability review and other platforms remain
unverified. A full large graph can initially have small labels; search, focus and
zoom provide a readable subset. This does not establish general large-graph usability.
