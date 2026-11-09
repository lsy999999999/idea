"""Temporal and input-relative novelty. Context comes from the controller, not the checker."""
from datetime import date
from copy import deepcopy
from urllib.parse import urlsplit, urlunsplit

from novelty_contract import COVERS, aggregate_coverage, keyed, require, snapshot, string

DEFAULT_CONTEXT = {"mode": "current", "reference_date": None, "reference_reason": "No historical cutoff supplied.",
                   "source_papers": []}


def canonical_url(value):
    string(value, "identity URL")
    parsed = urlsplit(value)
    require(parsed.scheme in {"http", "https"} and bool(parsed.netloc), "identity must be an http(s) URL")
    host = parsed.netloc.lower()
    if host in {"dx.doi.org", "www.doi.org"}:
        host = "doi.org"
    path = parsed.path.rstrip("/")
    if host == "doi.org":
        path = path.lower()
    return urlunsplit(("https", host, path, parsed.query, ""))


def evidence_record(record, project):
    require(isinstance(record, dict), "provenance needs a snapshot and exact quote")
    string(record.get("quote"), "provenance.quote")
    text = snapshot(record.get("snapshot_path"), project).read_text(encoding="utf-8")
    require(record["quote"] in text, "provenance quote absent from snapshot")


def date_interval(record, project, *, task_reference=False):
    """Partial dates use a bounded interval; no invented January 1 dates."""
    if record is None:
        return None
    require(isinstance(record, dict), "publication date must be null or a dated evidence record")
    if record.get("evidence_kind") == "task_configuration":
        require(task_reference, "a task cutoff cannot establish a source publication date")
    else:
        canonical_url(record.get("url"))
    evidence_record(record, project)
    bounds = []
    for field in ("earliest", "latest"):
        value = record.get(field)
        string(value, "date." + field)
        parsed = date.fromisoformat(value)
        require(parsed.isoformat() == value, "dates must be YYYY-MM-DD")
        bounds.append(parsed)
    require(bounds[0] <= bounds[1], "invalid date interval")
    return tuple(bounds)


def validate_context(context, project):
    require(isinstance(context, dict), "evaluation_context must be an object")
    require(context.get("mode") in {"current", "historical"}, "invalid novelty evaluation mode")
    string(context.get("reference_reason"), "reference_reason")
    require("reference_date" in context, "reference_date must be explicit (null if unknown)")
    reference = date_interval(context["reference_date"], project, task_reference=True)
    if context["mode"] == "current":
        require(reference is None, "current mode has no historical cutoff")
    papers = keyed(context.get("source_papers"), "paper_id", "source_papers")
    seen = set()
    for paper in papers.values():
        string(paper.get("title"), "source paper title")
        urls = paper.get("urls")
        require(isinstance(urls, list) and bool(urls), "source paper needs identity URLs")
        identities = [canonical_url(url) for url in urls]
        require(len(set(identities)) == len(identities) and not seen.intersection(identities), "duplicate source-paper identity")
        seen.update(identities)
        exposure = paper.get("idea_exposure")
        require(isinstance(exposure, dict) and exposure.get("status") in {"hidden", "exposed", "unknown"}, "invalid idea exposure")
        string(exposure.get("reason"), "idea_exposure.reason")
        if exposure["status"] != "unknown":
            evidence_record(exposure, project)
    return reference, papers


def evaluate_scope(idea, sources, claim_rows, completed, project):
    context = idea.get("evaluation_context", DEFAULT_CONTEXT)
    reference, papers = validate_context(context, project)
    identities = {canonical_url(url): paper for paper in papers.values() for url in paper["urls"]}
    roles, eligible, uncertain, hidden = [], set(), set(), set()
    for sid, source in sources.items():
        require("publication_date" in source, "v2 sources need publication_date (null if unknown)")
        published = date_interval(source["publication_date"], project)
        if context["mode"] == "current":
            timing = "current"
        elif reference is None or published is None:
            timing = "unknown"
        elif published[1] < reference[0]:
            timing = "before"
        elif published[0] > reference[1]:
            timing = "after"
        else:
            timing = "overlap"
        paper = identities.get(canonical_url(source["url"]))
        if paper:
            exposure = paper["idea_exposure"]["status"]
            role = {"hidden": "hidden_origin", "exposed": "exposed_origin", "unknown": "unknown_origin"}[exposure]
            if exposure == "hidden":
                hidden.add(sid)
            elif exposure == "exposed":
                eligible.add(sid)
            else:
                uncertain.add(sid)
        elif timing in {"current", "before"}:
            role = "eligible_prior"
            eligible.add(sid)
        elif timing == "after":
            role = "later_work"
        else:
            role = "date_uncertain"
            uncertain.add(sid)
        roles.append({"source_id": sid, "paper_id": paper["paper_id"] if paper else None,
                      "timing": timing, "role": role, "eligible": sid in eligible})

    scoped_search_complete = completed and not (context["mode"] == "historical" and reference is None)
    coverage, overall = aggregate_coverage(claim_rows, scoped_search_complete, eligible, uncertain)
    _, all_status = aggregate_coverage(claim_rows, completed)
    rediscovered = sorted(cid for cid, rows in claim_rows.items() if any(sid in hidden and tag in COVERS for sid, tag in rows))
    hidden_joint = set.intersection(*[{sid for sid, tag in rows if sid in hidden and tag in COVERS}
                                     for rows in claim_rows.values()])
    has_unknown = any(state == "UNKNOWN" for state in coverage.values())
    if overall == "COVERED":
        verdict = "CORE_ALREADY_KNOWN"
    elif overall == "UNCLEAR" or (hidden_joint and has_unknown):
        verdict = "UNRESOLVED"
    elif hidden_joint:
        verdict = "INDEPENDENT_REDISCOVERY"
    else:
        verdict = "RETAIN_CANDIDATE"
    assessment = {"context": deepcopy(context), "source_roles": roles,
                  "all_sources_status": all_status, "rediscovered_claim_ids": rediscovered,
                  "task_verdict": verdict, "candidate_retained": overall != "COVERED",
                  "world_novelty": "EXISTING_MATCH" if all_status == "COVERED" else "NOT_ESTABLISHED"}
    return coverage, overall, assessment
