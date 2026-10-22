# Browser acceptance · not performed

On 2026-10-23 the Browser runtime returned “No browser is available”; discovery
returned []. No search/filter/selection/download/visual/console behavior is claimed
verified. JavaScript syntax/content checks are separate, not substitutes.

Generate actual reports with `python scripts/preview.py`, then use a real desktop
browser. In developer tools enable offline network mode and open the file:// HTML
again; report operation must not require a server or network request.

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

JSON and Markdown files accompany the reports to compare browser downloads. The
large/incomplete cases come from temporary source fixtures generated and scanned
by the script, not manually fabricated graphs. Record browser version, file path,
actions, observed failures and any console messages when completing this checklist.
