"""Persistent researchers: sources -> dialogue <-> learning -> ideas -> two checks."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import shutil

from discover import PROJECT, inside, read, write, stage_run, now
from idea_check import CHECKER_PROMPT, POLICY, SCHEMA_VERSION, validate_checks, validate_ideas
from learning_memory import Memory, digest
from learning_support import (QuestionState, QUESTION_PROTOCOL, HypothesisState, HYPOTHESIS_PROTOCOL,
    LEARNING_PROTOCOL, REVIEW_PROTOCOL, LearningServices, material_coverage, review_packet,
    audit_review, validate_uptake, object_hash, default_policy)

LAB = PROJECT / "learning_lab"
CASES = {
    "community": [("microbial_ecologist", "微生物群落生态与功能恢复"),
                  ("nonequilibrium_physicist", "非平衡动力学、状态、记忆和观测")],
    "wine": [("wine_chemist_eval", "葡萄酒化学、感官测量与酿造过程"),
             ("measurement_theorist_eval", "统计物理、测量理论与可辨识性")],
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
    previous_settings = read(state_path).get('settings', {}) if state_path.exists() else {}
    knowledge_policy = (getattr(args, 'knowledge_policy', None) or
                        previous_settings.get('knowledge_policy') or default_policy())
    source_paths = [PROJECT/'src'/name for name in (
        'learning_lab.py', 'learning_support.py', 'learning_memory.py', 'runtime.py', 'discover.py',
        'idea_check.py', 'novelty_contract.py', 'novelty_scope.py', 'import_learning_handoff.py')]
    source_paths += [PROJECT/'historical_inquiry'/name for name in (
        'question_state.py', 'hypothesis_development.py', 'request_routing.py',
        'knowledge_broker.py', 'analysis_executor.py', 'fish_materials.py', 'prepare.py')]
    settings = {"protocol": "learning-inquiry-v2", "researchers": CASES[case],
                "knowledge_policy": knowledge_policy,
                "memory_root": str(memory.root.resolve()),
                "source_hashes": {str(p.relative_to(PROJECT)): digest(p) for p in source_paths},
                "case": case, "brief_sha256": digest(brief), "model": args.model,
                "effort": args.effort, "timeout": args.timeout, "check_timeout": args.check_timeout,
                "plan_sha256": digest(LAB / "PLAN_SOURCE.md")}
    settings = json.loads(json.dumps(settings))
    if state_path.exists():
        state = read(state_path)
        if state["settings"] != settings:
            raise ValueError("Resume settings/code changed; use a new run ID; frozen runs remain unchanged")
    else:
        if run.exists():
            raise ValueError("Use a new run directory or a resumable learning run")
        run.mkdir(parents=True)
        state = {"settings": settings, "created_at": now(), "status": "running", "stages": {}}
        for source_path in source_paths:
            dst = run / "controller_source" / source_path.relative_to(PROJECT)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, dst)
        write(state_path, state)

    if not (run/'manifest.json').exists():
        write(run/'manifest.json', {'stages': {}})
    researchers = [r for r, _ in CASES[case]]
    questions = QuestionState(run/'question_state', researchers)
    hypotheses = HypothesisState(run/'hypothesis_state', researchers)
    services = LearningServices(run, config=knowledge_policy,
                                fetch=getattr(args, 'knowledge_fetch', None))
    generation_results = {}

    def retrieve(rid, query):
        packet = memory.retrieve(rid, query, limit=len(memory.index(rid)['notes']))
        excluded = {key for key, item in packet['available_index'].items()
                    if read(item['path']).get('source_stage') == '07_check_experience'}
        packet['available_index'] = {k: v for k, v in packet['available_index'].items() if k not in excluded}
        packet['retrieved'] = [n for n in packet['retrieved'] if n['note']['key'] not in excluded][:4]
        packet['excluded_terminal_evaluation_notes'] = len(excluded)
        return packet

    def call(sid, role, prompt, inputs, timeout=None):
        researcher = role in researchers
        initial_call = sid in {f'02_initial_{i}' for i in range(len(researchers))}
        context = None
        if researcher:
            context_path = run/'researcher_context'/(sid+'.json')
            if context_path.exists():
                context = read(context_path)
            else:
                independent = sid.startswith('02_initial_')
                context = {'researcher': role,
                           'hypothesis_state': hypotheses.packet(sid, role, independent)}
                if not initial_call:
                    context['question_state'] = questions.packet(sid, role)
                    if independent:
                        context['question_state']['peer_questions'] = []
                        context['question_state']['shared_question'] = None
                write(context_path, context)
            inputs = [*inputs, context_path]
            if 'Also return memory_notes:' not in prompt:
                prompt += '\n' + NOTE_SCHEMA
            prompt = prompt.replace('1-3 reusable notes', '0-3 reusable notes; [] when unchanged')
            prompt += '\n' + HYPOTHESIS_PROTOCOL + '\n' + LEARNING_PROTOCOL
            if not initial_call:
                prompt += '\n' + QUESTION_PROTOCOL
            prompt += "\nUse controller-owned question_state, never invent question_before/question_after."
            prompt += "\nKeep hypotheses tied to specific entities/relations in this situation. A measurement or representation contribution is legitimate; explain its concrete consequences without forcing a natural mechanism."
        steering = sorted(run.glob('OPERATOR_STEERING*.md'))
        all_inputs = [brief, POLICY, LAB/'PLAN_SOURCE.md', *inputs, *steering[-1:]]
        if steering:
            prompt += '\nOperator guidance:\n' + steering[-1].read_text()
        input_hashes = [{'path': str(p), 'sha256': digest(p)} for p in all_inputs]
        prompt = COMMON + prompt
        fingerprint = object_hash({'role': role, 'prompt': prompt, 'inputs': input_hashes})

        def accept(path, result):
            if researcher:
                questions.validate(sid, role, result, context.get('question_state'), initial_call)
                hypotheses.validate(sid, role, result, context['hypothesis_state'])
                if 'learning_request' in result or 'analysis_plan' in result:
                    # Validate the same request envelope used by the service, including legacy terms.
                    from learning_support import service_request
                    service_request(result)
                replies = [read(p) for p in inputs if p.parent == run/'services/replies']
                if replies:
                    supplied = {s['id'] for reply in replies for s in reply['sources']}
                    used = result.get('source_use', [])
                    if not isinstance(used, list) or any(not isinstance(u, dict) for u in used):
                        raise ValueError('source_use must describe supplied material')
                    if {u.get('source_id') for u in used} != supplied or len(used) != len(supplied):
                        raise ValueError('Classify each returned source as direct/method/irrelevant/not_read')
                    if any(u.get('relation') not in {'direct', 'method', 'irrelevant', 'not_read'} or not u.get('reason') for u in used):
                        raise ValueError('Source use needs a scoped relevance reason')
                if sid in {f'05_return_{i}' for i in range(len(researchers))}:
                    validate_uptake(result, read(run/'internal_review/report.json'), role,
                                    run/'internal_review/report.json')
                questions.accept(sid, role, result, path, context.get('question_state'), initial_call)
                hypotheses.accept(sid, role, result, path, context['hypothesis_state'])
                generation_results[sid] = (role, path)
            prior = state['stages'].get(sid, {})
            state['stages'][sid] = {**prior, 'path': str(path), 'sha256': digest(path),
                                    'input_sha256': fingerprint}
            write(state_path, state)
            return path, result

        if sid in state['stages']:
            saved = state['stages'][sid]
            path = Path(saved['path'])
            if digest(path) != saved['sha256'] or saved.get('input_sha256') != fingerprint:
                raise ValueError('Saved stage input/output changed')
            return accept(path, read(path))

        def queue(reason=None):
            workspace = run/'stages'/sid/'native-001/workspace'
            workspace.mkdir(parents=True, exist_ok=True)
            manifest = read(run/'manifest.json')
            old = manifest.get('stages', {}).get(sid, {})
            recovery = ('\nPrior interrupted workspace (inspect and reuse actual sources): ' + old['output_path']) if old.get('output_path') else ''
            request = {'stage': sid, 'role': role, 'model': args.model, 'effort': args.effort,
                'workspace': str(workspace), 'inputs': [str(p) for p in all_inputs],
                'input_hashes': input_hashes, 'input_sha256': fingerprint,
                'prompt': prompt + recovery, 'created_at': now(), 'fallback_reason': reason}
            write(run/'PENDING_NATIVE.json', request)
            state['status'] = 'awaiting_native_role'
            write(state_path, state)
            print(json.dumps({'status': 'awaiting_native_role', 'stage': sid,
                              'request': str(run/'PENDING_NATIVE.json')}), flush=True)
            raise SystemExit(75)

        if args.executor == 'queue':
            queue()
        try:
            path, result = stage_run(run, sid, role, prompt, all_inputs, args.model, args.effort,
                                     timeout or args.timeout)
            if result.get('execution_status') == 'timed_out':
                partial = Path(read(run/'manifest.json')['stages'][sid]['output_path'])
                path, result = stage_run(run, sid+'_recovery', role,
                    prompt + '\nBounded recovery: reuse inspectable partial material in ' + str(partial) +
                    '. Save useful partial understanding and explicit remaining gaps; do not repeat broad searches.',
                    all_inputs, args.model, args.effort, timeout or args.timeout)
                if result.get('execution_status') == 'timed_out':
                    queue('cli_timeout_after_bounded_recovery')
        except RuntimeError:
            # Do not inspect credentials or retry authentication blindly. Preserve failure logs.
            queue('cli_failed_inspect_runtime_manifest')
        return accept(path, result)

    def learn(sid, rid, path, base_inputs):
        learned = []
        for hop in range(2):
            service_id = sid+f'_request_{hop}'
            reply = services.reply(service_id, read(path))
            if reply is None:
                return learned
            call_id = sid+f'_learn_{hop}'
            path, result = call(call_id, rid,
                "Study your actual controller reply. Identify directly relevant sources, transferable methods "
                "and irrelevant results; explain what changes in your assumption and what remains open. "
                "Classify every returned source; not_read is valid for sources not studied. "
                "Return source_use:[{source_id,relation:direct/method/irrelevant/not_read,reason}], learning_change, "
                "and an optional next learning_request. Label hypothetical worked examples. " + NOTE_SCHEMA,
                [*base_inputs, path, reply])
            memory.commit(rid, run.name, call_id, path)
            learned.append(path)
        tail = services.reply(sid+'_continuation_request', read(path))
        if tail:
            learned.append(tail)  # Explicitly returned, awaiting next common discussion.
        return learned

    source, source_result = call("01_materials", "shared_material_curator", """
