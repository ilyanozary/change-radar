"""Conservative lexical bindings, without crossing child scope boundaries.

Bindings are symbols, module imports, or unknown values. This is not dataflow:
assignments, directives and ambiguous redefinitions intentionally block resolution.
"""

import ast
from dataclasses import dataclass, field


@dataclass
class Frame:
    kind: str
    parent: str | None
    names: dict = field(default_factory=dict)
    directives: dict = field(default_factory=dict)


class Bindings(ast.NodeVisitor):
    def __init__(self, frame, qualified, symbols, imports):
        self.frame = frame
        self.qualified = qualified
        self.symbols = symbols
        self.imports = imports

    def bind(self, name, value=None):
        if name in self.frame.names and (
            self.frame.names[name] != value or (value and value[0] == "symbol")
        ):
            self.frame.names[name] = None
        else:
            self.frame.names[name] = value

    def visit_Name(self, node):
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bind(node.id)

    def visit_FunctionDef(self, node):
        qual = (self.qualified + "." if self.qualified else "") + node.name
        symbol = self.symbols.get(qual)
        self.bind(node.name, ("symbol", symbol) if symbol else None)
        # Defaults/decorators execute in the defining scope; never enter the body.
        for value in node.args.defaults + [x for x in node.args.kw_defaults if x]:
            self.visit(value)
        for value in node.decorator_list:
            self.visit(value)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        qual = (self.qualified + "." if self.qualified else "") + node.name
        symbol = self.symbols.get(qual)
        self.bind(node.name, ("symbol", symbol) if symbol else None)
        for value in (
            node.bases + [k.value for k in node.keywords] + node.decorator_list
        ):
            self.visit(value)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.bind(
                name,
                ("import", self.imports[id(node)][name])
                if name in self.imports.get(id(node), {})
                else None,
            )

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname or alias.name
            self.bind(
                name,
                ("import", self.imports[id(node)][name])
                if name in self.imports.get(id(node), {})
                else None,
            )

    def visit_Global(self, node):
        self.frame.directives.update({name: node.lineno for name in node.names})

    visit_Nonlocal = visit_Global

    def visit_ExceptHandler(self, node):
        if node.name:
            self.bind(node.name)
        self.generic_visit(node)

    def visit_MatchAs(self, node):
        if node.name:
            self.bind(node.name)
        self.generic_visit(node)

    def visit_MatchStar(self, node):
        if node.name:
            self.bind(node.name)

    def visit_MatchMapping(self, node):
        if node.rest:
            self.bind(node.rest)
        self.generic_visit(node)

    def visit_Lambda(self, node):
        for value in node.args.defaults + [x for x in node.args.kw_defaults if x]:
            self.visit(value)

    def visit_ListComp(self, node):
        # Iteration targets belong to a separate implicit scope. Walrus bindings,
        # unlike targets, escape to the containing scope; block them conservatively.
        class Walrus(ast.NodeVisitor):
            def visit_NamedExpr(inner, expr):
                if isinstance(expr.target, ast.Name):
                    self.bind(expr.target.id)
                inner.generic_visit(expr)

            def visit_Lambda(inner, expr):
                return

        Walrus().visit(node)

    visit_SetComp = visit_ListComp
    visit_DictComp = visit_ListComp
    visit_GeneratorExp = visit_ListComp


def index_scopes(tree, symbols, imports):
    frames = {}

    def build(body, qual, kind, parent, args=None):
        frame = Frame(kind, parent)
        frames[qual] = frame
        collector = Bindings(frame, qual, symbols, imports if kind == "module" else {})
        if args:
            params = args.posonlyargs + args.args + args.kwonlyargs
            params += [a for a in (args.vararg, args.kwarg) if a]
            for arg in params:
                collector.bind(arg.arg)
        for stmt in body:
            collector.visit(stmt)
        for name in frame.directives:
            frame.names[name] = None
        for stmt in body:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                child = (qual + "." if qual else "") + stmt.name
                if child in symbols:
                    build(
                        stmt.body,
                        child,
                        "class" if isinstance(stmt, ast.ClassDef) else "function",
                        qual,
                        getattr(stmt, "args", None),
                    )

    build(tree.body, "", "module", None)
    return frames


def lookup_binding(frames, scope, first):
    initial = True
    while scope is not None:
        frame = frames[scope]
        if initial or frame.kind != "class":
            if first in frame.names:
                return scope, frame.names[first]
        initial = False
        scope = frame.parent
    return None


def import_reference(frames, scope, name):
    first, *tail = name.split(".")
    found = lookup_binding(frames, scope, first)
    if found and found[1] and found[1][0] == "import":
        return found[1][1] + ("." + ".".join(tail) if tail else "")
    return None


def resolve_lexical(frames, scope, name, global_resolver, node_ids):
    first, *tail = name.split(".")
    found = lookup_binding(frames, scope, first)
    if found:
        binding = found[1]
        if binding is None:
            return None
        kind, value = binding
        if kind == "import":
            return global_resolver(value + ("." + ".".join(tail) if tail else ""))
        if tail:
            for i in range(len(tail)):
                parent = value + ("." + ".".join(tail[:i]) if i else "")
                if parent not in node_ids or node_ids[parent]["kind"] != "class":
                    return None
        candidate = value + ("." + ".".join(tail) if tail else "")
        return candidate if candidate in node_ids else None
    return None
