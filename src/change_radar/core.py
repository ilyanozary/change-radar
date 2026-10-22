import ast
import fnmatch
import os
import subprocess
import tempfile
import tokenize
from collections import defaultdict, deque
from pathlib import Path

LIMITATIONS = [
    "Static evidence is not proof of runtime breakage; empty results do not imply safety.",
    "Calls: lexical names, module aliases and explicit class attributes only. Instance dispatch, monkeypatching and dynamic imports require manual review.",
    "FastAPI: module-level app/router assignments, literal paths/prefixes and direct include_router only. Conditional mounting is not runtime-validated.",
    "Annotations are reference evidence, not complete Pydantic field or serialization analysis.",
    "No execution of target code or tests. No semantic interpretation of free text.",
    "No cache: scans rebuild the graph; gitignore rules are delegated to Git when available.",
    "Module bindings are simplified: scoped/conditional imports and wildcard imports need manual review. Direct module assignments and local parameters/assignments suppress call resolution for shadowed names.",
    "Endpoint test matching is heuristic: a matching HTTP method and literal URL does not prove the client calls this application.",
]


def git(root, *args, binary=False):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if p.returncode:
        raise ValueError(p.stderr.decode(errors="replace").strip())
    return p.stdout if binary else p.stdout.decode(errors="replace")


def discover(root, excludes):
    paths, skipped = [], []
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            d
            for d in dirs
            if d
            not in {
                ".git",
                ".venv",
                "venv",
                "__pycache__",
                "node_modules",
                ".change-radar",
                "dist",
                "build",
            }
            and not Path(base, d).is_symlink()
        )
        for name in sorted(files):
            p = Path(base, name)
            rel = p.relative_to(root).as_posix()
            if p.suffix != ".py":
                continue
            if p.is_symlink() or any(fnmatch.fnmatch(rel, x) for x in excludes):
                skipped.append(rel)
            else:
                paths.append(rel)
    try:
        # Pass paths through stdin, without shell interpretation; handles newlines and Unicode.
        p = subprocess.run(
            ["git", "-C", str(root), "check-ignore", "--no-index", "-z", "--stdin"],
            input=b"\0".join(os.fsencode(x) for x in paths) + b"\0",
            capture_output=True,
        )
        if p.returncode not in (0, 1):
            # Git's own wildmatch implementation also works for non-Git directories.
            # The temporary metadata is outside the scanned repository.
            with tempfile.TemporaryDirectory(prefix="change-radar-ignore-") as tmp:
                init = subprocess.run(
                    ["git", "init", "--bare", "-q", tmp], capture_output=True
                )
                if init.returncode == 0:
                    p = subprocess.run(
                        [
                            "git",
                            "--git-dir=" + tmp,
                            "--work-tree=" + str(root),
                            "-c",
                            "core.bare=false",
                            "check-ignore",
                            "--no-index",
                            "-z",
                            "--stdin",
                        ],
                        input=b"\0".join(os.fsencode(x) for x in paths) + b"\0",
                        capture_output=True,
                    )
        if p.returncode in (0, 1):
            ignored = {os.fsdecode(x) for x in p.stdout.split(b"\0") if x}
            skipped.extend(sorted(ignored))
            paths = [x for x in paths if x not in ignored]
        gitignore = p.returncode in (0, 1)
    except FileNotFoundError:
        gitignore = False
    return sorted(paths), sorted(skipped), gitignore


def dotted(n):
    if isinstance(n, ast.Name):
        return n.id
    if isinstance(n, ast.Attribute):
        b = dotted(n.value)
        return b + "." + n.attr if b else ""
    return ""


def literal(n):
    return n.value if isinstance(n, ast.Constant) and isinstance(n.value, str) else None


