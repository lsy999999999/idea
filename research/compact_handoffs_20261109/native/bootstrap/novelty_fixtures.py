"""Synthetic offline reports. These fixtures are not literature evidence."""
import copy
from pathlib import Path
from novelty_contract import FACETS, SCHEMA_VERSION, LEGACY_VERSION


def claim_report(ideas, root, *, known_direction=False, version=SCHEMA_VERSION):
    root.mkdir(parents=True, exist_ok=True)
    search_path = root / "synthetic_search.txt"
    search_path.write_text("Synthetic search fixture; no live retrieval occurred.\n")
    source_path = root / "synthetic_source.txt"
    quote = "This synthetic fixture studies exactly the supplied question."
    source_path.write_text(quote + "\n")
    result = {"schema_version": version, "searches": [], "checks": []}
    for idea in ideas:
        for facet in ("problem", "mechanism", "contribution"):
            result["searches"].append({"query": "synthetic " + facet,
                "url": "https://example.org/search", "status": "completed",
                "idea_ids": [idea["id"]], "facet": facet, "round": 1,
                "snapshot_path": str(search_path)})
        sources, evidence, comparisons = [], [], []
        if known_direction:
            sources = [{"source_id": "P1", "title": "Synthetic fixture",
                "url": "https://example.org/paper", "accessed_on": "2026-11-05",
                "content_note": "Synthetic data for a contract test.", "similarity": "very_similar",
                "evidence_level": "abstract", "snapshot_path": str(source_path)}]
            evidence = [{"evidence_id": "E1", "source_id": "P1", "quote": quote, "locator": "Synthetic abstract"}]
            unknown = {"relation": "UNKNOWN", "reason": "Fixture leaves this unspecified.", "evidence_ids": []}
            definite = {"relation": "EQUIVALENT", "reason": "Synthetic assigned relation.", "evidence_ids": ["E1"]}
            facets = {f: copy.deepcopy(unknown) for f in FACETS}
            facets["contribution"] = copy.deepcopy(definite)
            comparisons = [{"source_id": "P1", "facets": facets,
                "claim_relations": [{"claim_id": "C1", **definite,
                    "conditions": {"relation": "not_applicable", "reason": "A research question, not a theorem."}}]}]
        result["checks"].append({"idea_id": idea["id"], "prior_work": {
            "verdict": "already_done" if known_direction else "no_close_work_found",
            "reason": "Synthetic fixture result.", "sources": sources},
            "math": {"verdict": "no_obvious_error", "reason": "An unresolved question.", "errors": []},
            "novelty": {
                "idea_card": {f: "not specified" for f in FACETS},
                "claims": [{"claim_id": "C1", "text": idea["idea"], "idea_quote": idea["idea"],
                    "kind": "question", "coverage": "COVERED" if known_direction else "NO_COVERAGE_FOUND"}],
                "evidence": evidence, "comparisons": comparisons,
                "overall_status": "COVERED" if known_direction else "NO_COVERAGE_FOUND",
                "combination_assessment": {"status": "not_claimed", "claim_ids": [], "reason": "No combination claim."},
                "remaining_difference": [] if known_direction else [{"claim_id": "C1", "description": "Unconfirmed difference."}],
                "recommended_action": "INSPECT_PRIOR" if known_direction else "CONTINUE_EXPLORATION",
                "next_step": "Review the synthetic fixture.", "search_exhaustive": False,
                "search_summary": {"stop_reason": "planned_searches_complete", "limitations": "Offline synthetic fixture only."}}})
    if version == SCHEMA_VERSION:
        for idea, check in zip(ideas, result["checks"]):
            if check["prior_work"]["verdict"] == "already_done":
                check["prior_work"]["verdict"] = "close_direction_found"
            for source in check["prior_work"]["sources"]:
                source["publication_date"] = None
            scope_report(idea, check, root)
    return result


def scope_report(idea, check, root, *, completed=True):
    """Populate derived fields for a synthetic report; tests assert scenario outcomes separately."""
    from novelty_scope import evaluate_scope
    sources = {s["source_id"]: s for s in check["prior_work"]["sources"]}
    novelty = check["novelty"]
    rows = {c["claim_id"]: [] for c in novelty["claims"]}
    for comparison in novelty["comparisons"]:
        for row in comparison["claim_relations"]:
            rows[row["claim_id"]].append((comparison["source_id"], row["relation"]))
    coverage, overall, assessment = evaluate_scope(idea, sources, rows, completed, Path(__file__).resolve().parents[1])
    for claim in novelty["claims"]:
        claim["coverage"] = coverage[claim["claim_id"]]
    novelty.update(overall_status=overall, assessment=assessment,
                   remaining_difference=[{"claim_id": cid, "description": "Synthetic unresolved claim."}
                                         for cid, status in coverage.items() if status != "COVERED"])
    if overall == "UNCLEAR":
        novelty["recommended_action"] = "TARGETED_SEARCH"
