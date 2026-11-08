"""Separate disciplinary inputs -> research proposals -> two-part final check.

No experiment, solution, implementation, or quick-feasibility gate is included.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from discover import PROJECT, inside, now, read, stage_run, write
from idea_check import POLICY, GENERATOR_PROMPT, CHECKER_PROMPT, nonempty, validate_ideas, validate_checks, web_url


def validate_card(result, domain):
    card = result.get("domain_card")
    if not isinstance(card, dict) or card.get("domain") != domain:
        raise ValueError("Domain card must identify its assigned domain")
    for field in ("structures", "open_tensions"):
        if not isinstance(card.get(field), list) or not card[field]:
            raise ValueError(f"Domain card needs {field}")
    for structure in card["structures"]:
        for key in ("name", "relation"):
            nonempty(structure.get(key), key)
        assumptions = structure.get("assumptions")
        if isinstance(assumptions, list) and assumptions:
            for assumption in assumptions:
                nonempty(assumption, "assumption")
        else:
            nonempty(assumptions, "assumptions")
        sources = structure.get("sources")
        if not isinstance(sources, list) or not sources:
            raise ValueError("A borrowed structure needs an actual source")
        for source in sources:
            for key in ("title", "content_note", "accessed_on"):
                nonempty(source.get(key), key)
            web_url(source.get("url"))
    for tension in card["open_tensions"]:
        nonempty(tension, "open_tension")
    return card


def validate_bridges(result, count, domains):
    ideas = validate_ideas(result, count)
    for idea in ideas:
        fields = idea.get("domains")
        if (not isinstance(fields, list) or len(set(fields)) < 2
                or any(field not in domains for field in fields)):
            raise ValueError("Each proposal needs at least two supplied disciplines")
        for key in ("research_question", "conceptual_move", "why_this_crossing_matters"):
            nonempty(idea.get(key), key)
        mapping = idea.get("concept_mapping")
        if not isinstance(mapping, list) or len(mapping) < 2:
            raise ValueError("Describe at least two concrete correspondences")
        for item in mapping:
            for key in ("source_concept", "target_counterpart", "transfer", "where_analogy_may_break"):
                nonempty(item.get(key), key)
    return ideas


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--brief", required=True)
    p.add_argument("--domains", required=True, help="JSON list of disciplinary input names")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--count", type=int, default=3)
    p.add_argument("--model", default="gpt-6-luna")
    p.add_argument("--effort", default="high")
    p.add_argument("--timeout", type=int, default=600)
    p.add_argument("--check-timeout", type=int, default=900)
    a = p.parse_args()
    if not 1 <= a.count <= 6:
        p.error("count must be 1..6")
    brief, domain_file, run = inside(a.brief), inside(a.domains), inside(a.run_dir)
    domains = read(domain_file)
    if (not isinstance(domains, list) or not 2 <= len(domains) <= 6
            or any(not isinstance(x, str) or not x.strip() for x in domains)
            or len(set(domains)) != len(domains)):
        p.error("domains must contain 2..6 distinct names")
    if run == PROJECT or run in brief.parents or run in domain_file.parents:
        p.error("Use a separate run directory")
    settings = {"brief": str(brief), "brief_sha256": hashlib.sha256(brief.read_bytes()).hexdigest(),
        "domains": domains, "count": a.count, "model": a.model, "effort": a.effort,
        "timeout": a.timeout, "check_timeout": a.check_timeout}
    state_file = run / "idea_state.json"
    if state_file.exists():
        state = read(state_file)
        if state["settings"] != settings:
            raise ValueError("Resume settings changed")
        if state["status"] == "complete":
            print(json.dumps({"status": "complete", "report": state["check_report"]})); return
    else:
        if run.exists():
            raise ValueError("Existing directory is not a resumable cross-domain run")
        run.mkdir(parents=True)
        state = {"created_at": now(), "settings": settings, "status": "running",
                 "domain_results": [], "ideas_path": None, "check_report": None}
        snap = run / "controller_source"
        snap.mkdir()
        for name in ("cross_domain_ideas.py", "idea_check.py", "runtime.py", "discover.py"):
            shutil.copy2(PROJECT / "src" / name, snap / name)
        shutil.copy2(POLICY, snap / POLICY.name)
        write(state_file, state)

    def call(stage, role, prompt, inputs, timeout):
        saved = state.get("stage_results", {}).get(stage)
        if saved:
            path = Path(saved["path"])
            if hashlib.sha256(path.read_bytes()).hexdigest() != saved["sha256"]:
                raise ValueError("Saved stage result changed")
            return path, read(path)
        for n in range(2):
            sid = stage if n == 0 else stage + "_retry1"
            try:
                path, result = stage_run(run, sid, role, prompt, [brief, POLICY, *inputs],
                                         a.model, a.effort, timeout)
            except RuntimeError:
                manifest = run / "manifest.json"
                record = read(manifest).get("stages", {}).get(sid, {}) if manifest.exists() else {}
                if n == 0 and record.get("status") == "failed":
                    continue
                raise
            if result.get("execution_status") != "timed_out":
                state.setdefault("stage_results", {})[stage] = {"path": str(path),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                write(state_file, state)
                return path, result
        raise RuntimeError(f"{stage} did not return a result after two bounded attempts")

    for index, domain in enumerate(domains):
        if len(state["domain_results"]) > index:
            continue
        prompt = f"""You provide a disciplinary knowledge input for IDEA GENERATION, not an experiment.