def scan(root, excludes=()):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Repository must be an existing directory")
    files, skipped, ignores = discover(root, excludes)
    nodes, edges, issues, trees, modules, bindings, scopes = (
        {},
        [],
        [],
        {},
        defaultdict(list),
        {},
        {},
    )

    def node(id, **data):
        nodes[id] = dict(id=id, **data)

    edge_keys = set()

    def edge(a, b, kind, path, line, certainty="observed"):
        e = dict(
            source=a,
            target=b,
            type=kind,
            origin="python-ast",
            certainty=certainty,
            evidence=dict(path=path, line=line),
        )
        key = (a, b, kind, path, line, certainty)
        if key not in edge_keys:
            edge_keys.add(key)
            edges.append(e)

    for path in files:
        node(path, kind="file", path=path, name=path, line=1, end_line=1)
        parts = Path(path).with_suffix("").parts
        if len(parts) > 1 and parts[0] == "src":
            parts = parts[1:]
        if parts[-1] == "__init__":
            parts = parts[:-1]
        modules[".".join(parts)].append(path)
        try:
            with tokenize.open(root / path) as f:
                trees[path] = ast.parse(f.read(), filename=path)
        except (SyntaxError, UnicodeError, OSError) as exc:
            issues.append(
                dict(
                    path=path,
                    line=getattr(exc, "lineno", None),
                    category="parse_error",
                    message=type(exc).__name__,
                )
            )
            continue
        bindings[path] = {}
        scopes[path] = {}

        def definitions(body, prefix="", owner=path):
            for n in body:
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    qual = prefix + n.name
                    id = path + "::" + qual
                    node(
                        id,
                        kind="class" if isinstance(n, ast.ClassDef) else "function",
                        path=path,
                        name=qual,
                        line=n.lineno,
                        end_line=n.end_lineno,
                    )
                    scopes[path][qual] = id
                    edge(owner, id, "defines", path, n.lineno)
                    definitions(n.body, qual + ".", id)

        definitions(trees[path].body)
    module_for = {p: m for m, ps in modules.items() for p in ps}
    for path, tree in trees.items():
        for n in ast.walk(tree):
            if isinstance(n, (ast.Import, ast.ImportFrom)) and n not in tree.body:
                issues.append(
                    dict(
                        path=path,
                        line=n.lineno,
                        category="scoped_or_conditional_import",
                    )
                )
        for n in tree.body:
            if isinstance(n, ast.Import):
                for alias in n.names:
                    bindings[path][alias.asname or alias.name.split(".")[0]] = (
                        alias.name if alias.asname else alias.name.split(".")[0]
                    )
            elif isinstance(n, ast.ImportFrom):
                base = n.module or ""
                if n.level:
                    pkg = module_for[path].split(".")
                    if Path(path).name != "__init__.py":
                        pkg = pkg[:-1]
                    base = ".".join(
                        pkg[: max(0, len(pkg) - n.level + 1)] + ([base] if base else [])
                    )
                for alias in n.names:
                    bindings[path][alias.asname or alias.name] = (
                        base + "." + alias.name
                    ).strip(".")
    blocked_globals = {}
    for path, tree in trees.items():
        blocked_globals[path] = {
            x.id
            for n in tree.body
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))
            for x in ast.walk(n)
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)
        }
        for name in blocked_globals[path]:
            if name in bindings[path] or name in scopes[path]:
                issues.append(dict(path=path, line=1, category="rebound_name"))

    def resolve_global(name, seen=None):
        seen = set() if seen is None else seen
        if name in seen:
            return None
        seen.add(name)
        if name in modules:
            return modules[name][0] if len(modules[name]) == 1 else None
        bits = name.split(".")
        for i in range(len(bits) - 1, 0, -1):
            mod, tail = ".".join(bits[:i]), ".".join(bits[i:])
            if len(modules.get(mod, [])) == 1:
                p = modules[mod][0]
                if tail.split(".")[0] in blocked_globals.get(p, set()):
                    return None
                if tail in scopes.get(p, {}):
                    return scopes[p][tail]
                first, *rest = tail.split(".")
                if first in bindings.get(p, {}):
                    return resolve_global(
                        bindings[p][first] + ("." + ".".join(rest) if rest else ""),
                        seen,
                    )
        return None

    def expand(path, name):
        first, *rest = name.split(".")
        return bindings[path].get(first, first) + ("." + ".".join(rest) if rest else "")

    def resolve(path, name, scope=""):
        if not name:
            return None
        first = name.split(".")[0]
        if first in blocked_globals[path]:
            return None
        if first in bindings[path]:
            return resolve_global(expand(path, name))
        prefixes = scope.split(".")[:-1]
        while prefixes:
            key = ".".join(prefixes) + "." + name
            prefix_id = scopes[path].get(".".join(prefixes))
            if key in scopes[path] and (
                not prefix_id or nodes[prefix_id]["kind"] != "class"
            ):
                return scopes[path][key]
            prefixes.pop()
        return scopes[path].get(name)

    for path, tree in trees.items():
        for n in tree.body:
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for alias in n.names:
                    local = alias.asname or (
                        alias.name.split(".")[0]
                        if isinstance(n, ast.Import)
                        else alias.name
                    )
                    name = (
                        alias.name
                        if isinstance(n, ast.Import)
                        else bindings[path].get(local, "")
                    )
                    dest = resolve_global(name)
                    if dest:
                        edge(path, dest, "imports", path, n.lineno)
                    else:
                        top = name.split(".")[0]
                        category = (
                            "unresolved_local"
                            if any(m.split(".")[0] == top for m in modules)
                            else "external_or_unresolved"
                        )
                        if name in modules and len(modules[name]) > 1:
                            category = "ambiguous_import"
                        issues.append(
                            dict(
                                path=path,
                                line=n.lineno,
                                category=category,
                                reference=name,
                            )
                        )
        # Top-level bindings to FastAPI/APIRouter constructors only.
    routers, includes = {}, []
    for path, tree in trees.items():
        for n in tree.body:
            if isinstance(n, ast.Assign) and isinstance(n.value, ast.Call):
                constructor_name = dotted(n.value.func)
                if constructor_name.split(".")[0] in blocked_globals[path]:
                    continue
                constructor = expand(path, constructor_name)
                if constructor in {
                    "fastapi.FastAPI",
                    "fastapi.applications.FastAPI",
                    "fastapi.APIRouter",
                    "fastapi.routing.APIRouter",
                }:
                    prefix = ""
                    for kw in n.value.keywords:
                        if kw.arg == "prefix":
                            prefix = literal(kw.value)
                    for t in n.targets:
                        if isinstance(t, ast.Name):
                            writes = sum(
                                1
                                for stmt in tree.body
                                if isinstance(
                                    stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)
                                )
                                for target in ast.walk(stmt)
                                if isinstance(target, ast.Name)
                                and isinstance(target.ctx, ast.Store)
                                and target.id == t.id
                            )
                            if writes == 1:
                                routers[(path, t.id)] = prefix
                            else:
                                issues.append(
                                    dict(
                                        path=path,
                                        line=n.lineno,
                                        category="rebound_router",
                                    )
                                )
    for path, tree in trees.items():
        for n in ast.walk(tree):
            if (
                isinstance(n, ast.Call)
                and isinstance(n.func, ast.Attribute)
                and n.func.attr == "include_router"
                and n.args
            ):
                host = (path, dotted(n.func.value))
                if host not in routers:
                    continue
                name = expand(path, dotted(n.args[0]))
                router = None
                for rp, rn in routers:
                    if (rp == path and rn == dotted(n.args[0])) or module_for[
                        rp
                    ] + "." + rn == name:
                        router = (rp, rn)
                prefix = ""
                for kw in n.keywords:
                    if kw.arg == "prefix":
                        prefix = literal(kw.value)
                includes.append((host, router, prefix, path, n.lineno))

    def mounts(key, seen=()):
        if key in seen:
            return [None]
        parents = [x for x in includes if x[1] == key]
        own = routers[key]
        if not parents:
            return [own]
        return [
            a + b + own if all(isinstance(v, str) for v in (a, b, own)) else None
            for host, _, b, _, _ in parents
            for a in mounts(host, seen + (key,))
        ]

    endpoints = []
    for path, tree in trees.items():

        class Visitor(ast.NodeVisitor):
            def __init__(self):
                self.scope = ""
                self.owner = path
                self.blocked = set()

            def visit_ClassDef(self, n):
                self.visit_definition(n)

            def visit_FunctionDef(self, n):
                self.visit_definition(n)

            visit_AsyncFunctionDef = visit_FunctionDef

            def visit_definition(self, n):
                old = self.scope, self.owner, self.blocked
                self.scope = (self.scope + "." if self.scope else "") + n.name
                if self.scope not in scopes[path]:
                    issues.append(
                        dict(
                            path=path, line=n.lineno, category="conditional_definition"
                        )
                    )
                    self.scope, self.owner, self.blocked = old
                    return
                self.owner = scopes[path][self.scope]
                self.blocked = set()
                if hasattr(n, "args"):
                    self.blocked = {
                        a.arg
                        for a in n.args.posonlyargs + n.args.args + n.args.kwonlyargs
                    }
                    for child in ast.walk(n):
                        if isinstance(child, (ast.Import, ast.ImportFrom)):
                            self.blocked.update(
                                a.asname or a.name.split(".")[0] for a in child.names
                            )
                    self.blocked.update(
                        x.id
                        for st in n.body
                        for x in ast.walk(st)
                        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store)
                    )
                for dec in n.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(
                        dec.func, ast.Attribute
                    ):
                        key = path, dotted(dec.func.value)
                        method = dec.func.attr.upper()
                        if key in routers and method in {
                            "GET",
                            "POST",
                            "PUT",
                            "PATCH",
                            "DELETE",
                            "OPTIONS",
                            "HEAD",
                            "TRACE",
                        }:
                            route = (
                                literal(dec.args[0])
                                if dec.args
                                else next(
                                    (
                                        literal(k.value)
                                        for k in dec.keywords
                                        if k.arg == "path"
                                    ),
                                    None,
                                )
                            )
                            for prefix in mounts(key):
                                endpoints.append(
                                    dict(
                                        symbol=self.owner,
                                        method=method,
                                        path=prefix + route
                                        if prefix is not None and route is not None
                                        else None,
                                        evidence=dict(path=path, line=dec.lineno),
                                    )
                                )
                                if prefix is None or route is None:
                                    issues.append(
                                        dict(
                                            path=path,
                                            line=dec.lineno,
                                            category="unresolved_route",
                                        )
                                    )
                            for kw in dec.keywords:
                                if kw.arg == "response_model":
                                    self.references(kw.value, "response_model")
                for a in ast.iter_fields(n):
                    if a[0] == "returns" and a[1]:
                        self.references(a[1], "annotation")
                if hasattr(n, "args"):
                    for arg in n.args.posonlyargs + n.args.args + n.args.kwonlyargs:
                        if arg.annotation:
                            self.references(arg.annotation, "annotation")
                self.generic_visit(n)
                self.scope, self.owner, self.blocked = old

            def references(self, n, kind):
                for x in ast.walk(n):
                    if isinstance(x, (ast.Name, ast.Attribute)):
                        dest = resolve(path, dotted(x), self.scope)
                        if dest:
                            edge(self.owner, dest, kind, path, x.lineno)

            def visit_Call(self, n):
                name = dotted(n.func)
                dest = (
                    None
                    if name.split(".")[0] in self.blocked
                    else resolve(path, name, self.scope)
                )
                if dest:
                    edge(self.owner, dest, "calls", path, n.lineno)
                elif expand(path, name) in {
                    "fastapi.Depends",
                    "fastapi.params.Depends",
                }:
                    if n.args:
                        dependency = resolve(path, dotted(n.args[0]), self.scope)
                        if dependency:
                            edge(self.owner, dependency, "depends", path, n.lineno)
                        else:
                            issues.append(
                                dict(
                                    path=path,
                                    line=n.lineno,
                                    category="unresolved_dependency",
                                )
                            )
                elif name and expand(path, name).split(".")[0] not in {
                    "fastapi",
                    "pydantic",
                }:
                    issues.append(
                        dict(path=path, line=n.lineno, category="unresolved_call")
                    )
                self.generic_visit(n)

        Visitor().visit(tree)
    for path, tree in trees.items():
        if not any(p == "tests" or p.startswith("test_") for p in Path(path).parts):
            continue
        for call in ast.walk(tree):
            if (
                not isinstance(call, ast.Call)
                or not isinstance(call.func, ast.Attribute)
                or not call.args
            ):
                continue
            url = literal(call.args[0])
            for endpoint in endpoints:
                if (
                    url is not None
                    and endpoint["path"] == url
                    and endpoint["method"].lower() == call.func.attr.lower()
                ):
                    owners = [
                        n
                        for n in nodes.values()
                        if n["path"] == path
                        and n["kind"] == "function"
                        and n["line"] <= call.lineno <= n["end_line"]
                    ]
                    owner = (
                        min(owners, key=lambda n: n["end_line"] - n["line"])["id"]
                        if owners
                        else path
                    )
                    edge(
                        owner,
                        endpoint["symbol"],
                        "endpoint_literal",
                        path,
                        call.lineno,
                        "heuristic",
                    )
    for host, router, prefix, path, line in includes:
        if router:
            edge(host[0], router[0], "includes_router", path, line)
        else:
            issues.append(dict(path=path, line=line, category="unresolved_router"))
    return dict(
        schema_version="1.0",
        nodes=sorted(nodes.values(), key=lambda n: n["id"]),
        edges=sorted(
            edges,
            key=lambda e: (e["source"], e["target"], e["type"], e["evidence"]["line"]),
        ),
        endpoints=sorted(endpoints, key=lambda e: (e["symbol"], str(e["path"]))),
        coverage=dict(
            files=len(files),
            parsed=len(trees),
            skipped=skipped,
            gitignore_applied=ignores,
            issues=sorted(
                issues, key=lambda x: (x["path"], x.get("line") or 0, x["category"])
            ),
        ),
        limitations=LIMITATIONS,
    )


