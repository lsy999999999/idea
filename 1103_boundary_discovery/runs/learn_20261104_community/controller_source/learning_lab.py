"""Persistent researchers: sources -> dialogue <-> learning -> ideas -> two checks."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import shutil

from discover import PROJECT, inside, read, write, stage_run, now
from idea_check import CHECKER_PROMPT, POLICY, validate_checks, validate_ideas
from learning_memory import Memory, digest

LAB = PROJECT / "learning_lab"
CASES = {
    "community": [("microbial_ecologist", "微生物群落生态与功能恢复"),
                  ("nonequilibrium_physicist", "非平衡动力学、状态、记忆和观测")],
    "immune": [("immunologist", "免疫记忆、细胞状态和群体响应"),
               ("nonequilibrium_physicist", "非平衡动力学、状态、记忆和观测")],
}
COMMON = """
Execute agent_learn.md's learning and co-questioning plan. Chinese readable artifacts.
Do not read earlier project runs/candidates. Only use listed inputs, their cited source files,
the current case's exchanges, supplied memory, and public sources. A previous task is accessible
only through the supplied memory packet and its provenance. Do not scan old run directories.
Read the actual common sources behind summaries. Treat published findings as published knowledge.
Do not present them as discoveries. Preserve disagreements and all idea branches.
Use public sources via urllib/curl (Crossref, Europe PMC, PMC, arXiv, publishers as accessible).
Save retrieved text and exact URLs; distinguish full text, abstract and failed access.
No solving, scientific validation experiment, proof or novelty gate is required for ideas.
Small worked calculations are allowed to learn a concept, clearly labelled learning examples.
Save result.json with the six runtime fields plus the requested fields. Use summary as a STRING.
Do not spend your entire budget retrieving; save useful partial understanding if needed.
"""
NOTE_SCHEMA = """
Also return memory_notes: 1-3 reusable notes. Each object has:
key (stable lower_case ASCII concept key; reuse an existing key when correcting it), title,
kind (source_knowledge/interpretation/hypothesis/correction),
mastery (read/explained/used; a claimed use must identify an actual worked example),
understanding, conditions, example, open_questions (all nonempty strings),
tags (array, include English and Chinese terms), sources (array of actual URLs or source paths),
revision_reason (required when the key already exists).
Separate published knowledge, your inference and untested hypotheses. 'Unknown' is a valid
open_questions string, never invent competence. Describe corrections explicitly.
Also return memory_use: array of {key,source_task,used_for,scope_check} for notes actually used;
return [] if none. State what you still cannot explain/use.
"""


def run_case(case, run, args, memory):
    brief = LAB / "scenarios" / (case + ".md")
    state_path = run / "learning_state.json"
    settings = {"case": case, "brief_sha256": digest(brief), "model": args.model,
                "effort": args.effort, "timeout": args.timeout, "check_timeout": args.check_timeout,
                "plan_sha256": digest(LAB / "PLAN_SOURCE.md")}
    if state_path.exists():
        state = read(state_path)
        if state["settings"] != settings:
            raise ValueError("Resume settings changed")
    else:
        if run.exists():
            raise ValueError("Use a new run directory or a resumable learning run")
        run.mkdir(parents=True)
        state = {"settings": settings, "created_at": now(), "status": "running", "stages": {}}
        for name in ("learning_lab.py", "learning_memory.py", "runtime.py", "discover.py", "idea_check.py"):
            dst = run / "controller_source" / name
            dst.parent.mkdir(exist_ok=True)
            shutil.copy2(PROJECT / "src" / name, dst)
        write(state_path, state)

    def call(sid, role, prompt, inputs, timeout=None):
        if sid in state["stages"]:
            saved = state["stages"][sid]
            path = Path(saved["path"])
            if digest(path) != saved["sha256"]:
                raise ValueError("Saved stage changed")
            return path, read(path)
        path, result = stage_run(run, sid, role, COMMON + prompt,
            [brief, POLICY, LAB / "PLAN_SOURCE.md", *inputs], args.model, args.effort,
            timeout or args.timeout)
        if result.get("execution_status") == "timed_out":
            raise RuntimeError(f"Stage {sid} timed out; preserved partial output requires narrower recovery")
        state["stages"][sid] = {"path": str(path), "sha256": digest(path)}
        write(state_path, state)
        return path, result

    source, source_result = call("01_materials", "shared_material_curator", """
