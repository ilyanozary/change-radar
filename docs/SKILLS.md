# Shared agent skill

One canonical skill ships inside the wheel: `src/change_radar/skill/SKILL.md`. Both installers copy exactly that file and use the same installed CLI. There are no hooks, automatic AGENTS.md/CLAUDE.md edits, or hidden global installation. Agent metadata/resources are unnecessary for this instruction-only package.

Current official paths checked on 2026-10-22:

| Agent | Project | User |
|---|---|---|
| Codex | `.agents/skills/change-radar/SKILL.md` | `~/.agents/skills/change-radar/SKILL.md` |
| Claude Code | `.claude/skills/change-radar/SKILL.md` | `~/.claude/skills/change-radar/SKILL.md` |

Sources: [official Codex local discovery documentation](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills), [official Claude Code skills documentation](https://code.claude.com/docs/en/skills#choose-where-skills-load). Local skill discovery differs from cloud/plugin distribution; this installer targets local sessions.

```bash
change-radar install-skill --agent codex --scope project --root /path/to/repository --dry-run
change-radar install-skill --agent codex --scope project --root /path/to/repository
change-radar install-skill --agent claude --scope user --dry-run
```

`--scope` and `--agent` are mandatory. User scope uses the home directory; project scope uses the explicit root (current directory by default). No overwrite flag is provided: identical content is idempotent, differing existing content produces a unified diff in dry-run and is preserved on installation. Symlink destinations are refused. Back up/reconcile conflicting files yourself before reinstalling. Dry-run makes no directories.

Activate the environment or otherwise put `change-radar` on the agent's PATH. Start a new session if discovery does not refresh. Ask: “Use change-radar to assess replacing password login with OTP in examples/shop. Do not edit code.” The agent should choose seeds with reasons, run the CLI, inspect actual evidence locations and separate observations, inferences, and unknowns. CLI availability alone does not prove skill discovery or behavior.

Validation distinctions:

- Package structure/frontmatter: validated with skill-creator validator.
- Local copy, dry-run, conflict and symlink preservation: covered by automated tests; both destination types also exercised from the installed wheel.
- Real Codex workflow/discovery: not end-to-end tested. A Codex executable exists, but no separate agent session was launched.
- Real Claude Code workflow/discovery: not tested; executable absent in this environment.

Neither CLI nor skill runs target tests by default. Explicit authorization to analyze a repository does not authorize editing or deploying it.
