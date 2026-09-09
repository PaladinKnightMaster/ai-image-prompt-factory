# V3.2 Validation Report

**Release:** 3.2.0  
**Release theme:** Visual Intelligence Lab  
**Audit date:** 2026-09-07  
**Target model:** `gpt-image-2` (dated snapshot recorded as `gpt-image-2-2026-04-21` when reproducibility metadata is available)

## Executive result

V3.2 passes its offline release acceptance layer. It adds an internal source-corpus research system, prompt-mechanism decomposition, a confidence-gated VisualPattern registry, controlled experiment definitions, first-party benchmark candidates, and an explicit private/public asset boundary while retaining the V3.1 evidence/compatibility/regression system.

The release does **not** claim that planned visual experiments have been executed. No GPT Image 2 output was generated in this build session for the controlled V3.2 experiment suite, so there are no fabricated visual scores, causal findings, or newly promoted visual golden baselines.

## Structural validation

Final working-tree validator result before packaging:

```json
{
  "ok": true,
  "skill_version": "3.2.0",
  "compiler_version": "3.2.0",
  "json_files": 198,
  "era_packs": 13,
  "art_methods": 12,
  "evidence_sources": 20,
  "evidence_claims": 22,
  "evidence_relationships": 2,
  "golden_cases": 10,
  "compiled_golden_cases": 10,
  "regression_cases": 19,
  "regression_passed": 19,
  "regression_failed": 0,
  "corpus_assets": 606,
  "corpus_unique_hashes": 587,
  "corpus_duplicate_extra_files": 19,
  "visual_patterns": 33,
  "compiler_eligible_patterns": 8,
  "experiment_definitions": 15,
  "executed_experiments": 0,
  "benchmark_candidates": 20,
  "benchmark_golden": 0,
  "errors": []
}
```

The packaged-copy audit is rerun after ZIP creation; any difference from these numbers is a release failure.

## Automated tests

```text
41 passed
```

The suite covers the V3.0/V3.1 compiler foundation plus V3.2-specific behavior including:

- authoritative collection mapping;
- LAC/LCC non-reversal regression;
- prompt extraction/decomposition;
- bilingual prompt-method detection;
- low-signal audit;
- VisualPattern validation/confidence gating;
- unvalidated-pattern exclusion from compilation;
- supported-pattern traceability;
- single-factor ablation mutation rules;
- experiment metadata completeness;
- benchmark filtering/promotion rules;
- internal/public corpus boundary;
- V3.1 evidence and compatibility behavior.

## Regression suite

The 19 V3.1 semantic/prompt regression fixtures remain active and all pass:

```text
19 / 19 passed
0 failed
```

The fixtures continue to cover:

- Tang blue-and-white behavior across all four historical strictness modes;
- Ming + Wuxia overlay behavior;
- Wuxia without a historical base;
- Xianxia as fantasy overlay rather than historical evidence;
- Dunhuang strict narrowing;
- Greek living-vs-artifact distinction and polychromy/survival bias;
- Roman bronze-specific material logic;
- Edo ukiyo-e process logic;
- Edo ceramic without print-method leakage;
- identity/outfit/pose/style/layout reference-role isolation.

Historical case metadata that records `3.1.0` is intentionally retained where it describes when an existing fixture/baseline was created. Active V3.2 runtime scripts and newly packaged cases identify `3.2.0`.

## Internal corpus audit

The upgraded Image Library was re-scanned from the actual archive rather than trusting an inherited report.

```text
Total source files             642
Image assets                   606
Text/data documents             36
Unique image SHA-256 hashes    587
Exact duplicate groups          19
Exact duplicate extra files     19
```

Collection counts:

```text
APC  AIPixLab Collection        100
FSC  Fashion Style Collections   24
GAC  Game_Anim Style Collections 33
LAC  Liyue AI Collection         71
LCC  Larus Canus Collection     378
```

All five collection mappings are recorded as project-owner-verified X provenance. LAC is mapped to Liyue AI (`https://x.com/liyue_ai`) and LCC to MrLarus (`https://x.com/MrLarus`).

### V3.1 provenance bug corrected

Manual source review exposed a V3.1 mapping defect: LAC and LCC source documents were reversed in `src/aipf/corpus.py`. V3.2 corrects the mapping and includes a regression test to prevent recurrence.

## Prompt extraction and association

V3.2 extracted:

```text
Source prompt records                     191
Exact section-level image/prompt pairs    463
Probable pairs                              0
Unknown / intentionally unpaired          143
```

An earlier V3.2 candidate attempted to force-match some APC images when one source section contained several possible prompts. Manual contact-sheet review showed that this could attach the wrong prompt to an image. The association rule was changed to fail conservatively:

- exactly one unambiguous candidate in the relevant section -> `exact_section`;
- multiple plausible candidates -> `unknown`;
- no invented pairing.

The lower but reliable 463-pair count is the release metric.

## Prompt-mechanism decomposition

The 191 source prompts are decomposed into functional visual-control clauses instead of treated as monolithic spells. Current categories include identity, pose, body mechanics, hand logic, wardrobe, hair, makeup, material, fabric physics, artifact form, environment, camera, composition, lighting, color, emotion, narrative, text/layout, reference role, constraints, and low-signal quality wording.