Your assigned domain is exactly: {domain}
Do not read other domain cards, earlier research runs, or their candidates. Work from the brief
and sources in your own field. Retrieve 2-3 useful primary/review sources and extract 2-3
portable mechanisms, organizing principles, or formal structures, plus 2-3 unresolved tensions.
Prefer structures that change how a question is expressed over generic buzzwords or tools.
Do not pre-filter by data availability, implementation difficulty, a quick experiment, or
whether you can solve the question. Do not claim the imported structures themselves are novel.
You are not proposing the final cross-field ideas and must not run scientific experiments.
Output domain_card with domain (the exact assigned string), structures (array of objects with
name and relation as strings, assumptions as a string or string array,
sources:[{{title,url,accessed_on,content_note}}]),
and open_tensions (array of strings). Sources must be actually read; save downloaded text or
retrieval notes. If access fails, use another accessible source rather than fabricate citations.
Also provide the runtime's six standard fields and a short readable card.
"""
        path, result = call(f"domain_{index:02d}", "disciplinary_input", prompt, [], a.timeout)
        validate_card(result, domain)
        state["domain_results"].append(str(path))
        write(state_file, state)

    if not state["ideas_path"]:
        prompt = GENERATOR_PROMPT.format(count=a.count) + f"""
This run specifically requires substantive CROSS-DISCIPLINARY research ideas. Read all supplied
domain cards. Available discipline names: {json.dumps(domains)}.
Generate {a.count} distinct proposals spanning different disciplinary combinations, rather than
three variations of one method. A crossing must alter the question, representation, explanatory
mechanism, or organizing principle. Merely applying an AI model to a new dataset or relabeling a
known optimization is a weak starting point. You may go beyond the exact ideas in the cards.
For every idea add domains (at least two exact names from the list), research_question,
conceptual_move, why_this_crossing_matters, and concept_mapping (at least two objects containing
source_concept, target_counterpart, transfer, where_analogy_may_break as strings).
Write the core proposal concretely enough to recognize similar prior directions. A clear
conceptual proposal is enough; do not invent a decorative equation or demand a complete theory.
Keep ambitious ideas even when a solution is unknown. No experimental plan, accessible-data
requirement, or proof is needed. Novelty and broad mathematical coherence will be checked ONLY
after this complete batch is saved. Save every candidate; do not screen or reject them here.
"""
        path, result = call("synthesize", "cross_disciplinary_idea_builder", prompt,
                            list(map(Path, state["domain_results"])), a.timeout)
        ideas = validate_bridges(result, a.count, domains)
        file = run / "ideas.json"
        write(file, {"source": str(path), "domain_sources": state["domain_results"], "ideas": ideas})
        state["ideas_path"] = str(file)
        write(state_file, state)

    ideas = validate_ideas(read(state["ideas_path"]))
    path, result = call("check", "idea_check_agent", CHECKER_PROMPT + """
Cross-domain vocabulary is not proof of novelty. Compare the underlying research direction
using synonyms from BOTH disciplines. If a very similar direction already exists, say already_done;
minor differences or a new application label are not reasons to rescue it. A related principle
in one parent field alone is not the same as an existing combined research direction. Assess
the proposal as written, not a weaker caricature. Keep the two requested judgments independent.
Do not add practical readiness, tractability, experimental validation, or interdisciplinary
purity as a third acceptance test. Difficult or unsolved is not mathematically incoherent.
""", [Path(state["ideas_path"])], a.check_timeout)
    checks = validate_checks(result, ideas)
    output = run / "check_report.json"
    write(output, {"ideas_path": state["ideas_path"], "check_result_path": str(path),
                   "checks": checks, "searches": result["searches"]})
    state.update(status="complete", finished_at=now(), check_report=str(output))
    write(state_file, state)
    print(json.dumps({"status": "complete", "ideas": state["ideas_path"], "checks": str(output)}))


if __name__ == "__main__":
    main()
