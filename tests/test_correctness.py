"""Regression expectations written before changing the original resolver."""

import json
import tempfile
import unittest
from pathlib import Path

from change_radar.core import impact, scan
from change_radar.report import markdown, render


class CorrectnessTests(unittest.TestCase):
    def graph(self, source, extra=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "case.py").write_text(source)
            for path, text in (extra or {}).items():
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            return scan(root)

    def calls(self, graph, owner):
        return {
            e["target"]
            for e in graph["edges"]
            if e["source"] == "case.py::" + owner and e["type"] == "calls"
        }

    def test_parameter_kinds(self):
        for signature, async_ in [
            (signature, async_)
            for signature in ("f", "*f", "**f", "f, /", "*, f")
            for async_ in ("", "async ")
        ]:
            with self.subTest(signature=signature, async_=async_):
                g = self.graph(
                    f"def f(): pass\n{async_}def use({signature}): return f()\n"
                )
                self.assertEqual(self.calls(g, "use"), set())
                self.assertTrue(
                    any(
                        i["category"] == "unresolved_call" and i["line"] == 2
                        for i in g["coverage"]["issues"]
                    )
                )

    def test_nested_bindings_do_not_pollute_outer(self):
        for inner in [
            "f = 1",
            "import external as f",
            "from external import f",
            "def f(): pass",
            "class f: pass",
            "class Nested:\n    f = 1",
        ]:
            with self.subTest(inner=inner):
                body = "\n".join("        " + line for line in inner.splitlines())
                g = self.graph(
                    "def f(): pass\ndef outer():\n    def inner():\n"
                    + body
                    + "\n    return f()\n"
                )
                self.assertEqual(self.calls(g, "outer"), {"case.py::f"})

    def test_closure_bindings_and_local_definition_shadow_module(self):
        g = self.graph(
            "def f(): pass\ndef outer(f):\n    def inner(): return f()\n    return inner()\n"
        )
        self.assertEqual(self.calls(g, "outer.inner"), set())
        self.assertEqual(self.calls(g, "outer"), {"case.py::outer.inner"})
        g = self.graph(
            "from lib import f\ndef outer():\n    def f(): pass\n    def inner(): return f()\n    return f()\n",
            {"lib.py": "def f(): pass\n"},
        )
        self.assertEqual(self.calls(g, "outer"), {"case.py::outer.f"})
        self.assertEqual(self.calls(g, "outer.inner"), {"case.py::outer.f"})

    def test_class_scope_is_not_method_lexical_parent(self):
        for imported in (False, True):
            with self.subTest(function_attribute_imported=imported):
                factory = "def factory():\n    def inner(): pass\n"
                source = (
                    "from lib import factory\n" if imported else factory
                ) + "def use(): return factory.inner()\n"
                g = self.graph(source, {"lib.py": factory} if imported else None)
                self.assertEqual(self.calls(g, "use"), set())

        g = self.graph(
            "def f(): pass\nclass C:\n    def f(): pass\n    def method(self): return f()\n"
        )
        self.assertEqual(self.calls(g, "C.method"), {"case.py::f"})

    def test_default_argument_uses_enclosing_scope(self):
        g = self.graph("def f(): pass\ndef use(f=f()): return f()\n")
        edges = [e for e in g["edges"] if e["type"] == "calls"]
        self.assertEqual(
            [(e["source"], e["target"], e["evidence"]["line"]) for e in edges],
            [("case.py::use", "case.py::f", 2)],
        )
        g = self.graph("def f(): pass\ndef outer(f):\n    def inner(x=f()): pass\n")
        self.assertEqual(self.calls(g, "outer.inner"), set())

    def test_global_nonlocal_uncertainty(self):
        for directive in ["global f", "nonlocal f"]:
            with self.subTest(directive=directive):
                binding = "    f = None\n" if directive == "nonlocal f" else ""
                g = self.graph(
                    f"def f(): pass\ndef outer():\n{binding}    def use():\n        {directive}\n        return f()\n"
                )
                self.assertEqual(self.calls(g, "outer.use"), set())
                self.assertTrue(
                    any(
                        i["category"] == "unresolved_scope_directive"
                        for i in g["coverage"]["issues"]
                    )
                )

    def test_lambda_and_comprehension_do_not_leak_bindings(self):
        for expression in [
            "lambda f: f()",
            "[f() for f in items]",
            "{f() for f in items}",
            "(f() for f in items)",
            "{f: f() for f in items}",
        ]:
            with self.subTest(expression=expression):
                g = self.graph(
                    "def f(): pass\ndef use():\n    value = "
                    + expression
                    + "\n    return f()\n"
                )
                edges = [
                    e
                    for e in g["edges"]
                    if e["source"] == "case.py::use"
                    and e["target"] == "case.py::f"
                    and e["type"] == "calls"
                ]
                self.assertEqual([e["evidence"]["line"] for e in edges], [4])

    def test_inheritance_alias_multiple_and_transitive(self):
        source = "from lib import Base as Parent\nclass Mixin: pass\nclass Child(Parent, Mixin): pass\nclass Grandchild(Child): pass\ndef use(): return Grandchild()\n"
        g = self.graph(source, {"lib.py": "class Base: pass\n"})
        edges = [e for e in g["edges"] if e["type"] == "inherits"]
        self.assertEqual(
            {(e["source"], e["target"], e["evidence"]["line"]) for e in edges},
            {
                ("case.py::Child", "lib.py::Base", 3),
                ("case.py::Child", "case.py::Mixin", 3),
                ("case.py::Grandchild", "case.py::Child", 4),
            },
        )
        self.assertTrue(
            all(
                e["origin"] == "python-ast" and e["evidence"]["path"] == "case.py"
                for e in edges
            )
        )
        self.assertIn(
            "case.py::use", {i["id"] for i in impact(g, ["lib.py::Base"])["impact"]}
        )

    def test_unresolved_bases_are_coverage(self):
        g = self.graph(
            "class Dynamic(factory()): pass\nclass Generic(Base[int]): pass\nclass Unknown(External): pass\n"
        )
        self.assertEqual(
            sum(i["category"] == "unresolved_base" for i in g["coverage"]["issues"]), 3
        )
        self.assertFalse(any(e["type"] == "inherits" for e in g["edges"]))

    def test_test_labels_survive_all_reports(self):
        g = self.graph(
            "from fastapi import FastAPI\na=FastAPI()\n@a.get('/items')\ndef items(): pass\n",
            {
                "tests/test_http.py": "def test_http(): client.get('/items')\n",
                "tests/test_direct.py": "from case import items\ndef test_direct(): items()\n",
            },
        )
        data = impact(g, ["case.py::items"])
        labels = {t["id"]: t["evidence"] for t in data["suggested_tests"]}
        self.assertEqual(
            labels["tests/test_http.py::test_http"], "endpoint_literal_candidate"
        )
        self.assertEqual(labels["tests/test_direct.py::test_direct"], "graph_reference")
        md = markdown(data)
        self.assertIn(
            "`tests/test_http.py::test_http` (endpoint_literal_candidate)", md
        )
        self.assertIn("`tests/test_direct.py::test_direct` (graph_reference)", md)
        html = render(data)
        payload = html.split('<script id="data" type="application/json">')[1].split(
            "</script>"
        )[0]
        self.assertEqual(
            json.loads(payload)["suggested_tests"], data["suggested_tests"]
        )

    def test_closure_assignment_shadows_and_nested_class_does_not(self):
        g = self.graph(
            "def f(): pass\ndef outer():\n    f = 1\n    def inner(): return f()\n"
        )
        self.assertEqual(self.calls(g, "outer.inner"), set())
        g = self.graph(
            "def f(): pass\ndef outer():\n    class Inner:\n        f = 1\n    return f()\n"
        )
        self.assertEqual(self.calls(g, "outer"), {"case.py::f"})

    def test_comprehension_iterator_and_walrus(self):
        g = self.graph(
            "def f(): pass\ndef use():\n    values = [f() for f in f()]\n    return f()\n"
        )
        edges = [
            e
            for e in g["edges"]
            if e["source"] == "case.py::use"
            and e["target"] == "case.py::f"
            and e["type"] == "calls"
        ]
        self.assertEqual([e["evidence"]["line"] for e in edges], [3, 4])
        g = self.graph(
            "def f(): pass\ndef use():\n    values = [(f := other) for x in values]\n    return f()\n"
        )
        self.assertEqual(self.calls(g, "use"), set())

    def test_module_comprehension_does_not_shadow_imported_function(self):
        g = self.graph(
            "from lib import f\ndef use(): return f()\n",
            {"lib.py": "def f(): pass\nvalues = [f for f in items]\n"},
        )
        self.assertEqual(self.calls(g, "use"), {"lib.py::f"})

    def test_shadowed_depends_alias_is_not_injection(self):
        g = self.graph(
            "from fastapi import Depends as D\ndef dep(): pass\ndef outer(D):\n    def inner(user=D(dep)): pass\n"
        )
        self.assertFalse(any(e["type"] == "depends" for e in g["edges"]))

    def test_conditional_import_cannot_reuse_unconditional_binding(self):
        g = self.graph(
            "from lib import f\nif flag:\n    from other import f\ndef use(): return f()\n",
            {"lib.py": "def f(): pass\n", "other.py": "def f(): pass\n"},
        )
        self.assertEqual(self.calls(g, "use"), set())

    def test_browser_markdown_export_keeps_test_labels(self):
        data = impact(self.graph("def f(): pass\n"), ["case.py::f"])
        data["suggested_tests"] = [
            {
                "id": "tests/test_http.py::test_http",
                "evidence": "endpoint_literal_candidate",
                "chain": [],
            }
        ]
        data["request"] = "__RADAR_MARKDOWN__ __RADAR_DATA__ </script>"
        html = render(data)
        # Test the downloadable text itself, not merely the input JSON payload.
        prefix = "const markdownReport = "
        self.assertIn(prefix, html)
        exported = json.JSONDecoder().raw_decode(html.split(prefix, 1)[1])[0]
        self.assertEqual(exported, markdown(data))
        self.assertIn("endpoint_literal_candidate", exported)
        payload = html.split('<script id="data" type="application/json">')[1].split(
            "</script>"
        )[0]
        self.assertEqual(json.loads(payload)["request"], data["request"])
