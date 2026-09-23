# AI Image Prompt Factory V3.3 - Empirical Lab

## Release boundary

V3.3 closes the Empirical Lab scope. The existing annotated `v3.3.0` tag marks the scientific closure commit `3c0119efdbbbb1e340574cb5c4da95e02f3501ac`.

The authoritative detailed evidence synthesis is [`docs/V3.3_EVIDENCE_SYNTHESIS.md`](V3.3_EVIDENCE_SYNTHESIS.md).

The repository/package release version is 3.3.0. The compiler and evidence-snapshot lineage remains 3.2.0 intentionally because V3.3 did not promote a compiler change or rewrite golden reproducibility artifacts.

## Major additions

- empirical research framework;
- preregistered experiments;
- frozen fixtures;
- reviewer/blind evaluation workflow;
- execution provenance and SHA-256 artifact bindings;
- evidence classification and ceiling/floor safeguards;
- replication workflow;
- external-validity testing;
- cross-experiment synthesis.

## Evidence arc

- **EXP-014:** inconclusive because ceiling saturation limited discrimination.
- **EXP-016:** strong observed score signal, but insufficient generation provenance for a clean experiment-level conclusion.
- **EXP-017:** provenance-complete local replication supporting explicit identity/outfit/pose reference-role assignment; the strongest clean V3.3 result.
- **EXP-018:** independent fixture realization; the strong A02 separation did not transfer strongly enough to cross the preregistered support threshold, so the result remained inconclusive.

## Final scientific position

V3.3 contains credible positive evidence that explicit identity/outfit/pose role assignment can improve cross-reference leakage control. It does **not** establish that the effect is stable across fixture realizations.

V3.3 makes no statistical-significance claim and does not justify automatic compiler mutation, pattern-confidence promotion, or golden promotion.

The contrast between EXP-017 and EXP-018 makes fixture/context sensitivity an important unresolved hypothesis, not a proven causal fixture interaction.

## Review/provenance boundary

EXP-016 remained inconclusive despite a strong score signal because prompt-plus-reference binding could not be independently established for every sample. EXP-017 closed that local provenance gap with task commitments and execution receipts.

EXP-018 uses reviewer-specific blindness and must not be described as using the older strict global review-freeze-then-reveal ordering.

## Release-integrity erratum

The immutable `v3.3.0` closure tag contains an incorrect SHA-256 notation for the EXP-017 public result JSON in `docs/V3.3_EVIDENCE_SYNTHESIS.md`: `281714395d401f3125104a6d48feeeee4658d86da000cac511bc065bb5677bfe`. Post-closure forensic review found no artifact matching that value. The unchanged canonical Git blob at the tag and on current `main` hashes to `d7852692d34b5bdfe9478b0eb394e843874c3c374ae28991de5f28c35b45c3a1`.

Current `main` corrects that binding in the synthesis. The tag is not moved or rewritten, and no experiment output, result, evidence classification, provenance claim, or scientific conclusion changes.

## Post-closure integration

After the scientific closure tag was created, `main` received a CI-portability-only test fix so public GitHub Actions no longer depends on private frozen fixture bytes. That test-only change does not alter experiment outputs, evidence classifications, or V3.3 conclusions.

## Scope boundary

V3.3 is closed. Any new experiment, including a possible EXP-019, belongs to a separate future research scope.