Prepare an open scientific situation from the brief. Read and archive 2-4 sources, including
at least one original scientific study with concrete observations and one foundation/review.
Choose available sources (abstract-only must be marked). Avoid selecting the final question.
Save MATERIALS.md describing conditions, observations, expectations and their assumptions,
theory's successful range, existing explanations and unresolved ambiguities with source IDs.
Return materials: array of {id,observation,conditions,expectation,expectation_basis,
existing_explanations,unknowns,source_ids}; unknown expectations allowed.
Return sources: array of {id,title,url,access_level,local_path,content_note,
source_kind:original_study/review/textbook/dataset/other,
content_access:abstract/full_text/excerpt/metadata/failed,
domain_relation:direct/method/background,relevance_reason,supporting_quote:exact excerpt}.
Metadata or a secondary account is not reading the original study. The foundation should
be independent domain knowledge, not another copy of dataset documentation.
local_path must name an existing source text/excerpt file (absolute path).
Original papers already contain scientific interpretations: retain them as source claims.
""", [], args.check_timeout)
    if not source_result.get("materials") or not source_result.get("sources"):
        raise ValueError("Materials/source records missing")
    coverage = material_coverage(source_result)
    if coverage['status'] == 'incomplete':
        coverage_path = run/'material_gap.json'
        if not coverage_path.exists():
            write(coverage_path, coverage)
        source, source_result = call('01_materials_recovery', 'shared_material_curator',
            "Complete the specifically missing domain material using the previous downloaded sources. "
            "Read an original study and an independent domain foundation/review. Keep the source schema "
            "and materials schema from the original result; add source_kind, content_access, domain_relation, "
            "relevance_reason and exact supporting_quote. Preserve useful existing sources. "
            "If access remains unavailable, report the concrete gap; do not relabel metadata as original text.",
            [source, coverage_path], args.check_timeout)
        coverage = material_coverage(source_result)
    write(run/'MATERIAL_COVERAGE.json', coverage)
    source_files = []
    for item in source_result["sources"]:
        path = inside(item["local_path"])
        if not path.is_file():
            raise ValueError("Missing downloaded source")
        archive = LAB / "library" / (digest(path) + path.suffix)
        if not archive.exists():
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, archive)
        source_files.append(archive)
    write(run / "source_catalog.json", {"source_result": str(source),
        "sources": [{**item, "archived_path": str(path), "sha256": digest(path)}
                    for item, path in zip(source_result["sources"], source_files)]})
    base = [source, run / "source_catalog.json", run/"MATERIAL_COVERAGE.json", *source_files]
    # Immutable retrieval snapshots allow exact resumption even after memory updates.
    packets = {}
    for rid, domain in CASES[case]:
        memory.identity(rid, domain)
        packet = run / "memory_retrieval" / (rid + ".json")
        packets[rid] = packet

    initial, initial_learning = [], []
    for i, (rid, domain) in enumerate(CASES[case]):
        if not packets[rid].exists():
            query = brief.read_text() + "\n" + source_result["summary"] + "\n" + domain
            write(packets[rid], retrieve(rid, query))
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
        initial_learning.extend(learn(sid, rid, path, [*base, packets[rid]]))

    exchanges = []
    for i, (rid, domain) in enumerate(CASES[case]):
        sid = f"03_exchange_{i}"
        path, result = call(sid, rid, f"""
