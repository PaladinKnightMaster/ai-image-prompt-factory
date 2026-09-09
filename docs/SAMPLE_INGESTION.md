# Sample Corpus Ingestion

The Image Library is treated as an external evidence/sample corpus, not a runtime asset bundle.

## Pipeline

```text
source ZIP/directory
→ enumerate
→ SHA-256 hash
→ lightweight metadata
→ exact duplicate index
→ collection/tag index
→ license/publication status
→ promotion candidate report
```

## Current V3.1 ingestion result

- source archive: `Image Library(1).zip`
- source archive SHA-256: `c9f8c13df79891d0e6b1e7046d1c87ebaac73fb55af001e8987e665aebccb45f`
- 606 image assets
- 36 text documents
- 587 unique image hashes
- 19 exact duplicate groups / 19 duplicate extra files
- collections: APC 100, FSC 24, GAC 33, LAC 71, LCC 378
- 606 collection-level source-document associations
- 0 exact prompt-to-image associations asserted (filenames do not reliably encode the exact prompt entry)
- 606 assets with unknown redistribution rights
- 0 public-gallery-eligible external sample images

## License-first default

Unknown external samples receive:

- `license_status: unknown_license`
- `redistribution_status: metadata_only`

The public gallery must not emit those images. A private regression baseline can later reference an asset without converting it into a redistributable project asset.

## Duplicate behavior

V3.1 implements exact SHA-256 duplicate detection. It intentionally does not call resized/cropped images duplicates without a real perceptual comparison implementation. Perceptual hashing is a V3.2 extension point.

## Promotion

- **experimental:** unvalidated work.
- **public:** reviewed output + publication permission.
- **golden:** reproducible, semantically important benchmark with validated result and provenance.
- **regression:** designed to catch a named failure; image may remain private if licensing prevents redistribution.
