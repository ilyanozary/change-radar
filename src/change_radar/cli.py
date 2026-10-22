import argparse
import difflib
import json
import shutil
import sys
from pathlib import Path

from .core import diff, impact, scan
from .report import markdown, render


def install(agent, scope, root, dry_run=False):
    base = Path(root).resolve() if scope == "project" else Path.home()
    folder = ".agents" if agent == "codex" else ".claude"
    dest = base / folder / "skills" / "change-radar" / "SKILL.md"
    for parent in [dest, *dest.parents]:
        if parent == base:
            break
        if parent.is_symlink():
            raise ValueError(
                "Skill destination contains a symlink; preserved: " + str(parent)
            )
    content = Path(__file__).with_name("skill").joinpath("SKILL.md").read_text()
    if dest.exists():
        old = dest.read_text()
        if old != content:
            changes = "".join(
                difflib.unified_diff(
                    old.splitlines(True),
                    content.splitlines(True),
                    fromfile=str(dest),
                    tofile="packaged skill",
                )
            )
            if dry_run:
                return dict(
                    destination=str(dest), dry_run=True, conflict=True, diff=changes
                )
            raise ValueError(
                "Existing skill differs; preserved. Review with --dry-run.\n" + changes
            )
    if not dry_run:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content)
    return dict(destination=str(dest), dry_run=dry_run, conflict=False)


def parser():
    p = argparse.ArgumentParser(
        description="Local Python/FastAPI evidence-first impact analysis.",
        epilog="Example: change-radar impact examples/shop --seed app/services.py::authenticate --output /tmp/radar.html --format html",
    )
    subs = p.add_subparsers(dest="command", required=True)
    for command in ("scan", "impact", "diff"):
        s = subs.add_parser(command)
        s.add_argument("root", type=Path)
        s.add_argument(
            "--exclude",
            action="append",
            default=[],
            help="Root-relative glob; repeatable",
        )
        s.add_argument(
            "--output", type=Path, help="Explicit destination; otherwise stdout"
        )
        s.add_argument("--format", choices=["json", "markdown", "html"], default="json")
        if command != "scan":
            s.add_argument("--depth", type=int, default=4)
            s.add_argument("--limit", type=int, default=200)
            s.add_argument(
                "--request",
                default="",
                help="Display label only, never interpreted as instructions",
            )
        if command == "impact":
            s.add_argument(
                "--seed",
                action="append",
                required=True,
                default=[],
                help="Exact file or path::qualified_symbol; repeatable",
            )
        if command == "diff":
            s.add_argument(
                "--mode", choices=["staged", "unstaged", "base"], default="unstaged"
            )
            s.add_argument("--base")
    s = subs.add_parser("report")
    s.add_argument("input", type=Path)
    s.add_argument("--output", type=Path)
    s.add_argument("--format", choices=["html", "markdown", "json"], default="html")
    s = subs.add_parser("doctor")
    s.add_argument("root", type=Path, nargs="?", default=Path("."))
    s = subs.add_parser("install-skill")
    s.add_argument("--agent", choices=["codex", "claude"], required=True)
    s.add_argument("--scope", choices=["project", "user"], required=True)
    s.add_argument("--root", type=Path, default=Path("."))
    s.add_argument("--dry-run", action="store_true")
    return p


def main():
    p = parser()
    a = p.parse_args()
    try:
        if a.command == "install-skill":
            result = install(a.agent, a.scope, a.root, a.dry_run)
        elif a.command == "doctor":
            result = dict(
                schema_version="1.0",
                python=sys.version.split()[0],
                git=bool(shutil.which("git")),
                root_exists=a.root.is_dir(),
                network_required=False,
                target_execution=False,
                cache="not implemented; full rescan",
            )
        elif a.command == "report":
            result = json.loads(a.input.read_text())
            if (
                result.get("schema_version") != "1.0"
                or not isinstance(result.get("nodes"), list)
                or not isinstance(result.get("edges"), list)
            ):
                raise ValueError("Unsupported report schema")
        else:
            result = scan(a.root, a.exclude)
            if a.command == "impact":
                result = impact(result, a.seed, a.depth, a.limit, a.request)
            elif a.command == "diff":
                changes = diff(a.root, a.mode, a.base)
                ids = {n["id"] for n in result["nodes"]}
                seeds = [c["path"] for c in changes if c["path"] in ids]
                result = impact(result, seeds, a.depth, a.limit, a.request)
                result["git_changes"] = changes
                result["limitations"] = result["limitations"] + [
                    "Git seeds are entire changed files. Deleted files have no AST in the current tree; rename is represented as delete + add. Base compares commit to working tree. Untracked files are included only in unstaged mode."
                ]
        fmt = getattr(a, "format", "json")
        output = (
            render(result)
            if fmt == "html"
            else markdown(result)
            if fmt == "markdown"
            else json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\n"
        )
        if getattr(a, "output", None):
            out = a.output.resolve()
            if out.exists():
                raise ValueError(
                    "Output already exists; choose another path or remove it explicitly"
                )
            # Do not silently create folders or write over target source.
            with out.open("x", encoding="utf-8") as f:
                f.write(output)
        else:
            print(output, end="")
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print("change-radar: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
