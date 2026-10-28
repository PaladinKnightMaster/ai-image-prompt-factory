# Packaging Portability

PR2 makes the V3.4 prompt-authoring core installable as a self-contained Python
wheel. Canonical knowledge remains the repository trees. Installed wheels receive
a derived, read-only copy of an allowlisted public subset.

## Authority model

```text
Canonical repository knowledge
         |
         v
Build-time staging (aipf_packaging/stage_knowledge.py)
         |
         v
Installed aipf/_knowledge (read-only)
```

The allowlist and content hashes live in
[`aipf_packaging/resource_inventory.json`](../aipf_packaging/resource_inventory.json).
A wheel or sdist build fails if an inventory file is missing or its SHA-256 differs.
Wheel staging copies only inventory paths into `aipf/_knowledge`. The sdist command
filters the setuptools file list through the same inventory so uninventoried JSON
under knowledge trees cannot enter the source distribution.

## Supported installed commands

- `aipf classify`
- `aipf compile`
- `aipf lint`
- `aipf audit`
- `aipf evidence`

Internal APIs for TransformationPack / ArtMethodPack / EraPack resolution,
artifact form/state lookup, evidence selection, compatibility auditing, lexicon
access, lexical realization, and compile traces use the same resource layer.

## Not guaranteed from an installed wheel

These remain worktree or explicitly configured-data workflows:

- scientific experiment execution
- private fixture import
- research corpus ingestion
- internal gallery generation
- full repository validation
- default golden baseline creation
- `aipf regress` / `aipf baseline` without an explicit case directory

`aipf regress` fails closed when the case root is missing or contains zero cases.

## Path resolution

| Path kind | Source checkout | Installed wheel |
| --- | --- | --- |
| Relative knowledge resource | Repository root | `aipf/_knowledge` via `importlib.resources` |
| Absolute input path | Read as given | Read as given |
| Relative output path | Repository root | Current working directory |
| Packaged knowledge writes | N/A | Rejected |

Installed mode does not search the current working directory for knowledge
resources and does not fall back to a developer checkout. Missing packaged
resources raise actionable errors.

## Configuration

Source checkouts still load `.env` from the repository root. Installed wheels do
not treat a virtualenv parent directory as a project repository for `.env`
discovery. Scientific environment-variable names are unchanged; callers must set
them explicitly when needed.

## Build and verify

```bash
python aipf_packaging/stage_knowledge.py verify
python -m build
python -m pytest -q tests/test_package_portability.py
```

A wheel built from the repository and a wheel built from the source distribution
must both contain the inventory resources with matching SHA-256 digests.
