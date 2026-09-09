# Internal Corpus Interface

V3.2 treats the collected Image Library as a **development-time research corpus**, not the public benchmark gallery.

The source images remain outside the release ZIP. `corpus/indexes/` contains derived metadata and prompt intelligence:

- `image_library_manifest.json` — 606 source assets, hashes, collection mapping, prompt association status
- `prompt_index.json` — extracted source prompts with functional decomposition
- `duplicate_index.json` — exact SHA-256 duplicate groups
- `ingestion_report.json` — aggregate counts and association coverage
- `pattern_observations.json` — observational mechanism signals used to prioritize research
- `distillation_report.json` — prompt-method/category summary
- `promotion_candidates.json` — explicit internal/public boundary rules

Known source collections are marked `private_reference` / `private_only`. Provenance is separately recorded as verified by the project owner. Unknown or ambiguous prompt/image pairings remain unknown.
