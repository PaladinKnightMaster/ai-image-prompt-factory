# Compatibility Graph

V3.1 uses a graph-like indexed model rather than a binary allowed/forbidden table. The graph nodes are semantic context and evidence claims; edges are contextual relevance and mode-sensitive compatibility decisions.

## Dimensions

The model is designed to expand across time, subperiod, geography, culture, social role/rank, gender presentation where relevant, occasion, clothing/textile, hair/headwear, makeup, jewelry, architecture/furniture, food/tableware, instruments, weapons/tools, transportation, writing, ritual, technology/lighting, flora, visual art, material, and artifact form/state.

V3.1 does not pretend all dimensions are fully populated yet.

## Compatibility vocabulary

`canonical`, `well_attested`, `plausible`, `interpretive`, `rare`, `anachronistic`, `incompatible`, `unknown`.

## Decision status

The historical mode converts evidence compatibility into runtime action:

- `accept`
- `qualify`
- `adapt`
- `reject`
- `allow_hybrid`

A strict Tang request containing mature later-style blue-and-white is therefore not handled the same way as a fantasy-hybrid request containing the same object.

## Explanation

`aipf audit <case>` returns claim ID/version, compatibility, confidence, policy bucket, decision, instruction, source IDs, and survival-bias note. This is diagnostic provenance; the final image prompt remains natural language.

## Progressive disclosure

`claim_paths_for_spec()` routes by historical pack/art method. `select_evidence()` then applies contextual and meaningful trigger matching. Stopword-only overlap is ignored; this behavior is regression-tested because a permissive matcher previously caused unrelated evidence leakage.
