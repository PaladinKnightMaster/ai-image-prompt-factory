# AI Image Prompt Factory V3.3
[![CI](https://github.com/PaladinKnightMaster/ai-image-prompt-factory/actions/workflows/ci.yml/badge.svg)](https://github.com/PaladinKnightMaster/ai-image-prompt-factory/actions/workflows/ci.yml)
[![GitHub Pages](https://github.com/PaladinKnightMaster/ai-image-prompt-factory/actions/workflows/pages.yml/badge.svg)](https://github.com/PaladinKnightMaster/ai-image-prompt-factory/actions/workflows/pages.yml)
[![Latest Release](https://img.shields.io/github/v/release/PaladinKnightMaster/ai-image-prompt-factory)](https://github.com/PaladinKnightMaster/ai-image-prompt-factory/releases/latest)
[![License](https://img.shields.io/github/license/PaladinKnightMaster/ai-image-prompt-factory)](LICENSE)

**[View the public benchmark gallery →](https://paladinknightmaster.github.io/ai-image-prompt-factory/)**

**Empirical Lab** - an installable, agentic GPT Image 2 prompt compiler and controlled visual-research environment combining evidence-backed historical/material reasoning, preregistered prompt experiments, frozen fixtures, reviewer/blind evaluation, execution provenance, replication, transfer testing, and first-party benchmarks.

V3.3 does **not** ship the private 606-image research corpus or private frozen reference images in the public release. It ships public metadata, eligible fixture specifications, result records, provenance-aware tooling, and reconnects to private development assets through configured paths.

## V3.3 in one sentence

> V3.2 built the visual-learning laboratory; V3.3 executes it with preregistration, frozen fixtures, provenance-aware generation, controlled review, replication, external-validity testing, and cross-experiment evidence synthesis.

## Runtime

```text
User Request
→ Task Classifier
→ Explicit Parameter Lock
→ Reference-Image Role Assignment
→ Route Selection
→ Historical/Cultural Context Detection
→ Evidence Retrieval
→ Compatibility Audit
→ Temporal-Cultural Gate
→ Art/Craft/Material Gate
→ Validated VisualPattern Retrieval (opt-in / confidence-gated)
→ Director Gate
→ Conflict Resolver
→ GPT Image 2 Compiler
→ Optional Generation / Editing
→ Visual Evaluation
→ Regression / Experiment Comparison
→ Surgical Revision
→ Optional First-Party Benchmark Promotion
```

## What V3.3 adds
- Empirical research framework with preregistered single-factor experiments and explicit evidence classifications.
- Frozen first-party reference fixtures, transfer archetypes, and immutable reference ordering for controlled tests.
- Reviewer/blind evaluation workflows with precise blindness claims.
- Task commitments, execution receipts, and SHA-256 prompt/reference/output provenance bindings.
- Ceiling/floor safeguards and explicit treatment of saturated benchmarks.
- Replication workflow separating score strength from provenance quality.
- External-validity testing across independently constructed fixture realizations.
- Cross-experiment synthesis in `docs/V3.3_EVIDENCE_SYNTHESIS.md`.
- Credible positive evidence for explicit identity/outfit/pose reference-role assignment, strongest in EXP-017.
- No fixture-invariant claim: EXP-018 remained inconclusive.
- No statistical-significance claim, automatic compiler mutation, pattern-confidence promotion, or golden promotion from V3.3.
- V3.2 corpus intelligence, VisualPattern discipline, evidence-aware compilation, benchmarks, and public/private boundaries remain intact.
## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

python scripts/validate_repo.py
aipf regress
aipf patterns
aipf experiment-inventory
aipf experiment-plan EXP-001
aipf benchmark-report
aipf prompt-audit path/to/prompt.txt
```

Compile a case:

```bash
python scripts/factory.py compile cases/golden/04-tang-court-lantern/case.json
```

## Internal corpus workflow

The source images live outside the distributable repository. Point V3.3 at the extracted private corpus or use the ingestion tools:

```bash
export AIPF_CORPUS_PATH=/path/to/internal/image-library
python scripts/ingest_corpus.py /path/to/Image\ Library.zip --output-dir corpus/indexes
python scripts/analyze_corpus.py
python internal-gallery/generate_gallery.py \
  --corpus-root /path/to/extracted/corpus-parent \
  --output /tmp/aipf-internal-gallery \
  --thumbnails
```

Current audited corpus state: 606 images, 587 unique SHA-256 hashes, 19 duplicate extra files, 191 source prompts, 463 exact section-level image/prompt associations, and 143 deliberately unknown associations. Unknown is preferable to a fabricated pairing.

## VisualPattern discipline

A collected source example is an observation, not proof that every phrase in its prompt caused the output. V3.3 retains the sequence:

```text
source example
→ functional decomposition
→ mechanism hypothesis
→ VisualPattern
→ controlled experiment
→ confidence update
→ compiler eligibility
```

Only confidence-gated patterns can be injected by the Director Gate. Most corpus-derived patterns intentionally remain observational or hypothetical until controlled GPT Image 2 tests are run.

## Experiment lab

V3.3 executes the empirical-lab workflow rather than treating experiment plans as evidence. The release includes preregistered experiments, frozen fixtures, review packages, provenance-aware execution, published result metadata, replication, and transfer testing.

The final reference-role evidence arc is deliberately bounded: EXP-014 was inconclusive under ceiling saturation; EXP-016 showed a strong score signal but remained provenance-limited; EXP-017 reproduced the positive effect with locally validated execution binding and is the strongest clean supporting result; EXP-018 tested an independent fixture realization and remained inconclusive. See `docs/V3.3_EVIDENCE_SYNTHESIS.md`.
## Benchmarks

`benchmarks/` separates candidate specifications from future generated/golden outputs. A benchmark becomes golden only after generation metadata, evaluation and human approval exist. The initial 20 candidates cover reference-role isolation, Tang/Dunhuang/Ming+Wuxia/Edo/Greek/Roman cases, several art methods, and Director mechanics.

## Public versus internal galleries

- `internal-gallery/` generates the private research browser for the collected source corpus.
- `website/` generates the public case/benchmark gallery from project-owned case records only.

Repository validation fails if collected raster assets are found in the distributable tree.

## GPT Image 2 execution

Compilation remains the primary operation. Direct execution is dry-run by default:

```bash
python scripts/generate_api.py --prompt-file path/to/prompt.md
```

To execute explicitly:

```bash
pip install -e .[api]
export OPENAI_API_KEY=...
export AIPF_DIRECT_API=1
python scripts/generate_api.py --prompt-file path/to/prompt.md --execute --metadata-output generation.json
```

V3.3 targets `gpt-image-2` first and records the dated model snapshot when known. Unsupported parameters are not invented.

## Knowledge layout

- `references/` — era/site/genre/art and director knowledge.
- `evidence/` — versioned historical/material source claims.
- `compatibility/` — mode-sensitive temporal/cultural decisions.
- `visual-patterns/` — empirical visual-generation mechanism hypotheses and supported patterns.
- `experiments/` — controlled/ablation test definitions and future results.
- `corpus/indexes/` — derived internal-corpus metadata only; no raw source images.
- `benchmarks/` — first-party benchmark candidates/specs/compiled prompts.
- `cases/` + `regression/` — historical golden fixtures and executable regression baselines.
- `internal-gallery/` — private research gallery generator.
- `website/` — public case gallery.

## Project state / development

For the current release boundary and next planned scope, start with [project state](docs/PROJECT_STATE.md) and the [capability roadmap](docs/ROADMAP.md). Contributors and agents should follow the [repository operating contract](AGENTS.md).

## Scope boundary

V3.3 closes with credible positive evidence that explicit identity/outfit/pose role assignment can improve cross-reference leakage control, strongest in the provenance-complete EXP-017 replication. It does **not** establish a fixture-invariant effect: EXP-018 did not reproduce the strong A02 separation and remained inconclusive. V3.3 makes no statistical-significance claim and does not automatically change compiler behavior, pattern confidence, or golden benchmarks.

The authoritative detailed synthesis is `docs/V3.3_EVIDENCE_SYNTHESIS.md`. Historical V3.2 architecture remains documented in `docs/ADR-0003-v3.2-visual-intelligence-lab.md`, `docs/PROMPT_MECHANISM_MODEL.md`, `docs/VISUAL_PATTERN_REGISTRY.md`, `docs/EXPERIMENT_LAB.md`, and `docs/VALIDATION_REPORT_V3_2.md`.
