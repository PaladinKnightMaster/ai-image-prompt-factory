# Evidence Model

V3.1 separates four things that prompt collections commonly collapse:

1. **Source** — where information came from.
2. **Claim** — a bounded assertion supported by one or more sources.
3. **Interpretation** — how the claim should be understood for visual reasoning, including uncertainty.
4. **Prompt implication** — a production instruction derived from that interpretation.

## Source records

`evidence/sources/registry.json` stores title, institution/author, source type, URL, date metadata, evidence quality, relevance, copyright notes, and limitations. Evidence quality is not the same as truth certainty; it is a provenance signal.

## Claim records

`evidence/claims/*.json` store:

- `claim_id` and semantic `version`
- subject/value
- contextual selectors (pack, subperiod, region, role, occasion, art method, artifact state)
- compatibility vocabulary
- confidence + confidence reason
- source IDs
- interpretation
- prompt implications / safer alternatives
- trigger keywords
- survival-bias note when relevant
- mode-specific actions

Claims are routed progressively by `evidence/registry.json` and filtered against request context. The current implementation deliberately avoids loading every source/claim into every compilation.

## Confidence

Confidence is a bounded authoring judgment supported by the attached sources; it must not be treated as a statistical probability. New claims should explain why a confidence level was assigned. Weak/conflicting evidence must stay weak/conflicting.

## Evidence snapshot

A compiled case stores the selected claim IDs, claim versions, compatibility labels, confidence values, source IDs, and a deterministic SHA-256. This lets a future knowledge update coexist with an older golden baseline instead of silently changing its historical rationale.

## Source conflict

V3.1 supports conflicts by recording competing claims/contexts rather than flattening them. Prefer specificity:

- High Tang court evidence should not become universal Tang evidence.
- A modern surviving white marble surface should not automatically become evidence that an ancient sculpture was originally unpainted.
- An early/rare cobalt-decorated Tang ceramic should not be generalized into mature Yuan/Ming blue-and-white porcelain conventions.
