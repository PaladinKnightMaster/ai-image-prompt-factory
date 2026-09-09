# AI Image Prompt Factory V3.2

**Visual Intelligence Lab** — an installable, agentic GPT Image 2 prompt compiler that combines evidence-backed historical/material reasoning with an internal prompt/image research corpus, prompt-mechanism decomposition, a VisualPattern registry, controlled ablation experiments, and first-party benchmark planning.

V3.2 does **not** ship the private 606-image research corpus in the public release. It ships derived metadata/indexes and tooling, and reconnects to the private corpus through `AIPF_CORPUS_PATH` or the internal-gallery generator.

## V3.2 in one sentence

> V3.1 taught the system how to justify visual knowledge; V3.2 teaches the project how to turn collected examples into testable mechanism hypotheses without confusing correlation with causal evidence.

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

## What V3.2 adds

- Internal corpus model for APC/FSC/GAC/LAC/LCC with verified collection provenance and a hard private/public boundary.
- Corrected LAC/LCC mapping from V3.1: LAC = Liyue AI, LCC = Larus Canus / MrLarus.
- 191 extracted source-prompt records and prompt-mechanism decomposition into functional clauses.
- Prompt-method taxonomy covering structure, emotion, medium, reference, narrative, constraints, design systems, process, result and variable templates.
- Low-signal prompt audit for unverified/redundant quality and camera-brand language.
- 33 initial `VisualPattern` records with explicit observation/hypothesis/support states.
- Confidence-gated compiler eligibility: unvalidated corpus observations cannot silently enter production prompts.
- 15 controlled experiment/ablation plans; none are falsely marked executed without real image generation.
- 20 first-party benchmark candidates/specs/compiled prompts; promotion requires actual output, evaluation and human approval.
- Internal searchable prompt/image gallery generator, separate from the public benchmark gallery.
- Prompt clause traceability and pattern-aware semantic diffing.
- V3.1 evidence, historical strictness, survival-bias handling, 10 golden cases and 19 semantic/prompt regressions remain intact.

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

The source images live outside the distributable repository. Point V3.2 at the extracted private corpus or use the ingestion tools:

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

A collected source example is an observation, not proof that every phrase in its prompt caused the output. V3.2 uses the sequence:

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

V3.2 includes planned tests for posture mechanics, material physics, hand-object interaction, layered composition, camera-brand language, `8K/masterpiece` language, negative-prompt density, emotional adjective stacking, natural-language vs JSON-style briefs, garment construction, fabric physics, identity-lock repetition, explicit reference-role declarations, and pre-compiler historical adaptation.

Offline planning is first-class. If no generation API is available, experiments remain `planned`; the repository does not invent visual scores or conclusions.

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

V3.2 targets `gpt-image-2` first and records the dated model snapshot when known. Unsupported parameters are not invented.

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

## Scope boundary

V3.2 establishes a trustworthy visual-learning laboratory; it does not claim that its 33 initial patterns are scientifically proven, that its 15 planned experiments have been executed, or that 20 benchmark candidates are visual golden baselines. Those execution-dependent steps are the intended next empirical milestone.

See `docs/ADR-0003-v3.2-visual-intelligence-lab.md`, `docs/PROMPT_MECHANISM_MODEL.md`, `docs/VISUAL_PATTERN_REGISTRY.md`, `docs/EXPERIMENT_LAB.md`, and `docs/VALIDATION_REPORT_V3_2.md`.
