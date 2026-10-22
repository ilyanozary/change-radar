"""Bounded, non-executing annotation and module type-alias references."""

import ast

from .scopes import import_reference, lookup_binding

ANNOTATED = {"typing.Annotated", "typing_extensions.Annotated"}
DEPENDS = {"fastapi.Depends", "fastapi.params.Depends"}
CONTAINERS = {"list", "set", "tuple", "dict", "frozenset", "type"}
WRAPPERS = {
    f"typing.{name}"
    for name in (
        "List",
        "Set",
        "Tuple",
        "Dict",
        "FrozenSet",
        "Type",
        "Optional",
        "Union",
    )
}
BUILTINS = CONTAINERS | {"str", "int", "float", "bool", "bytes", "object", "complex"}


def name_of(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = name_of(node.value)
        return base + "." + node.attr if base else ""
    return ""


def dependency_argument(call):
    """Accept exactly one positional/keyword dependency, without guessing."""
    if any(k.arg is None for k in call.keywords):
        return None
    named = [k.value for k in call.keywords if k.arg == "dependency"]
    if len(call.args) == 1 and not named and not isinstance(call.args[0], ast.Starred):
        return call.args[0]
    if (
        not call.args
        and len(named) == 1
        and not any(k.arg is None for k in call.keywords)
    ):
        return named[0]
    return None


class AnnotationGraph:
    def __init__(self, trees, frames, nodes, edge, issue, resolve):
        self.frames, self.nodes, self.edge, self.issue, self.resolve = (
            frames,
            nodes,
            edge,
            issue,
            resolve,
        )
        self.records = {}
        self.results = {}
        self.active = []
        self.cyclic = set()
        for path, tree in trees.items():
            for stmt in tree.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                ):
                    name, value = stmt.targets[0].id, stmt.value
                elif (
                    isinstance(stmt, ast.AnnAssign)
                    and isinstance(stmt.target, ast.Name)
                    and stmt.value is not None
                ):
                    name, value = stmt.target.id, stmt.value
                else:
                    continue
                self.records.setdefault((path, name), (stmt, value))

    def destination(self, path, name, scope=""):
        first = name.split(".")[0]
        found = lookup_binding(self.frames[path], scope, first)
        if (
            "." not in name
            and found
            and found[0] == ""
            and (path, first) in self.records
        ):
            return self.assignment(path, first)
        return self.resolve(path, name, scope)

    def assignment(self, path, name):
        key = path, name
        if key not in self.records:
            return None
        if key in self.results:
            return self.results[key]
        stmt, value = self.records[key]
        if key in self.active:
            for member in self.active[self.active.index(key) :]:
                self.cyclic.add(member)
                self.issue(
                    member[0], self.records[member][0].lineno, "unresolved_alias_cycle"
                )
            return None
        if len(self.active) >= 64:
            self.issue(path, stmt.lineno, "unresolved_alias_limit")
            return None
        frame = self.frames[path][""]
        annotated = (
            isinstance(value, ast.Subscript)
            and import_reference(self.frames[path], "", name_of(value.value))
            in ANNOTATED
        )
        if frame.writes.get(name) != 1:
            if annotated:
                self.issue(path, stmt.lineno, "unresolved_annotation_alias")
            self.results[key] = None
            return None
        self.active.append(key)
        targets = []
        metadata = []
        valid = False
        try:
            if annotated:
                args = (
                    list(value.slice.elts)
                    if isinstance(value.slice, ast.Tuple)
                    else [value.slice]
                )
                if len(args) >= 2:
                    targets = self.type_targets(path, args[0], "")
                    metadata = args[1:]
                    valid = True
                else:
                    self.issue(path, stmt.lineno, "unresolved_annotation_alias")
            elif isinstance(value, (ast.Name, ast.Attribute)):
                dest = self.destination(path, name_of(value))
                if dest and self.nodes[dest]["kind"] in {"class", "alias"}:
                    targets = [(dest, value.lineno)]
                    valid = True
            if key in self.cyclic:
                valid = False
            if not valid:
                self.results[key] = None
                return None
            id = path + "::" + name
            self.nodes[id] = dict(
                id=id,
                kind="alias",
                name=name,
                path=path,
                line=stmt.lineno,
                end_line=stmt.end_lineno,
            )
            self.results[key] = id
            frame.names[name] = ("symbol", id)
            self.edge(path, id, "defines", path, stmt.lineno)
            for dest, line in targets:
                self.edge(id, dest, "annotation", path, line)
            for expr in metadata:
                if (
                    isinstance(expr, ast.Call)
                    and import_reference(self.frames[path], "", name_of(expr.func))
                    in DEPENDS
                ):
                    self.dependency(id, path, expr, "")
                else:
                    self.issue(path, expr.lineno, "unresolved_annotation_metadata")
            return id
        finally:
            self.active.pop()

    def prepare(self):
        for path, name in sorted(self.records):
            self.assignment(path, name)

    def dependency(self, owner, path, call, scope):
        value = dependency_argument(call)
        dest = (
            self.destination(path, name_of(value), scope) if value is not None else None
        )
        if dest and self.nodes[dest]["kind"] in {"function", "class"}:
            self.edge(owner, dest, "depends", path, call.lineno)
        else:
            self.issue(path, call.lineno, "unresolved_dependency")

    def references(self, owner, path, node, scope, kind="annotation"):
        for dest, line in self.type_targets(path, node, scope):
            self.edge(owner, dest, kind, path, line)

    def type_targets(self, path, node, scope, quoted_line=None):
        line = quoted_line or node.lineno

        def unresolved():
            self.issue(path, line, "unresolved_annotation")
            return []

        if isinstance(node, ast.Constant):
            if node.value is None or node.value is Ellipsis:
                return []
            if isinstance(node.value, str) and quoted_line is None:
                try:
                    expression = ast.parse(node.value, mode="eval").body
                except (SyntaxError, ValueError):
                    return unresolved()
                if isinstance(expression, (ast.Name, ast.Attribute)):
                    return self.type_targets(path, expression, scope, line)
            return unresolved()
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = name_of(node)
            dest = self.destination(path, name, scope)
            if dest and self.nodes[dest]["kind"] in {"class", "alias"}:
                return [(dest, line)]
            if (
                name in BUILTINS
                and lookup_binding(self.frames[path], scope, name) is None
            ):
                return []
            if import_reference(self.frames[path], scope, name) in {
                "typing.Any",
                "typing_extensions.Any",
            }:
                return []
            return unresolved()
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self.type_targets(
                path, node.left, scope, quoted_line
            ) + self.type_targets(path, node.right, scope, quoted_line)
        if isinstance(node, ast.Subscript):
            wrapper = name_of(node.value)
            imported = import_reference(self.frames[path], scope, wrapper)
            args = (
                list(node.slice.elts)
                if isinstance(node.slice, ast.Tuple)
                else [node.slice]
            )
            if imported in ANNOTATED:
                if len(args) < 2:
                    return unresolved()
                # Metadata is not a type reference (e.g. Annotated[str, Item]).
                return self.type_targets(path, args[0], scope, quoted_line)
            if imported in WRAPPERS or (
                wrapper in CONTAINERS
                and lookup_binding(self.frames[path], scope, wrapper) is None
            ):
                return [
                    target
                    for arg in args
                    for target in self.type_targets(path, arg, scope, quoted_line)
                ]
        return unresolved()
