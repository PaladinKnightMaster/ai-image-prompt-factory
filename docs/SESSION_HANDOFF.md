# Session Handoff

Purpose: Allows ChatGPT, Work, Codex, or a human developer to continue from repository state without relying on previous conversation history. Read [project state](PROJECT_STATE.md), [roadmap](ROADMAP.md), and [decisions](DECISIONS.md) first.

## Current handoff

- Date: 2026-09-23
- Environment: Codex desktop, local Windows repository
- Branch: `codex/v3-4-architecture-freeze`
- HEAD: this architecture freeze commit; resolve with `git rev-parse HEAD` after checkout
- Base HEAD: `a86b66cee21c37e9a055ee0b3809082b7413d370` on `main`
- Worktree: clean after documentation commit (verify with `git status`)
- Stable release: V3.3 Empirical Lab, tag `v3.3.0`
- V3.4 status: Architecture frozen — implementation next; implementation has not started or completed

### Architecture freeze completed

The approved architecture is [docs/V3.4_ARCHITECTURE_FREEZE.md](V3.4_ARCHITECTURE_FREEZE.md). The final amendments name the lexical realization profile `historical_precision`, name semantic/domain pack references `concept_refs`, and clarify globally unique concept IDs without requiring globally unique preferred terms. The approved component boundaries, four MVP transformation families, approximately 30 MVP concepts, and V3.3 empirical evidence remain unchanged.

### Files changed

`docs/V3.4_ARCHITECTURE_FREEZE.md`, `docs/PROJECT_STATE.md`, `docs/ROADMAP.md`, and `docs/SESSION_HANDOFF.md`.

### Validation performed

`python -m pytest -q`: 171 passed, with one nonfatal pytest cache-write warning. `python scripts/validate_repo.py`: passed; 19/19 regression cases passed. Both ran through `uv` with the bundled Python because the local `.venv` points to a missing interpreter. Checked local Markdown links in all four changed files. Searched the full architecture document: no `historically_strict` or `lexicon_refs` remains; `lexical_profile`, `lexical_trace`, and `references/lexicon/` remain intact. Confirmed `preferred_term` is not globally unique. `git diff --check` passed. Only the four documentation files changed; no V3.3 empirical evidence, experiment, case, or regression artifacts changed.

### Next exact task

Implement the frozen V3.4 Transformation Intelligence architecture. Do not treat V3.4 as complete until implementation and its required validation are finished.