Continue as {rid}. Read both actual independent initial notes and any earlier peer reply.
Address the peer's specific question. Explain a concept mismatch, a useful connection or a
disagreement. You may redefine the shared object and change the question. Do not just review.
Save EXCHANGE.md. Return shared_object, response_to_peer, disagreement (strings), and learning_request:
{{needed: boolean, gap: string, why_now: string, search_terms: [strings]}}.
The request must arise from this exchange; if no meaningful gap exists, set needed=false.
""", [*base, packets[rid], *initial, *initial_learning, *exchanges])
        if not isinstance(result.get("learning_request", {}).get("needed"), bool):
            raise ValueError("Explicit learning decision missing")
        memory.commit(rid, run.name, sid, path)
        exchanges.append(path)

    learned = list(initial_learning)
    for i, (rid, domain) in enumerate(CASES[case]):
        learned.extend(learn(f'04_targeted_{i}', rid, exchanges[i], [*base, *initial, *exchanges]))

    review_inputs = run/'internal_review/inputs.json'
    if not review_inputs.exists():
        write(review_inputs, review_packet(generation_results))
    review_path, review_result = call('04_internal_review', 'internal_reasoning_reviewer',
                                    REVIEW_PROTOCOL, [review_inputs])
    report = audit_review(review_result, read(review_inputs))
    write(run/'internal_review/report.json', report)

    returned = []
    for i, (rid, domain) in enumerate(CASES[case]):
        sid = f"05_return_{i}"
        current = run / "memory_retrieval" / (rid + "_return.json")
        if not current.exists():
            write(current, retrieve(rid, brief.read_text() + "\n" + source_result["summary"] + "\n" + domain))
        path, result = call(sid, rid, f"""
