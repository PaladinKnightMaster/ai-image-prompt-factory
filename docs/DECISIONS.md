# Architectural Decision Index

This is a compact index of accepted operating and architecture decisions, not a transcript. Detailed earlier decisions remain in [V3 architecture](ADR-0001-v3-architecture.md), [V3.1 evidence and regression](ADR-0002-v3.1-evidence-regression.md), and [V3.2 Visual Intelligence Lab](ADR-0003-v3.2-visual-intelligence-lab.md). The [current state](PROJECT_STATE.md) and [V3.3 synthesis](V3.3_EVIDENCE_SYNTHESIS.md) bound present claims.

## ADR-001 - Git repository is canonical project state

**Status:** Accepted. **Decision:** Committed repository content and artifacts are the shared state. **Rationale:** Multiple chat and development environments need a common, inspectable record. **Consequences:** Update state and handoff docs with meaningful work; verify claims against code, evidence, and Git.

## ADR-002 - Progressive disclosure over giant prompt context

**Status:** Accepted. **Decision:** Load only relevant route, era/site, art-method, evidence, and helper modules for a request. **Rationale:** Narrow context improves traceability and avoids unrelated knowledge leakage. **Consequences:** New modules must be routed and selectively loaded. See [V3 architecture](ADR-0001-v3-architecture.md).

## ADR-003 - Composition over duplicated style/era prompts

**Status:** Accepted. **Decision:** Compose structured modules and compile readable prompts instead of maintaining separate prompt libraries for every combination. **Rationale:** Shared rules and data avoid contradictory copies. **Consequences:** Future transformation routes reuse the same knowledge axes. See [knowledge model](KNOWLEDGE_MODEL.md).

## ADR-004 - Era, art method, artifact form, and transformation route remain independent axes

**Status:** Accepted. **Decision:** Model these axes separately, including artifact state. **Rationale:** A period, fabrication method, physical object, and conversion route answer different questions. **Consequences:** Compatibility is evaluated at composition time; no combined label silently substitutes for evidence. See [V3 architecture](ADR-0001-v3-architecture.md).

## ADR-005 - Explicit reference-image roles

**Status:** Accepted. **Decision:** Assign roles as permission boundaries, so an outfit, style, or layout reference does not silently import identity. **Rationale:** This prevents cross-reference leakage and honors user locks. **Consequences:** Preserve role isolation; evaluate claims with provenance. V3.3 provides credible positive evidence in the tested context, strongest in EXP-017, while EXP-018 leaves cross-fixture generalization unresolved. See [synthesis](V3.3_EVIDENCE_SYNTHESIS.md).

## ADR-006 - Empirical evidence gates compiler/pattern promotion

**Status:** Accepted. **Decision:** Keep observations, mechanism hypotheses, controlled results, and compiler eligibility distinct. **Rationale:** A strong image or score alone cannot establish causal mechanism or trustworthy provenance. **Consequences:** Require appropriate controlled evidence and review before promotion; no automatic V3.3 reference-role promotion. See [lab](EXPERIMENT_LAB.md) and [synthesis](V3.3_EVIDENCE_SYNTHESIS.md).

## ADR-007 - Gallery cases also serve as regression/evidence artifacts

**Status:** Accepted. **Decision:** Share case data across compilation, evidence snapshots, regression, and eligible gallery publication. **Rationale:** One case record can be inspected and retested without duplicate facts. **Consequences:** Golden/public promotion requires appropriate provenance and eligibility. See [V3.1 ADR](ADR-0002-v3.1-evidence-regression.md).

## ADR-008 - Separate semantic, aesthetic, historical/cultural, material, identity, and technical evaluation dimensions

**Status:** Accepted. **Decision:** Score these dimensions independently when applicable. **Rationale:** Aesthetic success cannot conceal a broken identity, anachronism, material error, or technical defect. **Consequences:** Revision plans preserve successful dimensions and target failures. See [evaluation model](EVALUATION_V3_1.md).

## ADR-009 - Conversation memory is advisory; committed repository state is authoritative

**Status:** Accepted. **Decision:** Verify chat-derived assumptions against committed files and Git before work. **Rationale:** Sessions can be partial, stale, or inaccessible across environments. **Consequences:** Use [project state](PROJECT_STATE.md) and [handoff](SESSION_HANDOFF.md) as entry points, then inspect the linked primary artifacts.
