# ESR-v0.1 Boundaries and Claim Limits

## Track separation

| Track | Label | Evidence quality |
| --- | --- | --- |
| **A** | EXP-019 preregistered scientific research | Only under frozen EXP-019 contracts and authorized gates |
| **B** | ESR exploratory self-review | Product feedback / hypothesis generation only |
| **C** | Engineering regression (`aipf regress`, baselines) | Compiler / text stability — not visual quality proof |
| **D** | Public Prompt Library / Gallery | Demonstration / curation under rights + human approval |

ESR materials must not share scientific evidence labels with Track A or imply equivalent evidence quality.

## What ESR may claim

- Owner self-review scores under `ESR-IQ-v0.1` with disclosed partial anonymization
- Directional product hypotheses after reveal
- Process readiness for a future PR2 package→freeze→reveal tool

## What ESR must not claim

- Confirmatory scientific evidence
- Independent human validation or inter-rater reliability
- Full blinding
- EXP-019 scientific admission or replacement of EXP-019 scoring
- Tamper-proof, independently certified, or externally anchored evidence from owner-local hashes alone
- Automatic public-gallery publication

## Evaluator and AI labels

| Field | Required value |
| --- | --- |
| `evaluator_identity_class` | `owner_self_review` |
| `independent_reviewer` | `false` |
| `scientific_status` | `exploratory` |
| `blindness_claim` | `partial_anonymization_only` |

AI advisory assessment (if used later) must be labeled `ai_assisted` and must **not** count as a second human assessor.

## M8 and G3 assessor language (corrected)

**Do not cite an “independent-reviewer waiver.”** No such waiver document authorizes ESR or EXP-019 scientific dual-human replacement.

Repo-verified distinctions:

1. **Draft G3 hardening item M8** refers to Q5 unsigned review artifact handling (sign only with signature + confirm). It is **not** an independent-reviewer waiver.
2. **G3 assessor-role deviation** (owner self-assessment + optional ChatGPT advisory) applies to the **G3 nonexperimental pilot only**, must not be described as independent human assessment, and does **not** change future scientific independent-review requirements.

ESR stands on its **own** honesty labels above. G3 deviation is precedent for clear labeling only.

## Integrity language

PR2 should reuse V3.3 patterns: canonical hashing, atomic writes, freeze-before-reveal, commitment verification, append-only correction history by procedure.

Owner-controlled hash verification detects casual post-freeze edits when the verifier is run. It does **not** provide an external provenance remote or third-party attestation.

## Gallery and library

Public gallery selection remains independent of ESR status. Rights clearance and explicit human approval remain mandatory. Do not copy private EXP-019 or sealed scientific materials into the gallery because an ESR score exists.

## Packaging note (PR1)

`data/schemas/esr_review.schema.json` is validated from the repository tree by tests. Inclusion in `aipf_packaging/resource_inventory.json` (wheel/sdist knowledge allowlist) is a **follow-up packaging decision** outside the minimal PR1 file scope unless separately authorized.

## Prohibited coupling

Do not modify or invoke for ESR claims:

- `src/aipf/experiment_review.py` scientific experiment path behavior
- `src/aipf/exp019_review.py` or EXP-019 dual R1/R2 / remote freeze checkpoints
- EXP-019 preregistrations, amendments, or sealed evidence
- G4/G5 authorization
- V3.4 prompt-generation behavior changes solely for ESR

## Milestone honesty

| Milestone | Delivers |
| --- | --- |
| **PR1** | Protocol, rubric, boundaries, schema, fixtures, automated schema tests |
| **PR2** | Minimal package → score → freeze → verify → reveal workflow |

PR1 alone is **not** an operational evaluation system.
