"""Claim-centred novelty report contract; checks records, not scientific truth."""
from pathlib import Path

SCHEMA_VERSION = "claim-centric-v1"
FACETS = ("problem", "mechanism", "contribution", "assumptions", "validation", "application")
RELATIONS = {"EQUIVALENT", "PRIOR_COVERS_IDEA", "PARTIAL_OVERLAP", "RELATED_ONLY", "DISTINCT", "UNKNOWN"}
COVERS = {"EQUIVALENT", "PRIOR_COVERS_IDEA"}
KINDS = {"method", "theory", "scientific_finding", "question", "combination", "other"}
CONDITIONS = {"idea_implies_prior", "prior_implies_idea", "equivalent", "incomparable", "unknown", "not_applicable"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def string(value, name):
    require(isinstance(value, str) and bool(value.strip()), f"{name} must be a nonempty string")


def records(value, name):
    require(isinstance(value, list) and all(isinstance(x, dict) for x in value), f"{name} must be an object array")
    return value


def keyed(value, key, name):
    result = {}
    for item in records(value, name):
        identifier = item.get(key)
        string(identifier, name + "." + key)
        require(identifier not in result, f"duplicate {name} id")
        result[identifier] = item
    return result


def snapshot(value, project):
    string(value, "snapshot_path")
    path = Path(value)
    if not path.is_absolute():
        path = project / path
    path = path.resolve()
    require(path.is_relative_to(project.resolve()) and path.is_file(), "snapshot must be an existing project-local file")
    return path


def idea_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            if key not in {"id", "source"}:
                yield from idea_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from idea_strings(item)


def validate_novelty(check, idea, searches, project):
    novelty = check.get("novelty")
    require(isinstance(novelty, dict), "claim-centric check needs novelty")
    card = novelty.get("idea_card")
    require(isinstance(card, dict) and set(card) == set(FACETS), "idea_card needs all six facets")
    for facet in FACETS:
        string(card[facet], "idea_card." + facet)
    claims = keyed(novelty.get("claims"), "claim_id", "claims")
    require(1 <= len(claims) <= 5, "extract 1..5 core claims; a question is a valid claim")
    for claim in claims.values():
        string(claim.get("text"), "claim.text")
        require(claim.get("kind") in KINDS, "invalid claim kind")
        quote = claim.get("idea_quote")
        string(quote, "claim.idea_quote")
        require(any(quote in text for text in idea_strings(idea)), "claim must quote the supplied idea verbatim")

    sources = keyed(check["prior_work"]["sources"], "source_id", "sources")
    texts = {}
    for sid, source in sources.items():
        level = source.get("evidence_level")
        require(level in {"full_text", "abstract", "metadata_only", "unavailable"}, "invalid evidence level")
        if level != "unavailable":
            path = snapshot(source.get("snapshot_path"), project)
            texts[sid] = path.read_text(encoding="utf-8")
        else:
            require(source.get("snapshot_path") is None, "unavailable source has no content snapshot")

    evidence = keyed(novelty.get("evidence"), "evidence_id", "evidence")
    for item in evidence.values():
        sid = item.get("source_id")
        require(sid in sources and sid in texts, "evidence needs an accessible source")
        string(item.get("quote"), "evidence.quote")
        string(item.get("locator"), "evidence.locator")
        require(item["quote"] in texts[sid], "evidence quote is absent from the saved source snapshot")

    def relation(row, sid):
        require(isinstance(row, dict), "comparison must be an object")
        tag = row.get("relation")
        require(tag in RELATIONS, "invalid comparison relation")
        string(row.get("reason"), "comparison.reason")
        refs = row.get("evidence_ids")
        require(isinstance(refs, list) and all(isinstance(ref, str) for ref in refs), "evidence_ids must be strings")
        require(len(refs) == len(set(refs)), "duplicate evidence reference")
        require(all(ref in evidence and evidence[ref]["source_id"] == sid for ref in refs), "evidence must belong to the compared source")
        if tag != "UNKNOWN":
            require(bool(refs), "a definite comparison needs source evidence")
            require(sources[sid]["evidence_level"] in {"abstract", "full_text"}, "metadata cannot establish a substantive relation")
        return tag

    comparisons = keyed(novelty.get("comparisons"), "source_id", "comparisons")
    require(set(comparisons) == set(sources), "compare every listed source")
    claim_rows = {cid: [] for cid in claims}
    for sid, comparison in comparisons.items():
        facets = comparison.get("facets")
        require(isinstance(facets, dict) and set(facets) == set(FACETS), "source comparison needs six facets")
        for facet in FACETS:
            relation(facets[facet], sid)
        rows = keyed(comparison.get("claim_relations"), "claim_id", "claim_relations")
        require(set(rows) == set(claims), "every source must address every core claim")
        for cid, row in rows.items():
            tag = relation(row, sid)
            condition = row.get("conditions")
            require(isinstance(condition, dict) and condition.get("relation") in CONDITIONS, "invalid conditions relation")
            string(condition.get("reason"), "conditions.reason")
            if tag in COVERS:
                if claims[cid]["kind"] == "theory":
                    require(condition["relation"] in {"idea_implies_prior", "equivalent"}, "theory coverage needs matching or weaker prior assumptions")
                require(sources[sid]["similarity"] == "very_similar", "covered core claim needs a very similar source")
            claim_rows[cid].append((sid, tag))

    completed_facets = {s["facet"] for s in searches
                        if s["status"] == "completed" and idea["id"] in s["idea_ids"]}
    completed = completed_facets == {"problem", "mechanism", "contribution"}
    coverage = {}
    covering_sources = []
    for cid, rows in claim_rows.items():
        covers = {sid for sid, tag in rows if tag in COVERS}
        covering_sources.append(covers)
        if covers:
            state = "COVERED"
        elif any(tag == "PARTIAL_OVERLAP" for _, tag in rows):
            state = "PARTIAL_OVERLAP"
        elif any(tag == "UNKNOWN" for _, tag in rows) or not completed:
            state = "UNKNOWN"
        else:
            state = "NO_COVERAGE_FOUND"
        require(claims[cid].get("coverage") == state, "claim coverage contradicts its source comparisons/searches")
        coverage[cid] = state

    # Several papers covering separate pieces do not establish an integrated prior.
    common_source = set.intersection(*covering_sources)
    if common_source:
        overall = "COVERED"
    elif any(s in {"COVERED", "PARTIAL_OVERLAP"} for s in coverage.values()):
        overall = "PARTIAL_OVERLAP"
    elif any(s == "UNKNOWN" for s in coverage.values()):
        overall = "UNCLEAR"
    else:
        overall = "NO_COVERAGE_FOUND"
    require(novelty.get("overall_status") == overall, "overall_status contradicts the claim coverage")
    if overall == "COVERED":
        require(check["prior_work"]["verdict"] == "already_done", "covered contribution must flag prior work")
    if check["prior_work"]["verdict"] == "no_close_work_found":
        require(completed, "no-close-work needs completed searches across all three retrieval facets")
        require(not any(s["similarity"] == "very_similar" for s in sources.values()), "close work cannot be reported as absent")
    if check["prior_work"]["verdict"] == "already_done":
        require(any(sources[sid]["similarity"] == "very_similar"
                    and any(comparison["facets"][f]["relation"] != "UNKNOWN"
                            for f in ("problem", "mechanism", "contribution"))
                    for sid, comparison in comparisons.items()),
                "already_done needs substantive evidence for a similar core direction")

    combination = novelty.get("combination_assessment")
    require(isinstance(combination, dict), "combination_assessment is required")
    string(combination.get("reason"), "combination.reason")
    combo_ids = {cid for cid, c in claims.items() if c["kind"] == "combination"}
    require(combination.get("claim_ids") == sorted(combo_ids), "identify the combination claims explicitly")
    require(combination.get("status") == ("assessed_as_claims" if combo_ids else "not_claimed"), "invalid combination assessment")

    differences = records(novelty.get("remaining_difference"), "remaining_difference")
    for difference in differences:
        cid = difference.get("claim_id")
        require(isinstance(cid, str) and cid in claims and coverage[cid] != "COVERED", "remaining difference must reference an unresolved core claim")
        string(difference.get("description"), "remaining_difference.description")
    action = novelty.get("recommended_action")
    require(action in {"INSPECT_PRIOR", "TARGETED_SEARCH", "CONTINUE_EXPLORATION", "REFINE_PROPOSAL"}, "invalid recommended action")
    if overall == "UNCLEAR":
        require(action == "TARGETED_SEARCH", "insufficient evidence should trigger targeted search")
    string(novelty.get("next_step"), "novelty.next_step")
    require(novelty.get("search_exhaustive") is False, "bounded searches must be labelled non-exhaustive")
    search = novelty.get("search_summary")
    require(isinstance(search, dict), "search_summary is required")
    require(search.get("stop_reason") in {"budget_reached", "sufficient_coverage", "access_limited", "planned_searches_complete"}, "invalid search stop reason")
    if search["stop_reason"] == "sufficient_coverage":
        require(overall == "COVERED", "early coverage stop needs an integrated covering source")
    string(search.get("limitations"), "search_summary.limitations")


def validate_report(result, ideas, project):
    require(result.get("schema_version") == SCHEMA_VERSION, "new checks require claim-centric-v1")
    for search in result["searches"]:
        require(search.get("facet") in {"problem", "mechanism", "contribution"}, "each search needs a retrieval facet")
        require(type(search.get("round")) is int and search["round"] in {1, 2}, "search round must be 1 or 2")
        if search["status"] == "completed":
            snapshot(search.get("snapshot_path"), project)
        else:
            string(search.get("failure_reason"), "search.failure_reason")
    by_id = {idea["id"]: idea for idea in ideas}
    for check in result["checks"]:
        validate_novelty(check, by_id[check["idea_id"]], result["searches"], project)