Return to the shared discussion as {rid}. Read both researchers' targeted learning outputs and
respond to their actual changes. Revise the common object/question where justified. Keep disagreements.
Return changed_because, shared_object (strings),
branches (array of candidate questions/hypotheses/connections, including unfinished alternatives).
Save RETURN.md. Preserve abandoned branches with reasons; do not force consensus or novelty.
Respond to EVERY supplied internal finding with verification_responses:
[{{finding_id,stance:accept/rebut/unresolved,reason}}]. Affected own note_keys require same-key
kind:correction versions describing the correction/dispute and citing the report path.
Keep tentative hypotheses open; an example error does not invalidate the research direction.
""" + NOTE_SCHEMA, [*base, current, *initial, *exchanges, *learned, *returned, run/"internal_review/report.json"])
        memory.commit(rid, run.name, sid, path)
        returned.append(path)
        learned.extend(learn(sid, rid, path, [*base, *returned]))

    # A fresh model call receives only retrieved memory + a small continuation task, not full dialogue.
    rid, domain = CASES[case][1]
    packet = run / "memory_retrieval" / "fresh_continuation.json"
    if not packet.exists():
        write(packet, retrieve(rid, brief.read_text() + "\n" + source_result["summary"]
                                      + "\n" + domain))
    fresh_path, fresh_result = call("08_fresh_continuation", rid, """
