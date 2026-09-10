# Experiment Lab

Experiments record a hypothesis, baseline prompt, controlled variants, preserved dimensions, target model, evaluation axes, and execution status. V3.2 ships planned experiments but does not claim visual findings because no controlled GPT Image 2 run was executed in this build environment.

## V3.3 host-native execution workflow

V3.3 makes experiment execution host-native first. A run plan assigns opaque
blind IDs to every output slot. `aipf experiment-export <run.json>` creates a
blind-safe generation package containing IDs, prompts, and generation settings
without control/variant labels. Images generated in ChatGPT or another host can
then be recorded with `aipf experiment-import`.

The optional API path remains available for users with API billing, but it is
not required for normal experiment planning, host export, import, or review.
Exact model snapshots must remain `unknown` when the host does not expose them;
the project must not invent snapshot metadata.

## V3.3 double-blind review hardening

Generation blind IDs are not reviewer IDs. Imported outputs are stored in the
neutral `outputs/` directory rather than `control/` or `variant/` directories,
and `aipf experiment-status <run.json>` reports progress without treatment
mapping.

After a completed run, `aipf experiment-review-package <run.json>` assigns a
fresh independent review ID to every image and copies only those re-aliased
images into `blind-review/`. The reviewer-facing manifest and review template do
not contain generation blind IDs, variant IDs, factors, prompts, prompt hashes,
replicate numbers, or image SHA-256 values. Image hashes are intentionally kept
out of reviewer-facing files because a hash exposed earlier in the generation
workflow could otherwise be used to correlate a review ID back to a generation
ID.

The review-ID-to-treatment mapping is stored separately under
`.review-private/mapping.json`. Private mapping entries retain the image SHA-256
values for integrity verification after the review is frozen. A SHA-256
commitment to that mapping is embedded in the reviewer package before scoring.
This prevents the mapping from being silently changed after review while keeping
the correlation key out of the reviewer context.

A review must be fully scored and frozen with
`aipf experiment-review-freeze <blind-review/review.json>` before
`aipf experiment-review-reveal <run.json>` will reveal the committed mapping.
The reveal step verifies the frozen review hash, mapping commitment, package
hash, and run identity before writing `blind-review/reveal.json`.

For a genuinely blind human study, reviewers must not inspect `run.json`,
`.review-private/`, generation metadata, or treatment mappings until after the
review is frozen. Runs whose treatment mapping was exposed to the reviewer
before scoring should be retained as pilot or pipeline-validation runs, not as
fully blinded evidence.

## V3.3 scoring anchors

The 1-5 scale is intentionally stricter than a simple good/bad rating so high-quality model outputs do not collapse at the ceiling:

- **5 — exceptional/clean:** fully satisfies the dimension with no meaningful visible weakness.
- **4 — strong:** clearly successful, but at least one noticeable weakness remains.
- **3 — acceptable/mixed:** usable result with material strengths and weaknesses.
- **2 — poor:** major weakness substantially harms the requested dimension.
- **1 — failed/severe:** the dimension is badly broken or not meaningfully satisfied.

For `technical_defects`, the direction stays the same: 5 means clean/no meaningful defects and 1 means severe visible defects. Reviewers should avoid using 5 as the default for merely good results.

## V3.3 result records

Completed and revealed experiments are persisted under `experiments/results/`. Each evidentiary run uses two representations:

- `*.result.json` — canonical machine-readable evidence record.
- `*.RESULT.md` — human-readable research report derived from that record.

The JSON record is authoritative if the two disagree. Small-N runs use evidence classifications `supports`, `weakly_supports`, `inconclusive`, `weakly_contradicts`, or `contradicts`; they do not claim statistical significance unless the experiment was designed and analyzed for that purpose.

EXP-001 v1.0.1 is the first recorded V3.3 empirical run. It weakly contradicted the hypothesis that explicit posture mechanics generally outperform generic pose language in the tested portrait context. The related VisualPattern therefore remains non-compiler-eligible and is marked `mixed` pending replication.
