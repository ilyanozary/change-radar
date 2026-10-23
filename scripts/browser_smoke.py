"""Real offline browser interactions against generated reports (optional Playwright)."""

import argparse
import json
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--browser-executable",
        help="Fresh headless browser executable; never a personal profile",
    )
    parser.add_argument("--output", type=Path, default=ROOT / ".change-radar/browser")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/preview.py")],
        check=True,
        capture_output=True,
    )
    reports = ROOT / ".change-radar/preview"
    checks = []
    console_errors = []
    page_errors = []
    network = []
    with sync_playwright() as p:
        options = {"headless": True}
        if args.browser_executable:
            options["executable_path"] = args.browser_executable
        browser = p.chromium.launch(**options)
        context = browser.new_context(
            offline=True,
            accept_downloads=True,
            viewport={"width": 1440, "height": 1000},
        )
        page = context.new_page()
        page.set_default_timeout(4000)
        page.on("pageerror", lambda error: page_errors.append(str(error)))
        page.on(
            "console",
            lambda message: (
                console_errors.append(message.text) if message.type == "error" else None
            ),
        )
        page.on(
            "request",
            lambda request: (
                network.append(request.url)
                if request.url.startswith(("http:", "https:", "ws:", "wss:"))
                else None
            ),
        )

        def open_report(name="auth"):
            page.goto((reports / (name + ".html")).as_uri(), wait_until="load")
            expect(page.locator("#status")).not_to_have_text("Loading graph…")

        def node(name):
            return page.locator(f'g.node[aria-label="{name}"]')

        def check(name, action):
            try:
                action()
                checks.append({"name": name, "passed": True})
                print("PASS", name, flush=True)
            except Exception as error:
                checks.append(
                    {"name": name, "passed": False, "error": str(error)[:1400]}
                )
                page.screenshot(path=str(out / (name + "-failure.png")), full_page=True)
                print("FAIL", name, str(error)[:220], flush=True)

        def offline_load():
            open_report()
            expect(page).to_have_title("Change Radar · Evidence map")
            expect(page.locator("#mode")).to_contain_text("DEMO")
            expect(page.locator("#endpoints")).to_contain_text("/v1/shop/items")
            expect(page.locator("#endpoints")).to_contain_text("/v1/shop/me")
            expect(page.locator("#endpoints")).not_to_contain_text("/health")
            assert page.locator("g.node").count() > 0
            page.screenshot(path=str(out / "desktop.png"), full_page=True)

        check("offline-file-load", offline_load)

        def search():
            open_report()
            page.get_by_role("textbox", name="Search", exact=True).fill("CurrentUser")
            expect(page.locator("g.node")).to_have_count(1)
            expect(node("security.py::CurrentUser")).to_be_visible()
            page.get_by_role("textbox", name="Search", exact=True).fill(
                "no-such-symbol-927"
            )
            expect(page.locator("g.node")).to_have_count(0)
            expect(page.locator("#status")).to_contain_text("No matching nodes")

        check("search-and-no-match", search)

        def filters():
            open_report()
            page.get_by_label("Node type", exact=True).select_option("alias")
            expect(page.locator("g.node")).to_have_count(1)
            page.get_by_role("button", name="Reset view").click()
            page.get_by_label("Relationship", exact=True).select_option("depends")
            expect(page.locator("path.edge")).to_have_count(2)
            page.get_by_role("button", name="Reset view").click()
            page.get_by_label("Depth", exact=True).select_option("0")
            expect(page.locator("g.node")).to_have_count(1)
            expect(node("security.py::read_token")).to_be_visible()

        check("node-relation-depth-filters", filters)

        def evidence():
            open_report()
            node("routes.py::listing").click()
            expect(page.locator("#detail")).to_contain_text("security.py::read_token")
            expect(page.locator("#detail")).to_contain_text("security.py::CurrentUser")
            expect(page.locator("#detail")).to_contain_text("security.py:13")
            expect(page.locator("#detail")).to_contain_text("observed")
            page.screenshot(path=str(out / "evidence.png"), full_page=True)
            page.get_by_role("button", name="Focus selection").click()
            assert page.locator("g.node").count() < 10
            expect(node("routes.py::listing")).to_be_visible()

        check("node-evidence-chain-and-focus", evidence)

        def edge_selection():
            open_report()
            page.get_by_label("Relationship", exact=True).select_option("depends")
            # Real pointer input at the midpoint of a rendered SVG stroke. No
            # dispatchEvent/handler calls that could conceal pointer-capture bugs.
            point = page.locator("path.edge").first.evaluate(
                "(e)=>{const p=e.getPointAtLength(e.getTotalLength()/2); const s=new DOMPoint(p.x,p.y).matrixTransform(e.getScreenCTM());return {x:s.x,y:s.y}}"
            )
            page.mouse.click(point["x"], point["y"])
            expect(page.locator("#detail h2")).to_have_text("depends")
            expect(page.locator("#detail")).to_contain_text("python-ast")
            expect(page.locator("#detail")).to_contain_text("observed")

        check("edge-pointer-selection", edge_selection)

        def zoom_pan_drag():
            open_report()
            graph = page.locator("#graph").bounding_box()
            assert graph
            before = page.locator("#world").get_attribute("transform")
            page.mouse.move(graph["x"] + 30, graph["y"] + graph["height"] - 35)
            page.mouse.wheel(0, -250)
            expect(page.locator("#world")).not_to_have_attribute("transform", before)
            before = page.locator("#world").get_attribute("transform")
            page.mouse.down()
            page.mouse.move(graph["x"] + 85, graph["y"] + graph["height"] - 20, steps=5)
            page.mouse.up()
            expect(page.locator("#world")).not_to_have_attribute("transform", before)
            page.get_by_role("button", name="Reset view").click()
            alias = node("security.py::CurrentUser")
            box = alias.bounding_box()
            assert box
            original = alias.get_attribute("transform")
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] / 2 + 35,
                box["y"] + box["height"] / 2 + 20,
                steps=5,
            )
            page.mouse.up()
            expect(node("security.py::CurrentUser")).not_to_have_attribute(
                "transform", original
            )

        check("zoom-pan-node-drag", zoom_pan_drag)

        def certainty():
            open_report()
            page.get_by_label("Certainty", exact=True).select_option("heuristic")
            expect(page.locator("path.edge")).to_have_count(1)
            page.get_by_label("Certainty", exact=True).select_option("observed")
            assert page.locator("path.edge").count() > 1

        check("certainty-filter", certainty)

        def downloads():
            open_report()
            for button, filename in [
                ("Export JSON", "export.json"),
                ("Export Markdown", "export.md"),
            ]:
                with page.expect_download() as info:
                    page.get_by_role("button", name=button, exact=True).click()
                download = info.value
                assert download.failure() is None
                download.save_as(out / filename)
            data = json.loads((out / "export.json").read_text())
            assert data["seeds"] == ["security.py::read_token"]
            assert any(
                t["evidence"] == "endpoint_literal_candidate"
                for t in data["suggested_tests"]
            )
            assert {"observed", "heuristic"} <= {e["certainty"] for e in data["edges"]}
            md = (out / "export.md").read_text()
            assert "endpoint_literal_candidate" in md and "observed" in md
            assert "`tests/test_http.py::test_items` (graph_reference)" not in md

        check("real-json-markdown-downloads", downloads)

        def composition():
            open_report("models")
            node("models.py::Page").click()
            expect(page.locator("#detail")).to_contain_text("models.py::Item")
            expect(page.locator("#detail")).to_contain_text("models.py:9")
            expect(page.locator("#detail")).to_contain_text("annotation")
            # listing also constructs Item directly; its shortest node chain can
            # legitimately be calls, so inspect the actual response-model edge.
            page.get_by_label("Relationship", exact=True).select_option(
                "response_model"
            )
            point = page.locator("path.edge").first.evaluate(
                "(e)=>{const p=e.getPointAtLength(e.getTotalLength()/2);const s=new DOMPoint(p.x,p.y).matrixTransform(e.getScreenCTM());return {x:s.x,y:s.y}}"
            )
            page.mouse.click(point["x"], point["y"])
            expect(page.locator("#detail h2")).to_have_text("response_model")
            expect(page.locator("#detail")).to_contain_text("models.py::Page")
            expect(page.locator("#detail")).to_contain_text("routes.py:8")

        check("composition-witness", composition)

        def empty():
            open_report("empty")
            expect(page.locator("g.node")).to_have_count(0)
            expect(page.locator("#status")).to_contain_text("No matching nodes")
            expect(page.locator("footer")).to_contain_text(
                "Empty results do not establish safety"
            )

        check("empty-state", empty)

        def limited():
            open_report("limited")
            expect(page.locator("#status")).to_contain_text("Traversal incomplete")
            expect(page.locator("g.node")).to_have_count(3)

        check("analysis-result-cap", limited)

        def incomplete():
            open_report("incomplete")
            expect(page.locator("#status")).to_contain_text("Parse coverage incomplete")
            page.locator("summary").click()
            expect(page.locator("#issues")).to_contain_text("broken.py")
            expect(page.locator("#issues")).to_contain_text("parse_error")

        check("parse-error-incomplete-state", incomplete)

        def large():
            open_report("large")
            expect(page.locator("g.node")).to_have_count(70)
            page.get_by_role("textbox", name="Search", exact=True).fill("consumer_79")
            expect(page.locator("g.node")).to_have_count(1)
            expect(node("bulk.py::consumer_79")).to_be_visible()
            box = node("bulk.py::consumer_79").bounding_box()
            assert box and box["width"] >= 150, (
                "Filtered node remains too small to read"
            )

        check("viewport-cap-and-hidden-node-search", large)

        def small():
            page.set_viewport_size({"width": 390, "height": 844})
            open_report()
            assert page.evaluate(
                "document.documentElement.scrollWidth <= innerWidth + 1"
            )
            page.get_by_role("textbox", name="Search", exact=True).fill("CurrentUser")
            box = node("security.py::CurrentUser").bounding_box()
            assert box and box["width"] >= 150, (
                "Filtered mobile node remains too small to read"
            )
            node("security.py::CurrentUser").click()
            expect(page.locator("#detail")).to_contain_text("security.py:13")
            page.screenshot(path=str(out / "mobile.png"), full_page=True)
            page.set_viewport_size({"width": 1440, "height": 1000})

        check("narrow-screen-layout", small)
        check(
            "no-console-or-page-errors",
            lambda: assert_clean(console_errors, page_errors),
        )
        check("no-page-network-requests", lambda: assert_clean(network, []))
        result = dict(
            browser=browser.version,
            playwright=version("playwright"),
            offline=True,
            transport="file://",
            headless=True,
            checks=checks,
            console_errors=console_errors,
            page_errors=page_errors,
            network_requests=network,
        )
        (out / "results.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        )
        context.close()
        browser.close()
    passed = sum(c["passed"] for c in checks)
    print(
        f"{passed}/{len(checks)} browser checks passed; results: {out / 'results.json'}"
    )
    return 0 if passed == len(checks) else 1


def assert_clean(first, second):
    assert not first and not second, repr((first, second))


if __name__ == "__main__":
    raise SystemExit(main())
