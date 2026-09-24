"""Read-only terminology, visible meanings, and non-authoritative candidate lookup."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import re
import unicodedata

from jsonschema import Draft202012Validator

from .io import load_json, repo_root


def normalize(text: str) -> str:
    plain = unicodedata.normalize("NFKD", text.casefold())
    plain = "".join(char for char in plain if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", plain)).strip()


def _surface(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w]+", " ", text.casefold())).strip()


def concepts() -> dict[str, dict]:
    return {record["id"]: record for record in load_json("references/lexicon/registry.json")["concepts"]}


def validate_registry(registry: dict | None = None) -> list[str]:
    registry = registry if registry is not None else load_json("references/lexicon/registry.json")
    schema = load_json("data/schemas/visual_semantic_lexicon.schema.json")
    errors = [error.message for error in Draft202012Validator(schema).iter_errors(registry)]
    seen_ids: set[str] = set()
    terms: dict[str, list[dict]] = defaultdict(list)
    source_ids = {row["source_id"] for row in load_json("evidence/sources/registry.json")["sources"]}
    claim_ids: set[str] = set()
    for path in (repo_root() / "evidence/claims").glob("*.json"):
        claim_ids.update(row["claim_id"] for row in load_json(path)["claims"])
    for record in registry.get("concepts", []):
        cid = record.get("id")
        if cid in seen_ids:
            errors.append(f"duplicate concept ID: {cid}")
        seen_ids.add(cid)
        term = normalize(record.get("preferred_term", ""))
        terms[term].append(record)
        for sid in record.get("evidence_refs", {}).get("source_ids", []):
            if sid not in source_ids:
                errors.append(f"{cid}: unknown source {sid}")
        for claim_id in record.get("evidence_refs", {}).get("claim_ids", []):
            if claim_id not in claim_ids:
                errors.append(f"{cid}: unknown claim {claim_id}")
        if record.get("preferred_term", "").casefold() in {alias.casefold() for alias in record.get("aliases", [])}:
            errors.append(f"{cid}: alias duplicates its preferred term")
    for term, records in terms.items():
        for index, left in enumerate(records):
            for right in records[index + 1:]:
                if (left.get("domain") == right.get("domain") and
                        left.get("retrieval_scope", {}) == right.get("retrieval_scope", {})) or (
                        normalize(left.get("visible_gloss", "")) == normalize(right.get("visible_gloss", ""))):
                    errors.append(f"preferred term {term!r} has insufficiently disambiguated concepts")
    return errors


def lookup_candidates(text: str, registry: dict | None = None) -> list[dict]:
    """Return lexical candidates only: never a compatibility or history verdict."""
    records = (registry or load_json("references/lexicon/registry.json"))["concepts"]
    found: dict[str, dict] = {}
    for field, match_type in (("preferred_term", "preferred_term"), ("aliases", "alias"), ("retrieval_terms", "retrieval_term")):
        query = normalize(text) if field == "retrieval_terms" else _surface(text)
        for record in records:
            phrases = record.get(field, []) if field != "preferred_term" else [record.get(field, "")]
            for phrase in phrases:
                needle = normalize(phrase) if field == "retrieval_terms" else _surface(phrase)
                if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", query):
                    found.setdefault(record["id"], {"concept_id": record["id"], "matched_text": phrase, "match_type": match_type})
                    break
    return list(found.values())


def validate_concept_refs() -> list[str]:
    known = set(concepts())
    errors: list[str] = []
    paths = [Path(row["path"]) for row in load_json("references/art-methods/registry.json")["methods"]]
    paths += [Path(row["path"]) for row in load_json("references/eras/registry.json")["packs"]]
    for path in paths:
        refs = load_json(path).get("concept_refs", {})
        ids = refs.get("core", []) + refs.get("conditional", [])
        if len(ids) != len(set(ids)):
            errors.append(f"{path}: repeated concept reference")
        for cid in ids:
            if cid not in known:
                errors.append(f"{path}: unknown concept {cid}")
    forms = load_json("references/artifacts/forms.json")["forms"]
    for form_id, form in forms.items():
        for cid in form.get("concept_refs", {}).get("core", []) + form.get("concept_refs", {}).get("conditional", []):
            if cid not in known:
                errors.append(f"artifact form {form_id}: unknown concept {cid}")
    return errors
