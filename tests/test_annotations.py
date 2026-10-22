"""Source-first positive/negative expectations for 0.1 annotation support."""

import tempfile
import unittest
from pathlib import Path

from change_radar.core import impact, scan


class AnnotationTests(unittest.TestCase):
    def graph(self, source, extra=None):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "case.py").write_text(source)
            for name, text in (extra or {}).items():
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(text)
            return scan(root)

    def reached(self, g, seed):
        return {x["id"] for x in impact(g, [seed], depth=12)["impact"]}

    def edge(self, g, source, target, kind, line):
        match = [
            e
            for e in g["edges"]
            if (e["source"], e["target"], e["type"]) == (source, target, kind)
        ]
        self.assertEqual(len(match), 1)
        self.assertEqual(
            match[0]["evidence"], {"path": source.split("::")[0], "line": line}
        )
        self.assertEqual(match[0]["certainty"], "observed")

    def test_annotated_alias_imports_keyword_and_evidence(self):
        for origin in ("typing", "typing_extensions"):
            for dependency in ("D(current_user)", "D(dependency=current_user)"):
                with self.subTest(origin=origin, dependency=dependency):
                    g = self.graph(
                        f'from {origin} import Annotated as A\nfrom fastapi import Depends as D, FastAPI\ndef current_user(): pass\nCurrentUser = A[str, {dependency}]\napp = FastAPI()\n@app.get("/me")\ndef me(user: CurrentUser): pass\n@app.get("/other")\ndef other(user: CurrentUser): pass\n'
                    )
                    self.assertTrue(
                        {"case.py::me", "case.py::other"}
                        <= self.reached(g, "case.py::current_user")
                    )
                    self.edge(
                        g, "case.py::CurrentUser", "case.py::current_user", "depends", 4
                    )
                    self.edge(g, "case.py::me", "case.py::CurrentUser", "annotation", 7)

    def test_alias_cross_file_module_import_and_reexport_chain(self):
        extra = {
            "pkg/dep.py": "from typing import Annotated\nfrom fastapi import Depends\ndef auth(): pass\nUser = Annotated[str, Depends(auth)]\n",
            "pkg/__init__.py": "from .dep import User as Exported\n",
        }
        g = self.graph(
            "import pkg\nAlias = pkg.Exported\ndef me(user: Alias): pass\n", extra
        )
        self.assertIn("case.py::me", self.reached(g, "pkg/dep.py::auth"))
        self.edge(g, "case.py::Alias", "pkg/dep.py::User", "annotation", 2)

    def test_chained_dependencies_and_forward_alias_chain(self):
        g = self.graph(
            "from typing import Annotated\nfrom fastapi import Depends\ndef token(): pass\nToken = Annotated[str, Depends(token)]\ndef current(user: Token): pass\nUser = Annotated[str, Depends(current)]\nAlias = Later\nLater = User\ndef me(user: Alias): pass\n"
        )
        self.assertIn("case.py::me", self.reached(g, "case.py::token"))
        self.edge(g, "case.py::current", "case.py::Token", "annotation", 5)

    def test_direct_depends_keyword(self):
        g = self.graph(
            "from fastapi import Depends as D\ndef dep(): pass\ndef me(user=D(dependency=dep)): pass\n"
        )
        self.edge(g, "case.py::me", "case.py::dep", "depends", 3)

    def test_rebound_and_ambiguous_aliases_do_not_connect(self):
        for suffix in (
            "User = unknown\n",
            "if flag:\n    User = unknown\n",
            "def User(): pass\n",
        ):
            with self.subTest(suffix=suffix):
                g = self.graph(
                    "from typing import Annotated\nfrom fastapi import Depends\ndef dep(): pass\nUser = Annotated[str, Depends(dep)]\n"
                    + suffix
                    + "def me(user: User): pass\n"
                )
                self.assertNotIn("case.py::me", self.reached(g, "case.py::dep"))
                self.assertTrue(
                    any(
                        i["category"].startswith("unresolved_annotation")
                        for i in g["coverage"]["issues"]
                    )
                )

    def test_shadowed_alias_constructor_and_depends(self):
        for shadow in ("Annotated = unknown", "Depends = unknown"):
            with self.subTest(shadow=shadow):
                g = self.graph(
                    "from typing import Annotated\nfrom fastapi import Depends\ndef dep(): pass\n"
                    + shadow
                    + "\nUser = Annotated[str, Depends(dep)]\ndef me(user: User): pass\n"
                )
                self.assertNotIn("case.py::me", self.reached(g, "case.py::dep"))
        g = self.graph(
            "from typing import Annotated\nfrom fastapi import Depends\ndef dep(): pass\nUser = Annotated[str, Depends(dep)]\ndef outer(User):\n    def me(user: User): pass\n"
        )
        self.assertNotIn("case.py::outer.me", self.reached(g, "case.py::dep"))

    def test_cycles_dynamic_alias_and_unknown_dependency_are_visible(self):
        g = self.graph(
            "from typing import Annotated\nfrom fastapi import Depends\nA = B\nB = A\nDynamic = make_alias()\nUser = Annotated[str, Depends(factory())]\ndef me(a: A, b: Dynamic, c: User): pass\n"
        )
        categories = {i["category"] for i in g["coverage"]["issues"]}
        self.assertIn("unresolved_alias_cycle", categories)
        self.assertIn("unresolved_dependency", categories)
        self.assertIn("unresolved_annotation", categories)
        self.assertFalse(any(e["type"] == "depends" for e in g["edges"]))

    def test_metadata_does_not_invent_annotation_dependencies(self):
        g = self.graph(
            "from typing import Annotated\nclass Item: pass\nclass Page:\n    field: Annotated[str, Item]\n"
        )
        self.assertFalse(
            any(
                e["source"] == "case.py::Page" and e["target"] == "case.py::Item"
                for e in g["edges"]
            )
        )

    def test_field_containers_optional_union_and_annotated(self):
        for expression in (
            "Item",
            "list[Item]",
            "set[Item]",
            "tuple[Item, ...]",
            "dict[str, Item]",
            "Optional[Item]",
            "Union[Item, None]",
            "Item | None",
            'Annotated[list[Item], "metadata"]',
            '"Item"',
        ):
            with self.subTest(expression=expression):
                g = self.graph(
                    "from typing import Annotated, Optional, Union\nclass Item: pass\nclass Page:\n    items: "
                    + expression
                    + "\ndef listing() -> Page: pass\n"
                )
                self.edge(g, "case.py::Page", "case.py::Item", "annotation", 4)
                self.assertIn("case.py::listing", self.reached(g, "case.py::Item"))

    def test_field_cross_file_alias_inheritance_and_response(self):
        g = self.graph(
            'from pydantic import BaseModel\nfrom other import Item as Product\nfrom fastapi import FastAPI\nclass Page(BaseModel):\n    items: list[Product]\nclass Child(Page): pass\napp = FastAPI()\n@app.get("/items", response_model=Child)\ndef listing(): pass\n',
            {"other.py": "class Item: pass\n"},
        )
        self.edge(g, "case.py::Page", "other.py::Item", "annotation", 5)
        self.assertIn("case.py::listing", self.reached(g, "other.py::Item"))

    def test_recursive_fields_and_quoted_refs_are_bounded(self):
        g = self.graph(
            'class Left:\n    right: "Right"\nclass Right:\n    left: "Left"\ndef endpoint() -> Left: pass\n'
        )
        self.edge(g, "case.py::Left", "case.py::Right", "annotation", 2)
        self.edge(g, "case.py::Right", "case.py::Left", "annotation", 4)
        result = impact(g, ["case.py::Left"], depth=12)
        self.assertFalse(result["truncated"])
        self.assertIn("case.py::endpoint", {x["id"] for x in result["impact"]})

    def test_dynamic_unknown_generics_and_executable_strings_not_guessed(self):
        for expression in (
            "Custom[Item]",
            "factory(Item)",
            '"factory(Item)"',
            '"Missing"',
        ):
            with self.subTest(expression=expression):
                g = self.graph(
                    "class Item: pass\nclass Page:\n    items: " + expression + "\n"
                )
                self.assertFalse(
                    any(
                        e["source"] == "case.py::Page"
                        and e["target"] == "case.py::Item"
                        for e in g["edges"]
                    )
                )
                self.assertTrue(
                    any(
                        i["category"] == "unresolved_annotation"
                        for i in g["coverage"]["issues"]
                    )
                )

    def test_shadowed_container_and_local_model_name_are_unknown(self):
        for binding in ("list = unknown", "Item = unknown"):
            with self.subTest(binding=binding):
                g = self.graph(
                    "class Item: pass\n"
                    + binding
                    + "\nclass Page:\n    items: list[Item]\n"
                )
                self.assertFalse(
                    any(
                        e["source"] == "case.py::Page"
                        and e["target"] == "case.py::Item"
                        for e in g["edges"]
                    )
                )
                self.assertTrue(
                    any(
                        i["category"] == "unresolved_annotation"
                        for i in g["coverage"]["issues"]
                    )
                )

    def test_dependency_unpacking_is_not_guessed(self):
        for call in (
            "D(dep, **options)",
            "D(dependency=dep, **options)",
            "D(dep, dependency=other)",
            "D(*factories)",
        ):
            with self.subTest(call=call):
                g = self.graph(
                    "from typing import Annotated\nfrom fastapi import Depends as D\ndef dep(): pass\nUser=Annotated[str, "
                    + call
                    + "]\ndef me(user: User): pass\n"
                )
                self.assertNotIn("case.py::me", self.reached(g, "case.py::dep"))
                self.assertTrue(
                    any(
                        i["category"] == "unresolved_dependency"
                        for i in g["coverage"]["issues"]
                    )
                )

    def test_module_imports_and_imported_typing_wrappers(self):
        g = self.graph(
            "import typing as t\nimport fastapi as fa\nimport data as models\ndef dep(): pass\nUser=t.Annotated[str, fa.Depends(dependency=dep)]\nclass Page:\n    items: t.Optional[t.List[models.Item]]\ndef me(user: User) -> Page: pass\n",
            {"data.py": "class Item: pass\n"},
        )
        self.assertIn("case.py::me", self.reached(g, "case.py::dep"))
        self.edge(g, "case.py::Page", "data.py::Item", "annotation", 7)
