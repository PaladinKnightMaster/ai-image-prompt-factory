# ESR-IQ-v0.1 Rubric

**Rubric id:** `ESR-IQ-v0.1`\
**Protocol:** `ESR-v0.1`\
**Scale:** integer **1–5**, **higher is better** for every scored dimension.\
**Score 3 (shared meaning):** usable / mixed — material strengths and weaknesses; neither clearly strong nor failed.

This rubric does **not** replace EXP-019 scientific rubrics or `evaluation.schema.json` case axes.

## Scoring stage

**S1 (frozen scores):** score only against the **common task brief** (and its shared style / transformation targets). Do not use concealed candidate prompt text.

**S4 (optional, non-frozen):** after reveal, optional prompt-specific diagnostics may be recorded separately. They must not rewrite S1 scores.

## Dimensions

### D1 — `task_brief_adherence` (mandatory integer 1–5)

Does the image follow the **shared task brief** subject and constraints?

| Score | Anchor |
| --- | --- |
| **5** | Fully meets brief subject and constraints; no meaningful miss |
| **4** | Clearly successful; at least one minor miss vs brief |
| **3** | Partial / mixed adherence; usable but incomplete |
| **2** | Major misses vs brief |
| **1** | Wrong subject or brief constraints largely ignored |

### D2 — `visual_coherence` (mandatory integer 1–5)

Are geometry, anatomy, lighting, and composition plausible as a picture?

| Score | Anchor |
| --- | --- |
| **5** | Plausible and coherent; no meaningful structural break |
| **4** | Strong; small coherence issues |
| **3** | Noticeable issues but still usable |
| **2** | Major coherence breaks |
| **1** | Collapsed / nonsensical structure |

### D3 — `target_style_fidelity` (mandatory integer 1–5)

Does the image achieve the **shared style target** stated in the task brief (not a hidden prompt)?

| Score | Anchor |
| --- | --- |
| **5** | Clearly achieves the stated style target |
| **4** | Close; minor style gaps |
| **3** | Partial style match |
| **2** | Weak / largely generic relative to target |
| **1** | Wrong style family vs brief |

### D4 — `technical_cleanliness` (mandatory integer 1–5)

Freedom from visible rendering defects (higher = cleaner). Named for higher-is-better clarity (not “severity”).

| Score | Anchor |
| --- | --- |
| **5** | Clean; no meaningful visible defects |
| **4** | Minor artifacts |
| **3** | Moderate artifacts; distracting but usable |
| **2** | Severe artifacts; harms use |
| **1** | Unusable defect load |

### D5 — `prompt_repeatability` (always N/A in ESR-v0.1)

Repeatability is a **generation-group** property, not a per-image score. ESR-v0.1 does not support group-level repeatability machinery.

At freeze / schema validation:

```json
{"value": null, "na_reason": "deferred_protocol_v0_1"}
```

Integer scores for D5 are **invalid**. Other N/A reasons for D5 are **invalid**.

### D6 — `transformation_fidelity`

When `transformation_in_scope` is **true**, score against the brief’s **transformation target** (mandatory integer 1–5):

| Score | Anchor |
| --- | --- |
| **5** | Source→target intent clearly preserved |
| **4** | Mostly preserved; minor slips |
| **3** | Partial transformation |
| **2** | Weak transformation |
| **1** | Failed or wrong transform |

When `transformation_in_scope` is **false**:

```json
{"value": null, "na_reason": "not_applicable_to_task"}
```

If transformation is in scope, the brief **must** include a non-empty `transformation_target`. Scoring D6 as N/A while in scope is **invalid**. Scoring D6 as an integer while out of scope is **invalid**.

## N/A policy

Allowed `na_reason` values in finalized ESR-v0.1 evaluations:

| Reason | Allowed on |
| --- | --- |
| `deferred_protocol_v0_1` | D5 only |
| `not_applicable_to_task` | D6 only, when transformation out of scope |

**Not permitted:** unrestricted `not_scored` (or any other reason) to finalize incomplete D1–D4 evaluations. D1–D4 must be integers 1–5.

When `value` is an integer, `na_reason` must be JSON `null`. When `value` is `null`, `na_reason` is mandatory as above.

## Aggregates

Means and summaries must exclude N/A cells and report `scored_n` per dimension. Do not invent automatic “objective” metrics as proof of subjective quality.

## AI-assisted scores (optional; not required)

If present in a later artifact, keep in a separate object labeled AI-assisted. Never average into human frozen scores as validated consensus. Never treat as a second independent human reviewer.