Prepare an open scientific situation from the brief. Read and archive 2-4 sources, including
at least one original scientific study with concrete observations and one foundation/review.
Choose available sources (abstract-only must be marked). Avoid selecting the final question.
Save MATERIALS.md describing conditions, observations, expectations and their assumptions,
theory's successful range, existing explanations and unresolved ambiguities with source IDs.
Return materials: array of {id,observation,conditions,expectation,expectation_basis,
existing_explanations,unknowns,source_ids}; unknown expectations allowed.
Return sources: array of {id,title,url,access_level,local_path,content_note}.
local_path must name an existing source text/excerpt file (absolute path).
Original papers already contain scientific interpretations: retain them as source claims.
""", [], args.check_timeout)
    if not source_result.get("materials") or not source_result.get("sources"):
        raise ValueError("Materials/source records missing")
    source_files = []
    for item in source_result["sources"]:
        path = inside(item["local_path"])
        if not path.is_file():
            raise ValueError("Missing downloaded source")
        archive = LAB / "library" / (digest(path) + path.suffix)
        if not archive.exists():
            shutil.copy2(path, archive)
        source_files.append(archive)
    write(run / "source_catalog.json", {"source_result": str(source),
        "sources": [{**item, "archived_path": str(path), "sha256": digest(path)}
                    for item, path in zip(source_result["sources"], source_files)]})
    base = [source, run / "source_catalog.json", *source_files]
    # Immutable retrieval snapshots allow exact resumption even after memory updates.
    packets = {}
    for rid, domain in CASES[case]:
        memory.identity(rid, domain)
        packet = run / "memory_retrieval" / (rid + ".json")
        if not packet.exists():
            query = brief.read_text() + "\n" + source_result["summary"] + " state memory recovery history response 记忆 恢复 状态 响应"
            write(packet, memory.retrieve(rid, query))
        packets[rid] = packet

    initial = []
    for i, (rid, domain) in enumerate(CASES[case]):
        sid = f"02_initial_{i}"
        path, result = call(sid, rid, f"""
You are stable researcher {rid}, domain {domain}. First inspect your supplied memory index
and retrieved current notes. Build YOUR independent initial understanding of the common material.
Do not read your peer's initial output yet. Learn necessary prerequisites from 1-2 actual sources
or existing notes; explain one concept with a worked example/derivation to check understanding.
Keep initial_question, interpretation, uncertainties and a concrete question_to_peer as strings
in result.json. Avoid forcing a final proposal. Return a Chinese NOTE.md.
""" + NOTE_SCHEMA, [*base, packets[rid]])
        memory.commit(rid, run.name, sid, path)
        initial.append(path)

    exchanges = []
    for i, (rid, domain) in enumerate(CASES[case]):
        sid = f"03_exchange_{i}"
        path, result = call(sid, rid, f"""
Continue as {rid}. Read both actual independent initial notes and any earlier peer reply.
Address the peer's specific question. Explain a concept mismatch, a useful connection or a
disagreement. You may redefine the shared object and change the question. Do not just review.
Save EXCHANGE.md. Return shared_object (string), question_before, question_after,
response_to_peer, disagreement (strings), and learning_request:
{{needed: boolean, gap: string, why_now: string, search_terms: [strings]}}.
The request must arise from this exchange; if no meaningful gap exists, set needed=false.
""", [*base, packets[rid], *initial, *exchanges])
        if not isinstance(result.get("learning_request", {}).get("needed"), bool):
            raise ValueError("Explicit learning decision missing")
        exchanges.append(path)

    learned = []
    for i, (rid, domain) in enumerate(CASES[case]):
        if not read(exchanges[i])["learning_request"]["needed"]:
            continue
        sid = f"04_learn_{i}"
        current = run / "memory_retrieval" / (rid + "_after_dialogue.json")
        if not current.exists():
            write(current, memory.retrieve(rid, json.dumps(read(exchanges[i])["learning_request"], ensure_ascii=False)))
        path, result = call(sid, rid, f"""
Continue as {rid}. Fulfil YOUR learning_request in the exchange, informed by your peer's reply.
Read 1-3 targeted primary/review/textbook sources; use a concrete worked example, derivation
or small calculation to test what you understand. This is learning, not validation of a new idea.
Preserve fetched source text. Save LEARNING.md explaining gap -> learned relation -> what changes
in your original understanding. State remaining gaps honestly. Return learning_change as a string.
""" + NOTE_SCHEMA, [*base, current, *initial, *exchanges])
        memory.commit(rid, run.name, sid, path)
        learned.append(path)

    returned = []
    for i, (rid, domain) in enumerate(CASES[case]):
        sid = f"05_return_{i}"
        current = run / "memory_retrieval" / (rid + "_return.json")
        if not current.exists():
            write(current, memory.retrieve(rid, source_result["summary"] + " memory state response 记忆 状态 响应"))
        path, result = call(sid, rid, f"""
