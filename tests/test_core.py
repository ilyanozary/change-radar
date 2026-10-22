import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from change_radar.cli import install
from change_radar.core import diff, impact, scan
from change_radar.report import render


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="رادار space ")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, path, text):
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def git(self, *args):
        return subprocess.run(
            ["git", "-C", str(self.root), *args], check=True, capture_output=True
        ).stdout

    def test_relative_alias_reexport_src_and_transitive(self):
        self.write("src/pkg/__init__.py", "from .service import work as exported\n")
        self.write("src/pkg/service.py", "def work(): return 1\n")
        self.write(
            "src/pkg/api.py",
            "from . import exported as run\ndef endpoint(): return run()\n",
        )
        g = scan(self.root)
        r = impact(g, ["src/pkg/service.py::work"])
        self.assertIn("src/pkg/api.py::endpoint", {i["id"] for i in r["impact"]})
        e = next(
            e
            for e in g["edges"]
            if e["source"].endswith("::endpoint") and e["type"] == "calls"
        )
        self.assertEqual(e["evidence"], {"path": "src/pkg/api.py", "line": 2})

    def test_cycle_depth_limit(self):
        self.write("a.py", "from b import b\ndef a(): return b()\n")
        self.write("b.py", "from a import a\ndef b(): return a()\n")
        g = scan(self.root)
        self.assertEqual(len(impact(g, ["a.py::a"], 0)["impact"]), 1)
        self.assertTrue(impact(g, ["a.py::a"], 0)["truncated"])
        self.assertLess(len(impact(g, ["a.py::a"], 20)["impact"]), 10)
        self.assertEqual(len(impact(g, ["a.py"], limit=1)["impact"]), 1)

    def test_parse_errors_and_no_execution(self):
        self.write("bad.py", "def (\n")
        self.write("good.py", "raise RuntimeError('MUST NOT RUN')\ndef f(): pass\n")
        g = scan(self.root)
        self.assertEqual(g["coverage"]["parsed"], 1)
        self.assertIn("good.py::f", {n["id"] for n in g["nodes"]})
        self.assertEqual(g["coverage"]["issues"][0]["category"], "parse_error")

    def test_ambiguity(self):
        self.write("src/pkg.py", "def f(): pass\n")
        self.write("pkg.py", "def f(): pass\n")
        self.write("caller.py", "import pkg\nfrom pkg import missing\nimport unknown\n")
        g = scan(self.root)
        self.assertIn(
            "ambiguous_import", {i["category"] for i in g["coverage"]["issues"]}
        )
        self.assertFalse(any(e["type"] == "imports" for e in g["edges"]))

    def test_shadowed_function_not_resolved(self):
        self.write("a.py", "def f(): pass\ndef use(f): return f()\n")
        self.assertFalse(any(e["type"] == "calls" for e in scan(self.root)["edges"]))

    def test_exclude_symlink_gitignore(self):
        self.git("init", "-q")
        self.write(".gitignore", "ignored.py\nnested/\n!keep.py\n")
        self.write("ignored.py", "x=1")
        self.write("keep.py", "x=1")
        self.write("skip.py", "x=1")
        self.write("nested/a.py", "x=1")
        (self.root / "link.py").symlink_to("/etc/passwd")
        g = scan(self.root, ["skip.py"])
        self.assertEqual([n["path"] for n in g["nodes"]], ["keep.py"])

    def test_unicode_path_determinism(self):
        self.write("پوشه space/نمونه.py", "def hello(): pass\n")
        self.assertEqual(scan(self.root), scan(self.root))
        self.assertEqual(len(scan(self.root)["nodes"]), 2)

    def test_fastapi_models_dependencies_prefix_and_alias(self):
        self.write("models.py", "class Model: pass\ndef dep(): pass\n")
        self.write(
            "routes.py",
            "from fastapi import APIRouter as R, Depends as D\nfrom models import Model, dep\nr=R(prefix='/auth')\n@r.post('/login', response_model=Model)\ndef login(body: Model, user=D(dep)): pass\n",
        )
        self.write(
            "main.py",
            "from fastapi import FastAPI as F\nfrom routes import r\na=F()\na.include_router(r,prefix='/v1')\n",
        )
        g = scan(self.root)
        self.assertEqual(g["endpoints"][0]["path"], "/v1/auth/login")
        self.assertIn(
            "routes.py::login",
            {x["id"] for x in impact(g, ["models.py::Model"])["impact"]},
        )
        self.assertTrue(
            any(
                e["type"] == "depends" and e["target"] == "models.py::dep"
                for e in g["edges"]
            )
        )

    def test_fake_decorator_and_dynamic_prefix(self):
        self.write(
            "a.py",
            "from fastapi import APIRouter\nr=APIRouter(prefix=dynamic)\n@r.get('/x')\ndef f(): pass\n@other.get('/fake')\ndef fake(): pass\n",
        )
        g = scan(self.root)
        self.assertEqual(len(g["endpoints"]), 1)
        self.assertIsNone(g["endpoints"][0]["path"])

    def test_git_modes_deleted_rename_untracked(self):
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test")
        self.write("old.py", "def f(): pass\n")
        self.git("add", ".")
        self.git("commit", "-qm", "initial")
        self.git("mv", "old.py", "new.py")
        self.write("untracked.py", "x=1")
        staged = diff(self.root, "staged")
        self.assertIn({"status": "D", "path": "old.py"}, staged)
        self.assertIn({"status": "A", "path": "new.py"}, staged)
        self.assertIn({"status": "?", "path": "untracked.py"}, diff(self.root))
        self.assertEqual(diff(self.root, "base", "HEAD"), staged)
        with self.assertRaises(ValueError):
            diff(self.root, "base", "--help")

    def test_html_injection_and_source_privacy(self):
        self.write("a.py", "secret='do-not-embed-this-value'\ndef f(): pass\n")
        r = impact(
            scan(self.root),
            ["a.py::f"],
            request="</script><img src=x onerror=alert(1)>",
        )
        html = render(r)
        self.assertNotIn("</script><img", html)
        self.assertNotIn("do-not-embed-this-value", html)
        payload = html.split('<script id="data" type="application/json">')[1].split(
            "</script>"
        )[0]
        self.assertEqual(json.loads(payload)["request"], r["request"])

    def test_installer_dry_run_and_conflict(self):
        d = install("codex", "project", self.root, True)
        p = Path(d["destination"])
        self.assertFalse(p.exists())
        install("codex", "project", self.root)
        p.write_text("user data")
        self.assertTrue(install("codex", "project", self.root, True)["conflict"])
        with self.assertRaises(ValueError):
            install("codex", "project", self.root)
        self.assertEqual(p.read_text(), "user data")

    def test_rescan_change_delete_rename(self):
        p = self.write("a.py", "def before(): pass\n")
        self.assertEqual(len(scan(self.root)["nodes"]), 2)
        p.write_text("def after(): pass\n")
        self.assertIn("a.py::after", {n["id"] for n in scan(self.root)["nodes"]})
        p.rename(self.root / "b.py")
        self.assertNotIn("a.py", {n["id"] for n in scan(self.root)["nodes"]})
        (self.root / "b.py").unlink()
        self.assertEqual(scan(self.root)["nodes"], [])

    def test_gitignore_without_repository(self):
        self.write(".gitignore", "secret.py\n")
        self.write("secret.py", "def f(): pass\n")
        self.write("safe.py", "def f(): pass\n")
        g = scan(self.root)
        self.assertTrue(g["coverage"]["gitignore_applied"])
        self.assertNotIn("secret.py", {n["id"] for n in g["nodes"]})
        self.assertFalse((self.root / ".git").exists())

    def test_endpoint_test_candidates_are_heuristic(self):
        self.write(
            "api.py",
            "from fastapi import FastAPI\na=FastAPI()\n@a.get('/items')\ndef items(): pass\n",
        )
        self.write(
            "tests/test_items.py", "def test_items():\n    client.get('/items')\n"
        )
        r = impact(scan(self.root), ["api.py::items"])
        candidate = next(
            t for t in r["suggested_tests"] if t["id"].endswith("::test_items")
        )
        self.assertEqual(candidate["evidence"], "endpoint_literal_candidate")
        self.assertEqual(candidate["chain"][0]["certainty"], "heuristic")

    def test_rebound_and_scoped_imports_do_not_invent_calls(self):
        self.write("lib.py", "def f(): pass\n")
        self.write(
            "a.py",
            "from lib import f\nf = unknown\ndef use(): return f()\ndef scoped():\n    from lib import f\n    return f()\n",
        )
        g = scan(self.root)
        self.assertFalse(any(e["type"] == "calls" for e in g["edges"]))
        self.assertIn(
            "scoped_or_conditional_import",
            {i["category"] for i in g["coverage"]["issues"]},
        )

    def test_installer_preserves_symlink(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.root / ".agents").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                install("codex", "project", self.root)
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_conditional_definition_is_coverage_not_scan_failure(self):
        self.write("a.py", "if flag:\n    def conditional(): pass\ndef good(): pass\n")
        self.write("bad.py", "def (")
        self.write("b.py", "from bad import missing\ndef b(): return missing()\n")
        g = scan(self.root)
        self.assertIn("a.py::good", {n["id"] for n in g["nodes"]})
        self.assertIn(
            "conditional_definition", {i["category"] for i in g["coverage"]["issues"]}
        )

    def test_scoped_import_shadows_module_function(self):
        self.write(
            "a.py",
            "def f(): pass\ndef use():\n    from external import f\n    return f()\n",
        )
        self.assertFalse(any(e["type"] == "calls" for e in scan(self.root)["edges"]))

    def test_src_named_module_is_not_a_layout_directory(self):
        self.write("src.py", "def f(): pass\n")
        self.write("consumer.py", "from src import f\ndef g(): return f()\n")
        g = scan(self.root)
        self.assertIn(
            "consumer.py::g", {x["id"] for x in impact(g, ["src.py::f"])["impact"]}
        )

    def test_submodule_import_points_to_submodule(self):
        self.write("pkg/__init__.py", "")
        self.write("pkg/service.py", "def f(): pass\n")
        self.write(
            "consumer.py", "import pkg.service\ndef use(): return pkg.service.f()\n"
        )
        g = scan(self.root)
        self.assertTrue(
            any(
                e["type"] == "imports" and e["target"] == "pkg/service.py"
                for e in g["edges"]
            )
        )
        self.assertTrue(
            any(
                e["type"] == "calls" and e["target"] == "pkg/service.py::f"
                for e in g["edges"]
            )
        )

    def test_known_router_rebinding_not_treated_as_fastapi(self):
        self.write(
            "a.py",
            "from fastapi import APIRouter\nr=APIRouter()\nr=other\n@r.get('/fake')\ndef f(): pass\n",
        )
        g = scan(self.root)
        self.assertEqual(g["endpoints"], [])
        self.assertIn(
            "rebound_router", {i["category"] for i in g["coverage"]["issues"]}
        )
