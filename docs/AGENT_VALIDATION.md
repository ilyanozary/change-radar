# Agent validation · 2026-10-23

## Codex: verified on one isolated fixture

A real installed Codex CLI session ran successfully (exit 0), not a simulated
subagent answer. The fresh 0.1.0a1 wheel was installed with --no-index --no-deps into
a new venv. examples/preview was copied into a separate temporary Git repository;
install-skill placed the canonical SKILL.md in .agents/skills/change-radar.
The agent's PATH included the new venv. No model or reasoning override was selected.

Natural prompt (without explicit skill invocation):

> اگر وابستگی احراز هویت را تغییر بدهم، چه endpointهایی ممکن است تحت‌تأثیر قرار بگیرند؟ با شاهد از کد توضیح بده.

The actual request also explicitly prohibited target execution, edits and forwarding
the source to external services. Normal Codex model service use is distinct from
the analysis engine, which remains offline and needs no key/network.

Observed commands in the actual JSONL session, all exit 0:

1. Listed local files and read .agents/skills/change-radar/SKILL.md.
2. Read security.py, routes.py, main.py, models.py and tests/test_http.py with line numbers.
3. Ran change-radar scan on the isolated project.
4. Chose security.py::current_user and explained its role; also analyzed read_token.
5. Ran change-radar impact for both seeds with depth 4/limit 200.
6. Read the impact result including truncation, consumers and suggested tests.

The final Persian answer identified GET /v1/shop/items and GET /v1/shop/me, gave
source witnesses for Depends, CurrentUser, both consumers and router prefixes,
and distinguished the independent health endpoint. It described runtime effects
conditionally and did not claim proof of breakage. It reported the read_token
analysis hitting the depth limit and suggested tests without executing them.
Source .py hashes were compared against the copied originals after the session;
no target source was modified. Session commands did not execute/import target code.
Raw logs remain in the ignored .change-radar/agent-smoke directory; they are not
published because they include local paths and unrelated connector startup logs.

This establishes discovery, seed selection, engine execution, source review and
limitations on this single fixture. It does not establish general semantic accuracy.
Optional global connector startup warnings occurred but did not prevent completion.

## Claude Code: not performed

The claude executable is absent. Its installer/dry-run/conflict behavior and wheel
asset inclusion are verified separately; that is not end-to-end agent verification.
Do not advertise Claude behavior as tested.

## Reproduction

1. Build the wheel; copy examples/preview into a new temporary project and git init.
2. Create a fresh venv outside the project and pip install --no-index --no-deps the
   exact dist/change_radar-0.1.0a1-py3-none-any.whl.
3. Put its bin directory on PATH. Run change-radar install-skill --agent codex
   --scope project --root PROJECT (use --dry-run first if files already exist).
4. In that directory run `codex exec --ephemeral --sandbox read-only --json` with
   the Persian prompt above. Keep stdout logs private and inspect actual commands,
   not only the final answer. Agent login/network availability is required.
5. Verify the skill read, chosen seeds, CLI calls, evidence inspection, limitations,
   unchanged source and lack of target execution. Run the same request in Claude
   Code after installing its project skill to .claude/skills/change-radar when that
   agent is available; record failures rather than assuming matching behavior.

Local skill discovery and exec usage were checked against official documentation:
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[non-interactive mode](https://learn.chatgpt.com/docs/non-interactive-mode).