def impact(graph, seeds, depth=4, limit=200, request=""):
    if depth < 0 or limit < 1:
        raise ValueError("depth >= 0 and limit >= 1 required")
    nodes = {n["id"]: n for n in graph["nodes"]}
    invalid = sorted(set(seeds) - nodes.keys())
    if invalid:
        raise ValueError("Unknown seeds: " + ", ".join(invalid))
    reverse = defaultdict(list)
    for e in graph["edges"]:
        reverse[e["target"]].append(e)
    reached = {
        s: dict(id=s, depth=0, role="change_candidate", chain=[])
        for s in sorted(set(seeds))
    }
    q = deque(reached)
    # A file seed intentionally selects its definitions as change candidates.
    for s in list(reached):
        if nodes[s]["kind"] == "file":
            for n in graph["nodes"]:
                if n["path"] == s and n["id"] != s:
                    reached[n["id"]] = dict(
                        id=n["id"], depth=0, role="change_candidate", chain=[]
                    )
                    q.append(n["id"])
    truncated = len(reached) > limit
    if truncated:
        reached = dict(list(reached.items())[:limit])
        q = deque(reached)
    while q:
        target = q.popleft()
        item = reached[target]
        if item["depth"] >= depth:
            if any(e["source"] not in reached for e in reverse[target]):
                truncated = True
            continue
        for e in reverse[target]:
            source = e["source"]
            if source in reached:
                continue
            if len(reached) >= limit:
                truncated = True
                continue
            reached[source] = dict(
                id=source,
                depth=item["depth"] + 1,
                role="containing_scope"
                if e["type"] == "defines"
                else "potential_consumer",
                certainty="inferred",
                chain=item["chain"] + [e],
            )
            q.append(source)
    tests = [
        dict(
            id=id,
            evidence="endpoint_literal_candidate"
            if any(e["certainty"] == "heuristic" for e in x["chain"])
            else "graph_reference",
            chain=x["chain"],
        )
        for id, x in reached.items()
        if any(
            p.startswith("test_") or p == "tests" for p in Path(nodes[id]["path"]).parts
        )
    ]
    return dict(
        **graph,
        request=request,
        seeds=sorted(set(seeds)),
        impact=sorted(reached.values(), key=lambda x: (x["depth"], x["id"])),
        truncated=truncated,
        depth_limit=depth,
        result_limit=limit,
        suggested_tests=tests,
        new_test_scenarios=[
            "Verify changed contract serialization and validation.",
            "Exercise affected endpoint success, authorization and failure paths.",
        ],
        implementation_order=[
            "Review seeds and their contracts.",
            "Update shared dependencies/models, then consumers.",
            "Review suggested tests and add regression cases; execute only when explicitly authorized.",
        ],
    )


def diff(root, mode="unstaged", base=None):
    args = [
        "diff",
        "--name-status",
        "-z",
        "--no-renames",
        "--no-ext-diff",
        "--no-textconv",
    ]
    if mode == "staged":
        args.append("--cached")
    if mode == "base":
        if not base or base.startswith("-"):
            raise ValueError("A non-option base revision is required")
        revision = git(
            root, "rev-parse", "--verify", "--end-of-options", base + "^{commit}"
        ).strip()
        args.append(revision)
    args.append("--")
    fields = git(root, *args, binary=True).split(b"\0")
    changes = [
        dict(status=os.fsdecode(fields[i]), path=os.fsdecode(fields[i + 1]))
        for i in range(0, len(fields) - 1, 2)
    ]
    if mode == "unstaged":
        changes += [
            dict(status="?", path=os.fsdecode(p))
            for p in git(
                root, "ls-files", "--others", "--exclude-standard", "-z", binary=True
            ).split(b"\0")
            if p
        ]
    return sorted(changes, key=lambda c: c["path"])
