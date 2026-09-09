# V3.1 Validation Report

**Release:** 3.1.0  
**Validation date:** 2026-09-07 (America/New_York)  
**Compiler version:** 3.1.0

## Release baseline

V3.1 was built from the immutable V3.0 release ZIP rather than a partially pruned working directory.

| Input | Verification / use |
|---|---|
| `AI_Image_Prompt_Factory_V3_0.zip` | SHA-256 `d902265d301cc7dfdf4210b671ed721ef76ac13ef405706ef5ec21aa86adf252`; architectural baseline |
| `Image Library(1).zip` | SHA-256 `c9f8c13df79891d0e6b1e7046d1c87ebaac73fb55af001e8987e665aebccb45f`; external sample corpus, indexed metadata-only |
| V2.1 / GPT Image 2 source packages | already audited during V3.0; retained concepts reviewed but not bulk-migrated again |

## Structural validation

Command:

```bash
PYTHONPATH=src python scripts/validate_repo.py
```

Final result:

```json
{
  "ok": true,
  "skill_version": "3.1.0",
  "compiler_version": "3.1.0",
  "json_files": 135,
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
  "errors": []
}
```

The validator checks JSON Schema documents themselves, registry targets, knowledge/source/claim/conflict records, case schemas, evidence source references, corpus publication rules, the example evaluator record, all golden compilations, and all regression specifications.

## Automated tests

Command:

```bash
PYTHONPATH=src pytest -q
```

Result:

```text
.............................                                            [100%]
29 passed
```

Coverage includes evidence/source integrity, bounded progressive loading, trigger-leak prevention, historical strictness behavior, evidence snapshot stability, Greek survival-bias states, Roman bronze fabrication, Edo woodblock-versus-ceramic separation, reference-role isolation, Wuxia/Xianxia overlay behavior, semantic and prompt-section diffing, corpus hashing/licensing, evaluator axes, surgical revision, evidence relationships, golden baseline drift, and the original V3 smoke tests.

## Regression results

Command:

```bash
PYTHONPATH=src python scripts/run_regression.py
```

Result:

```json
{
  "ok": true,
  "cases": 19,
  "passed": 19,
  "failed": 0
}
```

The targeted cases cover:

- all four Tang + mature-blue-and-white historical strictness behaviors;
- Ming + Wuxia base/overlay separation;
- Wuxia without a historical base;
- Ming + Xianxia fantasy behavior;
- strict Dunhuang without cave/date narrowing;
- Classical Greek living versus artifact interpretation;
- Greek marble newly-created, excavated, and museum-conserved states;
- Hellenistic reconstruction from later-copy survival evidence;
- Roman bronze material/fabrication behavior;
- Edo ukiyo-e production logic;
- Edo Arita/Hizen ceramic logic without print leakage;
- identity/outfit/pose/style/layout reference-role isolation.

## Golden baseline drift

Commands:

```bash
PYTHONPATH=src python scripts/build_baselines.py
PYTHONPATH=src python -m aipf.cli baseline-check regression/baselines/golden_baselines.json
```

Result:

```text
10 golden baselines
10 stable
0 drifted
```

Baselines include separate hashes for the semantic case, compiled prompt, evidence snapshot, compatibility audit, lint findings, optional evaluation/output data, and compiler/skill/model metadata. Hash stability is a change detector, not a proxy for visual quality.

## Evidence/provenance validation

V3.1 contains:

- 20 structured source records;
- 22 versioned evidence claims;
- 2 explicit claim relationships (chronological variation / interpretive tension);
- source, claim, interpretation, prompt implication, confidence rationale, and survival-bias fields kept separate;
- case evidence snapshots that pin claim versions and source IDs.

The current two relationships are **not** presented as direct scholarly disputes. V3.1 preserves the distinction between chronological/interpretive tension and actual source disagreement.

## Image Library ingestion

The supplied upgraded Image Library was scanned directly.

```json
{
  "source_name": "Image Library(1).zip",
  "source_sha256": "c9f8c13df79891d0e6b1e7046d1c87ebaac73fb55af001e8987e665aebccb45f",
  "image_assets": 606,
  "text_documents": 36,
  "unique_hashes": 587,
  "exact_duplicate_groups": 19,
  "exact_duplicate_extra_files": 19,
  "collection_source_associations": 606,
  "exact_prompt_associations": 0,
  "unknown_license_assets": 606,
  "publishable_assets": 0,
  "public_gallery_eligible": 0
}
```