This is a fresh continuation session. Read only the supplied retrieved memory packet and brief;
do not read the prior case dialogue or candidates. Choose a saved unresolved question and advance
its formulation by applying a saved relation to a new small illustrative example. Identify exact
note key/version/source_task used, applicability and what must still be learned. Save CONTINUATION.md.
Return memory_use array of {key,source_task,used_for,scope_check}, continuation_question,
worked_example, and remaining_gap. This illustrates retrieval and use, not an advantage benchmark.
""", [packet])
    memory.commit(rid, run.name, '08_fresh_continuation', fresh_path)
    learned.extend(learn('08_fresh_continuation', rid, fresh_path, [packet]))

    history_path = run/'candidate_history.json'
    if not history_path.exists():
        write(history_path, {**questions.history_packet('06_candidates'),
                             **hypotheses.history_packet('06_candidates')})
    synth, synthesis = call("06_candidates", "discussion_recorder", """
Organize the ideas actually emerging from these exchanges, without inventing a replacement agenda.
Keep 1-4 distinct candidates if they emerged; incomplete questions are valid. If none, ideas=[]
and explain the unresolved learning entry point. Save all branches in BRANCHES.md, including
abandoned ones. Return ideas array with id,title,idea,motivation,emergence (specific earlier
stage paths and changes),domains. Save IDEAS.md. Also return question_trajectory array with
stage, researcher, question, cause; quote real changes. Use the authoritative question history,
not self-described question_before. Preserve actual assumptions and conditional consequences,
not just whether-questions. Also return preserved_branches:[{ref:exact current hypothesis ref,
reason:disposition}], accounting for ALL current branches including incomplete/parked ones.
Do not pre-screen for novelty, evidence strength or feasibility.
""", [*base, *initial, *exchanges, *learned, *returned, fresh_path, history_path])
    ideas = synthesis.get("ideas")
    if not isinstance(ideas, list):
        raise ValueError("Candidate list missing")
    if ideas:
        validate_ideas(synthesis)
        if any("evaluation_context" in idea for idea in ideas):
            raise ValueError("Generator cannot declare its own historical/exposure context")
    refs = [c['ref'] for c in read(history_path)['current_hypotheses']]
    preserved = [c.get('ref') for c in synthesis.get('preserved_branches', [])]
    if len(refs) != len(preserved) or any(preserved.count(r) != 1 for r in refs):
        raise ValueError('Recorder omitted or changed hypothesis branch refs')
    idea_path = run / "ideas.json"
    write(idea_path, {"source": str(synth), "ideas": ideas})
    freeze = run/'GENERATION_FREEZE.json'
    if not freeze.exists():
        protected = [idea_path, history_path, run/'source_catalog.json', run/'MATERIAL_COVERAGE.json', *source_files]
        for folder in ('stages', 'memory_retrieval', 'researcher_context', 'question_state',
                       'hypothesis_state', 'internal_review', 'services', 'controller_source'):
            protected.extend(p for p in (run/folder).rglob('*') if p.is_file() and '07_check' not in p.parts)
        write(freeze, {'files': {str(p): digest(p) for p in protected},
                       'memory_files': {str(p): digest(p) for p in memory.root.rglob('*.json')},
                       'external_feedback_used_for_generation': False})
    for p, expected in read(freeze)['files'].items():
        if digest(p) != expected:
            raise ValueError('Frozen generation changed before evaluation')
    memory_before = {str(p): digest(p) for p in memory.root.rglob('*.json')}
    if memory_before != read(freeze)['memory_files']:
        raise ValueError('Research memory changed across the frozen evaluation boundary')
    if ideas:
        if "07_check" not in state["stages"]:
            state["check_schema_version"] = SCHEMA_VERSION
            write(state_path, state)
        require_claims = state.get("check_schema_version") == SCHEMA_VERSION
        check, checked = call("07_check", "idea_check_agent", CHECKER_PROMPT + """