Return to the shared discussion as {rid}. Read both researchers' targeted learning outputs and
respond to their actual changes. Revise the common object/question where justified. Keep disagreements.
Return question_before, question_after, changed_because, shared_object (strings),
branches (array of candidate questions/hypotheses/connections, including unfinished alternatives).
Save RETURN.md. Preserve abandoned branches with reasons; do not force consensus or novelty.
""" + NOTE_SCHEMA, [*base, current, *initial, *exchanges, *learned, *returned])
        memory.commit(rid, run.name, sid, path)
        returned.append(path)

    synth, synthesis = call("06_candidates", "discussion_recorder", """
Organize the ideas actually emerging from these exchanges, without inventing a replacement agenda.
Keep 1-4 distinct candidates if they emerged; incomplete questions are valid. If none, ideas=[]
and explain the unresolved learning entry point. Save all branches in BRANCHES.md, including
abandoned ones. Return ideas array with id,title,idea,motivation,emergence (specific earlier
stage paths and changes),domains. Save IDEAS.md. Also return question_trajectory array with
stage, researcher, question, cause; quote real changes. Do not pre-screen for novelty or feasibility.
""", [*base, *initial, *exchanges, *learned, *returned])
    ideas = synthesis.get("ideas")
    if not isinstance(ideas, list):
        raise ValueError("Candidate list missing")
    if ideas:
        validate_ideas(synthesis)
    idea_path = run / "ideas.json"
    write(idea_path, {"source": str(synth), "ideas": ideas})
    if ideas:
        check, checked = call("07_check", "idea_check_agent", CHECKER_PROMPT + """
Compare broad core direction, not every detail's exact conjunction. Use established short terms
and both fields' synonyms. Read source content and save search responses/excerpts locally.
Do not rescue an existing direction merely because its new name or biological context differs.
""", [idea_path], args.check_timeout)
        validate_checks(checked, ideas)
        write(run / "check_report.json", {"source": str(check), "checks": checked["checks"], "searches": checked["searches"]})
    else:
        write(run / "check_report.json", {"checks": [], "searches": [], "reason": "No candidates; learning entry point preserved"})

    # A fresh model call receives only retrieved memory + a small continuation task, not full dialogue.
    rid, domain = CASES[case][1]
    packet = run / "memory_retrieval" / "fresh_continuation.json"
    if not packet.exists():
        write(packet, memory.retrieve(rid, "state memory history recovery observation 记忆 恢复 状态 观测 响应"))
    call("08_fresh_continuation", rid, """
This is a fresh continuation session. Read only the supplied retrieved memory packet and brief;
do not read the prior case dialogue or candidates. Choose a saved unresolved question and advance
its formulation by applying a saved relation to a new small illustrative example. Identify exact
note key/version/source_task used, applicability and what must still be learned. Save CONTINUATION.md.
Return memory_use array of {key,source_task,used_for,scope_check}, continuation_question,
worked_example, and remaining_gap. This illustrates retrieval and use, not an advantage benchmark.
""", [packet])
    state.update(status="complete", finished_at=now())
    write(state_path, state)
    print(json.dumps({"case": case, "status": "complete", "run": str(run)}, ensure_ascii=False), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", choices=[*CASES, "both"], default="both")
    p.add_argument("--run-prefix", default="learn_20261104")
    p.add_argument("--model", default="gpt-6-luna")
    p.add_argument("--effort", default="medium")
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--check-timeout", type=int, default=600)
    args = p.parse_args()
    if not args.run_prefix.replace("_", "").isalnum() or min(args.timeout, args.check_timeout) <= 0:
        p.error("safe run prefix and positive timeouts required")
    LAB.mkdir(exist_ok=True)
    with (LAB / ".controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        memory = Memory(LAB / "researchers")
        for case in CASES if args.case == "both" else [args.case]:
            run_case(case, PROJECT / "runs" / (args.run_prefix + "_" + case), args, memory)


if __name__ == "__main__":
    main()
