# EXP-019 metadata recovery publication audit

Audit target: branch `codex/exp-019-metadata-recovery-addendum`, based on canonical `main` `57db53766665aabc452be6a82eb19a4d2490d15c`. Publication review is required; this audit does not authorize real recovery or merge.

## Amendment and version decision

`EXP-019-MR-20260928-01` is a post-start procedural addendum layered onto unchanged EXP-019 v1.1.1. It was frozen at `2026-09-28T14:05:13Z`, before any metadata recovery. Exact amendment SHA-256: `b061e5ab023684df102b029d1ed1c319b0cddf24579c51215030be354730512a`. The implementation and repository validator check it; Git pins LF line endings.

A new experiment version would change the definition/run ID and invalidate the existing root's frozen plan. This addendum instead records its ID and hash only in future recovery evidence and future successful attempt receipts. It leaves the two prior finalized outputs and historical v1.1.0 unchanged. The trigger was malformed host capture, not an observed scientific outcome or reviewer score. No private treatment identity was used.

## Rule and implementation audit

Preparation accepts only the current unimported v1.1.1 host-native slot, a decodable raster, an invalid pre-import sidecar, zero slot attempts/checkpoints, and truthful original-conversation/unchanged-image attestations. A valid sidecar cannot be replaced. A directly reported generation/reference/count/edit conflict requires protocol review and cannot be erased through capture recovery.

Preparation preserves exact rejected bytes, hash, detailed validator failures, retained-image hash, slot/run binding, exact rendered query, addendum binding, and zero-attempt status in the private recovery area. It reserves one replay without modifying run-private.json or appending provenance. The previous immediate-collection rule gains only the documented same-chat timing exception for prior text-only metadata/packaging messages.

Stage accepts only the first response to that exact replay, with truthful execution attestations. Exclusive reservation prevents concurrent or partial-stage reuse. Invalid JSON/schema/evidence/attestations consume the sole metadata response, preserve it, and block; there is no third query or generation retry. Successful stage replaces only the active sidecar, after rejected evidence preservation. The retained image and generation-attempt count remain unchanged.

Canonical import checks recovery bindings before ledger events or promotion. It imports generation attempt 1 and binds six recovery evidence file hashes into the canonical attempt receipt; the existing receipt digest commits them in one normal attempt checkpoint. Verification detects later changes. Existing receipts lacking recovery bindings retain their original meaning. No new event type, public checkpoint field, root, run version, scientific definition, host schema, or image retry rule is introduced.

Host execution, same-chat origin, and first-response behavior remain operator-attested, because the host supplies no signed response. Local recovery evidence is not tamper-evident until successful import anchors it. Deliberate pre-import deletion/rewrite of all records is outside that integrity boundary, as disclosed in the addendum. No local validation is represented as proving host behavior.

## Synthetic verification

Final validation: **375 passed**, zero failures. EXP-019 categories: recovery 41; host metadata/query integrity 41; host-native execution/review 26; preregistration 3; remote provenance 16; execution infrastructure 51 (178 EXP-019 tests total). The remaining 197 tests cover the rest of the repository. Repository validator: passed, 576 JSON files, no errors; 19/19 regressions and 10/10 compiled golden cases. The raw-raster privacy gate and live-identifier/private-path scan passed. Validator regeneration produced no unrelated tracked diff.

Tests cover eligibility, valid-sidecar refusal, prior/finalized attempts/checkpoints, rejected-byte preservation, one-replay reservation, partial stage, schema/JSON/UTF-8 failures, immutable image/query/sidecar bindings, wrong-slot response, coaching and all execution attestations, invalid-response exhaustion, manual active-sidecar rewrite, CLI exit/status behavior, recorded-time stability, attempt-1 import, ordinary Git chain verification, privacy-safe checkpoint fields, and finalized recovery-evidence tampering. Tests use synthetic rasters and temporary Git remotes only.

## Real-run preservation and privacy

Before/after snapshots verify all 56 current v1.1.1 files and all 31 historical v1.1.0 files byte-for-byte. This includes BC9QJ5, ZVS8JE, the R5BCSG raster, rejected sidecar, blank receipt, run ledger, generation package, and provenance index. No recovery prepare/stage/replay/import command was executed on the real run. Its state remains 2 generated, 0 failed, 10 planned; R5BCSG is current; there are two attempt checkpoints and head `db6dd155939bd9961f6ed510b482ecec90ca7b62`.

The frozen active/archived definitions, textual fixture, prompt bindings, and metadata-query template remain byte-identical to main. The original metadata schema and root/checkpoint implementation are unchanged. No treatment mapping, host generation ID, raw response, image byte, review, or analysis is added to public artifacts or checkpoint records. The triggering empty-field contradiction is disclosed without host identifiers. Transport ZIPs/checksums/manifests remain optional convenience evidence.

## Changed-file scope

- `.gitattributes`: portable exact amendment bytes.
- `experiments/amendments/EXP-019.v1.1.1.METADATA-RECOVERY-01.md`: frozen normative addendum and post-start disclosure.
- `experiments/preregistrations/EXP-019.PREREGISTRATION.md`: link/disclosure while retaining original scientific rules.
- `data/schemas/exp019_metadata_recovery_attestation.schema.json`: strict recovery execution attestations.
- `src/aipf/exp019_metadata_recovery.py`: explicit private prepare/stage/binding verification.
- `src/aipf/exp019_host.py`: prospective import/receipt guards only.
- `src/aipf/cli.py`: two explicit recovery commands.
- `scripts/validate_repo.py`: byte-frozen addendum gate.
- `tests/test_exp019_metadata_recovery.py`: synthetic recovery and real temporary Git backend tests.
- `docs/EXPERIMENT_LAB.md`, `docs/PROJECT_STATE.md`, `docs/SESSION_HANDOFF.md`: correct current state and operational handoff.
- This audit: reviewable scope, evidence, and limitations.

## Publication conclusion

READY FOR PUBLICATION REVIEW: full suite, validator, regression/golden checks, byte-frozen addendum, and privacy/preservation audits passed. The 13-file scope contains no unrelated generated artifact diff. This is an author-performed publication audit; independent PR review remains required. The branch is prepared as a pull request, with no automatic merge. After reviewed publication/merge and subsequent explicit execution authorization, the existing R5BCSG image is eligible for one exact same-chat metadata replay through the new tooling. No recovery has occurred during this task.
