# Licensing and Provenance

This document is engineering guidance, not legal advice.

## Project-authored material

V3/V3.1/V3.2 compiler code, schemas, cases, evidence normalization, tests, documentation, and generated metadata indexes in this repository are project-authored unless a file states otherwise. The repository license is MIT.

## External repository inspiration

V3/V3.1/V3.2 studied public projects including the Female Portrait Director / Female Outfit Director family, Garden GPT Image 2 skill, `awesome-gpt-image-2`, and other prompt-skill collections. Architectural ideas such as progressive loading, explicit routing, runtime modes, atomic prompt semantics, and case galleries informed design choices. V3.1 does not intentionally copy their prompt libraries or source code into the repository.

Upstream licenses/terms should be checked at the pinned source/version before code is ever vendored. Architectural inspiration is documented separately from code reuse.

## Historical/art research

`evidence/sources/registry.json` records URLs, institutions, source type, relevance and copyright notes. The repository stores structured claims/paraphrases and provenance rather than mirroring copyrighted museum/academic pages or redistributing their images.

## Image Library

The project owner reports creator approval for the collected source material and has chosen to keep the 606-image corpus private for development/research rather than publish it. V3.2 therefore treats all collected samples as `private_reference`: raw source images and the internal gallery are excluded from the public release package, while derived metadata and mechanism hypotheses may be stored in the repository. This is an engineering boundary, not a claim about public redistribution licensing.

## Public gallery rule

A public output image must be project-generated/first-party or have explicit publishable redistribution status. Unknown-license and private-reference assets are excluded regardless of visual quality.