Corpus-wide method detection currently finds strong use of structure, emotion, medium, design-system, result, constraint, variable-template, narrative, reference and process methods. The decomposition is bilingual enough to classify the manually inspected Chinese GAC source that initially returned an empty method set; this defect was fixed during manual review.

The analyzer reports 144 prompt records with at least one quality-audit finding. These are diagnostic hypotheses, not proof that the flagged language harms output.

## VisualPattern registry

V3.2 contains:

```text
VisualPatterns                33
Compiler-eligible patterns     8
```

Pattern records explicitly separate:

- source observation;
- mechanism hypothesis;
- validation status;
- evidence/source examples;
- experiment relationships;
- failure modes;
- compiler eligibility.

Most corpus-derived patterns remain `hypothesis` or `observed` and are **not** compiler-eligible. The eight eligible patterns are a small, explicitly supported subset grounded in existing project rules/V3.1 semantics and human curation; their records do not falsely claim controlled V3.2 experiment support. Compiler trace output identifies each injected pattern and its validation basis.

## Experiment lab

Definitions:

```text
Planned experiments   15
Executed experiments   0
```

All 15 current definitions pass the single-factor mutation validator. The planned experiments cover:

1. explicit posture mechanics vs generic pose language;
2. material physics vs material name only;
3. director micro-story;
4. explicit hand-object mechanics;
5. layered spatial roles;
6. camera-brand wording;
7. `8K/masterpiece` wording;
8. targeted constraints vs broad generic negative stack;
9. precise emotional direction vs adjective stacking;
10. natural-language brief vs JSON-style structure;
11. garment construction detail;
12. fabric physics;
13. repeated vs single identity lock;
14. explicit vs implicit reference-role declaration;
15. historical adaptation before compilation vs post-hoc negative prompting.

No experiment report is labeled executed without output metadata.

## First-party benchmark planning

V3.2 contains:

```text
Benchmark candidates       20
Compiled benchmark specs   20
Generated candidates        0
Golden visual benchmarks    0
```

All 20 semantic benchmark specifications compile successfully. They cover reference-role isolation, Tang/Dunhuang/Ming+Wuxia/Edo/Greek/Roman cases, art methods, and Director mechanics.

Promotion rules are fail-closed: a candidate cannot become golden without a real generated output, generation metadata, evaluation and human approval.

## Gallery validation

### Internal research gallery

A local static internal gallery was generated successfully from the source corpus:

```text
Assets represented    606
Thumbnails             606
Approx. gallery size   9.8 MB
```

It exposes collection, association status, prompt methods and associated prompt text for research. It is not part of the public release ZIP.

### Public gallery

The public gallery was regenerated from project case records:

```text
Case records             29
Publishable corpus images 0
```

The public/internal boundary is enforced by repository validation: collected raster assets in the distributable repository tree cause a validation error.

## Manual inspection

Manual release inspection covered:

- 20 exact image/prompt associations;
- the corresponding 20 prompt decompositions;
- 10 VisualPatterns;
- all 15 experiment plans;
- representative compiled benchmark prompts;
- internal-gallery rendering and public-gallery filtering.

Manual review directly caused three corrections:

1. LAC/LCC source mapping was fixed.
2. Ambiguous APC image/prompt force-matching was removed.
3. Chinese prompt-method decomposition was expanded so Chinese structured prompts no longer appear method-empty.

See `docs/MANUAL_INSPECTION_V3_2.md`.

## Public/private boundary

The public release intentionally contains:

- code;
- schemas;
- evidence records;
- derived source-corpus indexes;
- VisualPatterns;
- experiment definitions;
- first-party benchmark specifications/compiled prompts;
- tests;
- docs;
- public case gallery.

It intentionally excludes:

- the 606 full-resolution collected source images;
- the generated internal research gallery and its thumbnails;
- API keys/local credentials;
- local absolute corpus paths;
- generated caches and temporary files.

The project owner reports creator approval for the collected source material but has chosen to keep it private for internal development/research. The packaging boundary is therefore an explicit product/engineering rule rather than an inference about public redistribution rights.

## Model execution status

GPT Image 2 remains the primary adapter target. V3.2 preserves prompt-only, host-native, direct API and editing/evaluation paths. Direct API execution is opt-in and dry-run by default.

This release session did not execute the 15 controlled visual experiments. Therefore:

- no causal ablation finding is claimed;
- no automatic visual score is reported as empirical truth;
- no first-party visual benchmark is promoted to golden;
- camera-brand, `8K/masterpiece`, and related low-signal findings remain hypotheses to test.

## Definition-of-done assessment

V3.2 demonstrates the offline portion of the intended learning loop end to end:

```text
collected source example
→ prompt/image association
→ prompt mechanism decomposition
→ candidate VisualPattern
→ experiment definition
→ controlled prompt variants
→ future generation/evaluation slot
→ confidence-gated compiler eligibility
→ first-party benchmark candidate
```

The generation/evaluation portion is deliberately left unexecuted rather than simulated. That is the main empirical task for V3.3.

## Packaged-copy verification

A release candidate ZIP was extracted into a fresh directory and tested from the extracted copy rather than from the working tree. Results:

```text
pytest                           41 / 41 passed
semantic/prompt regressions      19 / 19 passed
benchmark spec compile smoke     20 / 20 passed
structural validator             OK, zero errors
raw source raster assets          0 in public repository tree
```

The final release packaging repeats this extraction/test process after this report is frozen. The external release checksum file is the authoritative checksum for the delivered ZIP.
