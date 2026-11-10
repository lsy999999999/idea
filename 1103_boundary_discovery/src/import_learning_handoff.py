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
    state = read(run / "learning_state.json")
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
