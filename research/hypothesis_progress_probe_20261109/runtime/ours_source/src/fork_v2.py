"""Start a traceable continuation at an existing V2 evidence snapshot."""
from __future__ import annotations
import argparse
import hashlib
from pathlib import Path
import shutil
from discover import PROJECT, inside, now, read, write


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--from-run", required=True)
    p.add_argument("--to-run", required=True)
    p.add_argument("--after-experiments", type=int, required=True)
    p.add_argument("--max-new-experiments", type=int, default=1)
    p.add_argument("--anchor-file", required=True)
    a = p.parse_args()
    original, target, anchor = inside(a.from_run), inside(a.to_run), inside(a.anchor_file)
    old = read(original / "v2_state.json")
    k = a.after_experiments
    if not 0 <= k <= len(old["rounds"]) or a.max_new_experiments < 1:
        raise ValueError("Invalid continuation boundary or budget")
    if k + a.max_new_experiments > 10:
        raise ValueError("Continuation exceeds supported experiment budget")
    ledger_source = original / f"snapshots/ledger_{k:02d}.json"
    ledger = read(ledger_source)
    expected = {read(x["plan_path"])["id"] for x in old["rounds"][:k]}
    if set(ledger["experiments"]) != expected:
        raise ValueError("Snapshot does not match requested experiment boundary")
    if target.exists():
        raise ValueError("Continuation destination already exists")
    target.mkdir(parents=True)
    settings = dict(old["settings"])
    settings.update(max_experiments=k + a.max_new_experiments, anchor_file=str(anchor),
                    anchor_sha256=hashlib.sha256(anchor.read_bytes()).hexdigest())
    state = {"created_at": now(), "settings": settings, "status": "running", "ledger": ledger,
        "seeds": old["seeds"], "bridge": old["bridge"], "rounds": old["rounds"][:k], "review": None,
        "fork_provenance": {"source_run": str(original), "ledger_snapshot": str(ledger_source),
            "ledger_sha256": hashlib.sha256(ledger_source.read_bytes()).hexdigest(),
            "inherited_experiments": k, "max_new_experiments": a.max_new_experiments,
            "scope": "Continuation with updated selection constraints; not an independent or matched-budget method comparison."}}
    write(target / "v2_state.json", state)
    snap = target / "controller_source"
    snap.mkdir()
    for name in ("discover_v2.py", "hypothesis_ledger.py", "selection_guard.py", "discover.py", "runtime.py", "fork_v2.py"):
        shutil.copy2(PROJECT / "src" / name, snap / name)
    shutil.copy2(PROJECT / "docs/V2_CONTRACT.md", snap / "V2_CONTRACT.md")
    shutil.copy2(anchor, snap / "anchor.txt")
    print(f"Created continuation {target}; inherited {k} experiments; new budget {a.max_new_experiments}.")


if __name__ == "__main__":
    main()
