# Agent and Developer Operating Contract

AI Image Prompt Factory is an agentic image-prompt engineering, transformation, cultural/art reasoning, empirical evaluation, and gallery system. The Git repository and its committed artifacts are the canonical shared project state across ChatGPT IDEA_POOL, ChatGPT Work, Codex, local development, future agents, and GitHub. Prior conversation memory is advisory, never authoritative.

Before substantial work, read [current state](docs/PROJECT_STATE.md), [capability roadmap](docs/ROADMAP.md), [decision index](docs/DECISIONS.md), and [session handoff](docs/SESSION_HANDOFF.md). Inspect the relevant code, evidence, and Git history before making claims. The runtime contract remains in [SKILL.md](SKILL.md); module authoring guidance remains in [docs/CONTRIBUTING_MODULES.md](docs/CONTRIBUTING_MODULES.md).

## Branch and evidence discipline

- `main` is stable and releasable. Use scoped branches for substantial work. Never force-push `main` or silently rewrite history.
- Preserve committed experimental definitions, fixtures, result records, provenance bindings, and synthesis across empirical releases.
- Preregister comparisons where applicable; freeze fixtures and review rules before seeing results. Do not reroll ordinary failures away or change outcomes after reveal.
- Judge score quality and provenance quality separately. Gather evidence before changing compiler behavior, pattern confidence, or golden cases.

## Knowledge and architecture invariants

- Separate historical evidence, interpretation, and prompt implication. Preserve uncertainty, cite sources for factual era/art claims, and never fabricate historical certainty.
- Respect the distinct behavior of `strict_reconstruction`, `historically_informed`, `period_drama`, and `fantasy_hybrid`.
- Use progressive disclosure and one source of truth. Compose route and knowledge modules instead of duplicating prompt libraries.
- Explicit user instructions outrank defaults. Keep reference-image roles isolated as permission boundaries.
- Keep era, art method, artifact form/state, and transformation route separable. Use a structured internal specification and a readable final prompt.
- Let evaluation and gallery cases consume shared case/evidence data. Evaluate semantic, aesthetic, historical/cultural, material, identity, and technical dimensions independently.

## Validation and handoff

From the repository root, run `python -m pytest -q` and `python scripts/validate_repo.py` for a full change. The validator regenerates some checked-in case and regression artifacts; inspect the diff afterward and do not commit unrelated changes. CI runs these same commands. For module changes, follow [docs/CONTRIBUTING_MODULES.md](docs/CONTRIBUTING_MODULES.md).

At the end of meaningful work, update [docs/SESSION_HANDOFF.md](docs/SESSION_HANDOFF.md) with the current branch, worktree, validation, findings, and next task. Keep it concise; Git history is the detailed log.
