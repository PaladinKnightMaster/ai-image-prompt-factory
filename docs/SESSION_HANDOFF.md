# Session Handoff

Purpose: Allows ChatGPT, Work, Codex, or a human developer to continue from repository state without relying on previous conversation history. Read [project state](PROJECT_STATE.md), [roadmap](ROADMAP.md), and [decisions](DECISIONS.md) first.

## Current handoff

- Date: 2026-09-23
- Environment: Codex desktop, local Windows repository
- Branch: `chore/project-sync-protocol`
- HEAD: this handoff commit; resolve with `git rev-parse HEAD` after checkout
- Base: `main` at `3617a040483410b4d4e2d0468a48165c69087a3e`
- Worktree: clean after documentation commit (verify with `git status`)
- Stable release: `v3.3.0`, annotated tag on `3c0119e`, integrated into `main`
- Tests: 171 pytest tests passed; repository validator passed (19/19 regression cases)

### What changed

Added a durable Git-centered project-state protocol and forward capability indexes. No V3.4 implementation or experiment artifact was changed.

### Files changed

`AGENTS.md`, `README.md`, `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`, `docs/DECISIONS.md`, `docs/RESEARCH_QUEUE.md`, `docs/SESSION_HANDOFF.md`.

### Validation performed

Checked local Markdown links in all seven changed files. Ran `python -m pytest -q` and `python scripts/validate_repo.py` through `uv` with the bundled Python because the local `.venv` points to a missing interpreter. Pytest reported one nonfatal cache-write warning for `.pytest_cache`. The validator passed; subsequent Git status showed no experimental, case, or regression artifact changes. `git diff --check` passed.

### Important findings

V3.3 is tagged and integrated. Current `main` contains a source-hash notation erratum for EXP-017; the result and scientific conclusions did not change. Existing V3 ADRs, contributor guidance, historical roadmaps, and `manifest.json` were retained as their own sources.

### Known risks / unresolved issues

Cross-fixture generalization for explicit reference roles remains unresolved. The branch is pushed, but PR creation is pending because GitHub CLI returned HTTP 401 and the available browser session is signed out. This branch needs review and merge before its documents become canonical on `main`.

### Next recommended task

Open a process-only PR from `chore/project-sync-protocol` into `main`, review and merge it, then begin a separate V3.4 foundation research task using the P0 [research queue](RESEARCH_QUEUE.md).

### Do not do yet

Do not describe V3.4 as implemented, mutate compiler/pattern/golden behavior from V3.3 reference-role evidence alone, or alter released experimental evidence.

## Reusable handoff template

Replace the current handoff above after meaningful work; do not append a command diary.

```text
Date:
Environment:
Branch:
HEAD: (commit or "this handoff commit; git rev-parse HEAD" when committing this file)
Base:
Worktree:
Stable release:
Tests:

What changed:
Files changed:
Validation performed:
Important findings:
Known risks / unresolved issues:
Next recommended task:
Do not do yet:
```
