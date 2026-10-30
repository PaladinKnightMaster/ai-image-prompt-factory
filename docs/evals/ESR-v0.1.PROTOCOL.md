# ESR-v0.1 Protocol — Exploratory Self-Review

**Status:** contract foundation (PR1). Not an operational evaluation system until PR2 lifecycle code exists.\
**Scientific status:** exploratory product-quality feedback only.\
**Evaluator:** one — project owner as operator and self-reviewer.\
**Independence:** not established.\
**Blindness:** `partial_anonymization_only` — never claim full blinding.

This protocol does **not** amend EXP-019, authorize G4/G5, or admit gallery assets.

## Purpose

Provide a versioned, zero-budget owner self-review workflow for comparing prompts and images without paid external reviewers, without dual independent human scoring, and without confirmatory scientific claims.

## Stages

| Stage | Name | Action |
| --- | --- | --- |
| **S1** | Common-brief scoring | Score partially anonymized images against a **shared task brief** only |
| **S2** | Freeze | Lock S1 scores; verify integrity hashes (PR2 runtime) |
| **S3** | Reveal | Release private treatment mapping only after verified freeze |
| **S4** | Post-reveal diagnostics (optional) | Prompt-specific notes stored **separately**; never rewrite frozen S1 scores |

Intended operational order (PR2):

`VALIDATE PROMPT → (optional AUTHORIZED GENERATE) → PRESERVE → DE-IDENTIFY → S1 → S2 → S3 → S4 → REPORT`

PR1 implements documentation and the S1 score-document schema only. No generation is authorized by this document.

## Common task brief

Every session has one reviewer-visible **task brief** that is identical across arms:

- Subject and constraints to satisfy (basis for D1)
- Shared **style target** (basis for D3) — required
- Shared **transformation target** when `transformation_in_scope` is true (basis for D6)
- Digest: `task_brief_sha256` over the canonical brief payload (algorithm aligned with V3.3 canonical JSON hashing — see Integrity)

The brief **must not** contain candidate prompt text, candidate ids, or treatment labels.

## Reviewer-visible vs private

| Reviewer-facing (S1 package) | Private until S3 reveal |
| --- | --- |
| Anonymized images under `review_id` | Candidate / treatment assignment |
| Task brief + digest | Candidate-linked `prompt_sha256` |
| Blank/filled score sheet (`esr_review` document) | Mapping `review_id → candidate` |
| Presentation order by `review_id` | Generation receipts binding prompts to images |
| Recognition / notes fields | Operator generation workspace paths |

A reviewer-facing package **must never** expose candidate identifiers, treatment assignments, or candidate-linked prompt digests before reveal.

## Prespecified generation and inclusion (session planning)

Before any authorized generation (future), record:

- Planned generation count
- Output-inclusion rules (which successes enter review; exclusions listed)
- Model identity and relevant settings
- Candidate prompt identifiers and exact prompt digests (private)

PR1 does not implement generation.

## Anonymized presentation

- Fresh random `review_id`s (pattern compatible with `esr_review.schema.json`)
- Presentation order randomized / sorted by `review_id` only
- Prefer metadata-stripped review copies (PR2); do not assume byte-identical host exports are metadata-free

## Recognition, deviations, contamination

- Per item: `recognized_image_or_treatment` ∈ `{none, suspected, certain}`
- Record protocol deviations in `deviations`
- If mapping or treatment identity is exposed before freeze → `contamination_status: contaminated_pilot` (usable for process practice; not for comparative product claims or gallery promotion)

## Score document

Machine-readable S1/S2 shape: `data/schemas/esr_review.schema.json`.\
Human rubric: `docs/evals/ESR-IQ-v0.1.RUBRIC.md`.\
Boundaries: `docs/evals/ESR-v0.1.BOUNDARIES.md`.

### S4 post-reveal diagnostics (optional; separate artifacts)

S4 records are **not** fields inside the frozen S1/S2 review document and are **not** part of the payload hashed as `review_sha256`.

Required linkage and immutability rules:

1. Store every S4 artifact **separately** from the frozen S1 scoring record (`review.frozen.json` or equivalent).
2. Every S4 artifact **must** reference the corresponding frozen review identifier: `review_id`.
3. Every S4 artifact **must** also reference the verified frozen-review canonical SHA-256: `review_sha256` (same V3.3-style canonical JSON digest used at freeze — no alternate hashing scheme).
4. S4 diagnostics **must never** modify, replace, or recalculate frozen S1 scores.
5. PR2 runtime **must** verify that the referenced `review_id` and `review_sha256` match the frozen artifact before accepting the linkage; reject otherwise.

Label S4 content as non-frozen diagnostic (e.g. post-reveal prompt-specific notes after treatment reveal). Candidate identity may appear in S4 only **after** S3 reveal.

## Integrity (intended PR2 contract)

Reuse the V3.3 **patterns** (do not modify scientific experiment review code in PR1):

- Canonical JSON SHA-256 (`sort_keys`, compact separators, UTF-8)
- Atomic JSON writes
- Mapping commitment and package hash before scoring
- Freeze-before-reveal with frozen review hash verification (`review_sha256`)
- Corrections via new revision only (immutable-by-procedure history)

**Limits:** owner-controlled local hashes are not an external trust anchor, not independently certified, and not tamper-proof against a party with filesystem write access.

## PR2 runtime validation (not fully enforceable in JSON Schema)

The following must be checked by PR2 code even when a document validates against `esr_review.schema.json`:

1. Every `items[].review_id` appears exactly once in `presentation_order` and vice versa.
2. `review_id` values are unique across `items` (schema only enforces uniqueness inside `presentation_order`).
3. Review images exist, match declared digests in the **private** mapping, and reviewer package omits private fields.
4. Freeze rejected unless S1 complete under rubric rules; reveal rejected unless freeze verifies.
5. S4 artifacts remain separate files; each cites `review_id` + `review_sha256`; linkage is accepted only after those values verify against the frozen review; S4 never mutates frozen scores.
6. Canonical digests of brief/prompts/images match recomputation.

## Limitations (always disclose)

- Single owner self-review; independence not established
- Partial anonymization only; owner-authored candidate prompts increase recognition risk
- No confirmatory scientific evidence; no EXP-019 admission
- AI advisory (if used later) is not a second human assessor
