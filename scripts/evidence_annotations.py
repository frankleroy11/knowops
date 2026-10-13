"""Versioned, source-grounded alternatives; canonical labels remain unchanged."""

import json
from pathlib import Path


def normalize(value):
    return " ".join(str(value).split())


def load_annotations(evals: Path):
    path = evals / "evidence_annotations.json"
    return json.loads(path.read_text()) if path.exists() else {"version": None, "changes": {}}


def annotation_for(question, evals: Path):
    entry = load_annotations(evals)["changes"].get(question["id"], {})
    if entry and (
        entry["question"] != question["question"] or entry["domain"] != question["domain"]
    ):
        raise ValueError("Annotation question/domain mismatch")
    return entry


def validate_annotations(evals: Path):
    data = load_annotations(evals)
    questions_path = evals / "questions.json"
    questions = (
        {q["id"]: q for q in json.loads(questions_path.read_text())}
        if questions_path.exists()
        else {}
    )
    for id, entry in data["changes"].items():
        for group in entry.get("fact_groups", []):
            if not group.get("fact") or not group.get("options"):
                raise ValueError(f"{id}: empty fact/options")
            for option in group["options"]:
                path = evals / "corpus" / entry["domain"] / option["source"]
                if not option["quote"].strip() or normalize(option["quote"]) not in normalize(
                    path.read_text()
                ):
                    raise ValueError(f"{id}: evidence quote not in {option['source']}")
        for quote in entry.get("strict_terms_additions", []):
            # Additions must be traceable; exact source assignment remains in the canonical scorer.
            sources = [
                evals / "corpus" / entry["domain"] / name
                for name in questions.get(id, {}).get("expected_sources", [])
            ]
            if not quote.strip() or not any(
                normalize(quote) in normalize(p.read_text()) for p in sources
            ):
                raise ValueError(f"{id}: missing supplementary evidence")
    return data


def fact_coverage(groups, hits):
    return all(
        any(
            h["filename"] == o["source"] and normalize(o["quote"]) in normalize(h["content"])
            for h in hits
            for o in group["options"]
        )
        for group in groups
    )
