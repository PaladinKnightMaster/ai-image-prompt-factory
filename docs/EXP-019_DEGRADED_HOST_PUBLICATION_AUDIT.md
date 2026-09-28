# EXP-019 degraded host provenance publication audit

Publication candidate on `codex/exp-019-degraded-host-provenance`, based on merged PR #12
(`9e7a963072658f97f6bee98b91bf6b8dcfcdcc81`). Review and merge are still required; no real
degraded operation is authorized by this implementation task.

## Decision and evidence representation

Second post-start addendum: `EXP-019-DHP-20260928-01`, frozen `2026-09-28T20:46:47Z`.
SHA-256: `9d6fb9e7ba6e8f38729d980cb04f612957b26c42518d27f9ff781d03a0f7dc91`.
The first metadata-recovery addendum remains byte-identical and independently checked.

The raw host schema is unchanged. The only exception is the pair of canonical errors for an empty
observed generated path. A separate strict repository-derived wrapper preserves the initial raw
response, full rejection, canonical query and truthful operator attestations. No host response is
normalized, replaced or represented as schema-valid. Trusted capture hashes and permanent
conversation loss are explicit operator claims; this does not invent a signed host provenance source.

Preparation requires the current planned zero-attempt/checkpoint slot, evaluable original raster,
exact original image/raw hashes, frozen addendum and query integrity. It consumes zero attempts
or checkpoints. Finalization separately requires the wrapper/amendment ID and all ordinary operator
receipt scientific bindings. It creates attempt 1, normal canonical bytes and one ordinary checkpoint.
Reservations for recovery and degradation are mutually exclusive; repeats, arbitrary invalid
metadata, manual repair, alternate queries and outcome-informed admission are blocked.

## Result, review and commitment

Legacy normal results retain `provenance_valid: true`. Degraded results instead require
`binding_integrity_valid: true`, a strict aggregate qualification/count, invalid raw schema
conformance and the second post-start amendment identity. Invalid/unadmitted evidence cannot reach
review or analysis. Numerical bands, comparisons, weights, safeguards and interpretation rules
remain unchanged; supportive evidence is possible with a mandatory provenance limitation.

Reviewer-facing files contain only the usual blinded pixels/rubric. Sanitized exports recompute the
verified analysis and allowlist aggregate numbers, safeguards and provenance qualification. They
exclude private paths, raw host data, host IDs, sample IDs/hashes and individual reviewer records.
Final interpretation must retain the aggregate affected count and reduced host-path traceability.

The unchanged six-field external checkpoint commits image/raw/query/receipt evidence. The receipt
commits the immutable wrapper SHA, which commits private rejection/attestations/query/raw and both
addenda. The append-only finalization link is an exact function of anchored receipt/wrapper identities,
avoiding a hash cycle; verification checks it. Preexisting root/attempt digests are not migrated.

## Validation and preservation

Full local unit suite: **477 passed** (423.92 seconds). Categories are disjoint:

| Module/category | Passed |
| --- | ---: |
| New degraded-host admission/integrity/export | 102 |
| EXP-019 execution infrastructure | 51 |
| Host metadata/query integrity | 41 |
| Host-native execution | 26 |
| First metadata-recovery addendum | 41 |
| Preregistration | 3 |
| Remote provenance | 16 |
| Other project tests | 197 |
| **Total** | **477** |

EXP-019 subtotal: 280. Named review, analysis and result selectors respectively cover 41, 10 and
59 test IDs within the full suite (overlapping, not additional tests). Both frozen addenda are
checked by the repository validator. Local validator: **passed**, 579 JSON files (285 source JSON
after publication plus 294 preexisting ignored local JSON), zero errors, **19/19 regression** and
**10/10 golden** cases. No unrelated regenerated artifact changes. Final targeted checks cover
active/preserved byte tampering and review/private-mapping admission guards.

Privacy scan: zero hits across 17 private run/slot/path/capture-hash/host-ID sentinels in added
public content; no real raw sidecar, raster, wrapper, reviewer record or result enters this PR.
All **56 current-run + 31 historical files** remain byte-identical with no added private files.
Canonical active version is v1.1.1. Definition, fixture, metadata query template, strict raw sidecar
schema, first addendum and historical definition match the base. Canonical remote provenance
head remains unchanged. Preparation/import and all empirical work remain unexecuted for the real run.

Only synthetic fixtures exercise the new commands. The integration test uses an actual temporary
bare Git remote, twelve finalized rasters including two independent degraded slots, fifteen
checkpoints, two blind review freezes, reveal, unchanged supportive arithmetic, private result
validation and sanitized export. It asserts every remote checkpoint has exactly six fields and
reviewer/public files exclude private provenance material.

The preservation baseline covers all 56 current-run files and all 31 historical v1.1.0 files.
The real run remains two imported outputs, zero failures, ten pending, zero current-slot attempts,
two attempt checkpoints, and its prior provenance head. No real private evidence is included here.

## Changed surfaces and next action

Normative addendum, private attestation/wrapper schemas, qualified private result schema and aggregate
public result schema; isolated degraded-host module; explicit CLI commands; small canonical-import,
verification, metadata-recovery exclusion and analysis hooks; frozen-amendment validator; synthetic
tests; publication/state/handoff/lab/preregistration disclosure. No frozen scientific source changes.

Changed files (18):

- `.gitattributes`
- `data/schemas/exp019_degraded_host_attestation.schema.json`
- `data/schemas/exp019_degraded_host_evidence.schema.json`
- `data/schemas/exp019_host_result_v1_1_1.schema.json`
- `data/schemas/exp019_public_result_v1_1_1.schema.json`
- `docs/EXP-019_DEGRADED_HOST_PUBLICATION_AUDIT.md`
- `docs/EXPERIMENT_LAB.md`
- `docs/PROJECT_STATE.md`
- `docs/SESSION_HANDOFF.md`
- `experiments/amendments/EXP-019.v1.1.1.DEGRADED-HOST-PROVENANCE-01.md`
- `experiments/preregistrations/EXP-019.PREREGISTRATION.md`
- `scripts/validate_repo.py`
- `src/aipf/cli.py`
- `src/aipf/exp019_analysis.py`
- `src/aipf/exp019_degraded_host.py`
- `src/aipf/exp019_host.py`
- `src/aipf/exp019_metadata_recovery.py`
- `tests/test_exp019_degraded_host.py`

After independent publication review and reviewed merge, a separately authorized operator may
prepare/finalize the blocked original raster through the explicit degraded path as attempt 1,
without regeneration or rewriting its rejected response. This task stops with an open unmerged PR.