All external sample images default to `unknown_license` + `metadata_only`. No third-party sample image is copied into the release repository or emitted by the public gallery. Collection-level source-document associations are recorded where the prefix is reliable; exact prompt-to-image associations remain unknown because filenames do not prove an exact prompt match.

## Gallery V2

Command:

```bash
PYTHONPATH=src python website/generate_gallery.py
```

Result:

```json
{
  "cases": 29,
  "publishable_images": 0,
  "json": "website/generated/cases.json",
  "html": "website/generated/index.html"
}
```

The gallery is generated from case records and publication status. Unknown-license corpus assets fail closed.

## Runtime / API smoke checks

`python scripts/check_mode.py --json` resolved this environment to:

```json
{
  "mode": "ADVISOR",
  "can_execute": false,
  "recommendation": "Return/save the compiled prompt; do not claim an image was generated."
}
```

`python scripts/generate_api.py --prompt ... --metadata-output ...` was run in its default dry-run mode. The resulting metadata validated against `generation_metadata.schema.json`; provider/model, model snapshot field, prompt hash, generation mode, compiler/skill version, quality/size, and input reference hashes are representable. Unsupported `seed` is explicitly `null` rather than invented.

No billable or network image-generation call was made for release validation.

## Installation smoke check

An editable install succeeded using the already-installed offline build toolchain:

```bash
python -m pip install -e . --no-deps --no-build-isolation
```

From outside the repository, both `aipf classify` and `aipf compile` executed successfully.

## Manual compiled-prompt inspection

Automated tests were not treated as sufficient. Representative Tang, Dunhuang, Ming/Wuxia, Edo ceramic/ukiyo-e, Classical/Hellenistic Greek, and Roman bronze outputs were inspected manually.

This inspection caught and corrected semantic defects that structural tests alone did not expose:

1. Tang blue-and-white acceptance fixtures initially inherited lantern-hand choreography even when the subject needed to hold a vessel. The fixtures now use explicit vessel-support hand logic.
2. Greek marble artifact-state fixtures initially shared a museum-conservation scene. `newly_created`, `excavated`, and `museum_conserved` now produce distinct physical contexts and surface states.
3. A broad Tang `sancai` trigger could influence unrelated ceramic requests. It was narrowed to explicit Sancai/three-color/Tang-glazed intent.
4. The compiler now states that compatibility adaptations override incompatible raw-request wording, preventing a corrected object from being silently reasserted by the opening task sentence.
5. Evidence trigger matching was tightened after a generic token could select an unrelated historical claim; regression coverage now guards this failure.
6. Final release audit caught a stale `src/aipf/__init__.py` runtime version (`3.0.0`) despite 3.1.0 package metadata; it was corrected to `3.1.0` before packaging.

## Packaged-copy validation

A release-candidate ZIP was created, extracted into a clean directory, and tested from the extracted copy.

Results from the extracted package:

- 29/29 automated tests passed;
- 19/19 regressions passed;
- structural validation returned `ok: true` with zero errors;
- 10/10 golden baselines were stable with zero drift;
- Gallery V2 regenerated 29 cases with zero publishable unknown-license images.

The final release ZIP is rebuilt from the same clean source tree after this report is written and is subjected to the same core validation before delivery.

## Deliberate non-validation / limits

V3.1 implements Level 1 semantic regression and Level 2 prompt regression. **Level 3 visual regression is not claimed as passed** because this release did not generate new GPT Image 2 outputs or run a vision evaluator against first-party output images.

Therefore:

- no visual score was fabricated;
- no historical/art-material module is advertised as museum-grade certification;
- evidence confidence values are curated engineering judgments with explicit source rationale, not statistical probabilities;
- exact near-duplicate image detection beyond SHA-256 is intentionally not faked;
- the Image Library remains metadata-only until redistribution rights are established.

## Release conclusion

V3.1 passes the intended foundation acceptance criteria: evidence is traceable and versioned, uncertainty/survival bias affect compilation, historical strictness materially changes decisions, the sample corpus is indexed without redistribution leakage, semantic/prompt drift is executable in CI without an image API, and the repository preserves a clean path to real first-party visual regression in V3.2.