Compare broad core direction, not every detail's exact conjunction. Use established short terms
and both fields' synonyms. Read source content and save search responses/excerpts locally.
Record direction overlap separately from substantive residual claims and temporal/exposure scope.
""", [idea_path], args.check_timeout)
        validate_checks(checked, ideas, require_claims=require_claims)
        write(run / "check_report.json", {
            **({"schema_version": checked["schema_version"]} if "schema_version" in checked else {}),
            "source": str(check), "checks": checked["checks"], "searches": checked["searches"]})
    else:
        write(run / "check_report.json", {"checks": [], "searches": [], "reason": "No candidates; learning entry point preserved"})

    if memory_before != {str(p): digest(p) for p in memory.root.rglob('*.json')}:
        raise ValueError('Final evaluator modified memory')
    for p, expected in read(freeze)['files'].items():
        if digest(p) != expected:
            raise ValueError('Final evaluator modified frozen generation')
    write(run/'EVALUATION_ISOLATION.json', {'memory_unchanged': True,
          'researcher_calls_after_evaluation': 0, 'evaluation_experience_written_to_memory': False})
    state.update(status="complete", finished_at=now())
    write(state_path, state)
    print(json.dumps({"case": case, "status": "complete", "run": str(run)}, ensure_ascii=False), flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case", choices=[*CASES, "both"], default="both")
    p.add_argument("--run-prefix", default="learn_20261104")
    p.add_argument("--model", default="gpt-6-luna")
    p.add_argument("--effort", default="low")
    p.add_argument("--timeout", type=int, default=420)
    p.add_argument("--check-timeout", type=int, default=600)
    p.add_argument("--memory-root", type=Path, help="Existing or copied researcher store; defaults to learning_lab/researchers")
    p.add_argument("--executor", choices=["cli", "queue"], default="cli")
    args = p.parse_args()
    if not args.run_prefix.replace("_", "").isalnum() or min(args.timeout, args.check_timeout) <= 0:
        p.error("safe run prefix and positive timeouts required")
    LAB.mkdir(exist_ok=True)
    with (LAB / ".controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        memory = Memory(inside(args.memory_root) if args.memory_root else LAB / "researchers")
        for case in ('community', 'immune') if args.case == "both" else [args.case]:
            run_case(case, PROJECT / "runs" / (args.run_prefix + "_" + case), args, memory)


if __name__ == "__main__":
    main()
