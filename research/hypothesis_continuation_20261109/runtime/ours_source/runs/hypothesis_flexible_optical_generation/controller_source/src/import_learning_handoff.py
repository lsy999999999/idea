"""Admit an explicitly dispatched native research role without claiming a CLI call."""
import argparse
from pathlib import Path

from discover import PROJECT, inside, read, write, now
from learning_memory import digest
from runtime import sha256_tree


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", required=True)
    p.add_argument("--agent", required=True)
    args = p.parse_args()
    run = inside(args.run)
    request = read(run / "PENDING_NATIVE.json")
    workspace = inside(request["workspace"])
    assert workspace.is_relative_to(run), "Workspace must belong to this run"
    path = workspace / "result.json"
    result = read(path)
    assert isinstance(result.get("summary"), str) and result["summary"].strip()
    for k in ["artifacts", "evidence", "claims", "limitations", "next_actions"]:
        assert isinstance(result.get(k), list), k
    assert result["artifacts"]
    for item in result["artifacts"]:
        value = item.get("path") if isinstance(item, dict) else item
        apath = Path(value)
        choices = [apath] if apath.is_absolute() else [workspace / apath, run.parents[1] / apath]
        assert any(p.resolve().is_relative_to(PROJECT) and p.exists() for p in choices), value
    for item in request["input_hashes"]:
        assert digest(item["path"]) == item["sha256"], "Input mutated while role worked"
    # Validate conceptual handoff before marking a native result admitted. Old packets have none.
    from hypothesis_cycle import validate_step
    for item in request["input_hashes"]:
        ipath = Path(item['path'])
        if ipath.parent.name == 'researcher_context':
            context = read(ipath)
            if 'development_cycle' in context:
                validate_step(result, context['development_cycle'])
    state = read(run / "learning_state.json")
    settings=state.get('settings',{})
    owners=[r[0] for r in settings.get('researchers',[])]
    if request['stage']=='08_fresh_continuation':
        from learning_support import validate_memory_use
        validate_memory_use(result,read(run/'memory_retrieval/fresh_continuation.json'))
    if request.get('role') in owners and settings.get('memory_root'):
        from learning_memory import Memory,validate_notes
        index=Memory(settings['memory_root']).index(request['role'])
        committed=index.get('commits',{}).get(run.name+'/'+request['stage'])
        if committed and committed['source_sha256']!=digest(path):raise ValueError('Committed source mutated')
        if not committed:validate_notes(result.get('memory_notes',[]),index['notes'])
    for item in request['input_hashes']:
        ipath=Path(item['path'])
        if ipath.parent.name=='researcher_context' and request.get('role') in owners:
            from learning_support import QuestionState,HypothesisState,service_request,validate_uptake
            context=read(ipath);sid=request['stage'];role=request['role']
            initial=sid in {f'02_initial_{i}' for i in range(len(owners))}
            QuestionState(run/'question_state',owners).validate(sid,role,result,context.get('question_state'),initial)
            HypothesisState(run/'hypothesis_state',owners).validate(sid,role,result,context['hypothesis_state'])
            service_request(result)
            if sid in {f'05_return_{i}' for i in range(len(owners))}:
                validate_uptake(result,read(run/'internal_review/report.json'),role,run/'internal_review/report.json')
    manifest = read(run / "manifest.json")
    sid = request["stage"]
    if sid in state["stages"]:
        assert state["stages"][sid]["sha256"] == digest(path)
        return
    if sid in manifest["stages"]:
        manifest.setdefault("previous_execution_records", []).append({"stage": sid, **manifest["stages"][sid]})
    manifest["stages"][sid] = {"status": "success", "execution_adapter": "collaboration",
        "agent_name": args.agent, "requested_model": request["model"], "reasoning_effort": request["effort"],
        "result_path": str(path), "output_path": str(workspace), "output_sha256": sha256_tree(workspace),
        "elapsed_s": None, "usage": [], "inputs": request["input_hashes"], "accepted_at": now()}
    write(run / "manifest.json", manifest)
    state["stages"][sid] = {"path": str(path), "sha256": digest(path),
                            "adapter": "collaboration", "agent_name": args.agent}
    if 'input_sha256' in request:
        state['stages'][sid]['input_sha256'] = request['input_sha256']
    write(run / "learning_state.json", state)
    archive = run / "native_dispatch" / (sid + ".json")
    write(archive, {**request, "agent_name": args.agent, "result_sha256": digest(path)})
    (run / "PENDING_NATIVE.json").unlink()
    print(sid + " admitted")


if __name__ == "__main__":
    main()
