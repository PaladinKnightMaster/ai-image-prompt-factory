# Experiment Results

AIPF stores completed empirical experiment findings in **both JSON and Markdown**.

- `*.result.json` is the canonical machine-readable source of truth used for validation, aggregation, confidence updates, and future tooling.
- `*.RESULT.md` is the human-readable report used for code review, research discussion, release notes, and the website.

When the two representations disagree, the JSON record is authoritative and the Markdown report must be regenerated or corrected.

Results must preserve the run ID, experiment version, review hash, mapping commitment, aggregate scores, evidence classification, limitations, and raw revealed score mapping. Small-N experiments must use evidence language such as `supports`, `weakly_supports`, `inconclusive`, `weakly_contradicts`, or `contradicts`; they must not claim statistical significance without an appropriate statistical design.

## Recorded V3.3 results

- `EXP-001-1.0.1-20260910T132045Z-DEQ4` - explicit pose mechanics vs generic pose language; **weakly_contradicts**.
- `EXP-002-1.0.1-20260910T181605Z-2GVM` - explicit material physics vs material-name-only; **contradicts**.
- `EXP-004-1.0.1-20260910T221621Z-EK6M` - explicit hand-object mechanics vs generic holding; **supports**.
- `EXP-003-1.0.1-20260911T124433Z-SGB4` - director micro-story vs semantically matched static description; **supports**.
- `EXP-005-1.0.1-20260911T175641Z-U8ZL` - explicit layered spatial roles vs generic cinematic depth; **weakly_supports**.
