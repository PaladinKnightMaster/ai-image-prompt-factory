# Evaluation V3.2

Do not use one vague beauty score. The evaluator keeps six axes independent on a 0–5 scale (for `technical_defects`, 5 means clean):

- semantic compliance
- aesthetic quality
- historical/cultural integrity
- art/material fidelity
- identity fidelity when applicable
- technical defects

Each axis has explicit subdimensions in `src/aipf/evaluation.py`. A host vision model or human reviewer may populate the record; this repository does not pretend a visual evaluation happened if no image was examined.

Create a blank record:

```bash
aipf evaluation-template cases/golden/03-roman-bronze-bust/case.json --output evaluation.json
```

Then classify one or more failures from `failure_taxonomy.json`, list what must be preserved, and generate a surgical revision:

```bash
aipf revision evaluation.json
# or structured JSON
aipf revision evaluation.json --json
```

The revision contract is: preserve successful identity/pose/composition/etc.; change only observed failed dimensions.


V3.2 adds experiment-specific subdimensions and human-review fields while preserving the independent top-level score axes. Planned experiments remain unscored until real outputs exist.
