"""Artifact and question-attribution audit; no model call or scientific rewriting."""
import json
from pathlib import Path
import shutil

from prepare import HERE, save
from run import RESEARCHERS, audit
from learning_memory import digest


def load(path):
    return json.loads(Path(path).read_text())


def main():
    case = HERE / "cases/airfoil_001"
    run = case / "run"
    audit(case)
    ledger = []
    for i, (rid, _) in enumerate(RESEARCHERS):
        before = None
        for prefix in ("01_initial", "02_exchange", "04_return"):
            sid = f"{prefix}_{i}"
            path = run / "stages" / sid / "result.json"
            r = load(path)
            after = r.get("initial_question", r.get("question_after"))
            ledger.append({"researcher": rid, "stage": sid, "source_sha256": digest(path),
                           "canonical_previous_question": before,
                           "self_reported_before": r.get("question_before"), "question_after": after,
                           "exact_before_text_matches": None if before is None else r.get("question_before") == before,
                           "note": "Text mismatch alone is not a semantic error. Source quotations are preserved."})
            before = after
    a = load(run / "stages/02_exchange_0/result.json")
    b = load(run / "stages/02_exchange_1/result.json")
    attribution = {"personal_question_versions": ledger,
                   "second_exchange_repeats_peer_question_before_exactly": a["question_before"] == b["question_before"],
                   "controller_semantic_warning": "The second role's own initial question concerns stable spectral features and repeatability. Its reported prior question instead focuses on thickness ratio, closely following the peer. Exact textual equality and this semantic observation are separate; neither proves a new shared question."}
    save(run / "question_attribution_audit.json", attribution)
    audits = list(run.glob("stages/*/attempt-*/execution_audit.json"))
    audits += list((case / "reviews").glob("*/attempt-*/execution_audit.json"))
    records = [load(p) for p in audits]
    successful = [r for r in records if r["returncode"] == 0 and not r["tool_events"]]
    source_snapshot = case / "controller_only/final_controller_snapshot"
    source_snapshot.mkdir(exist_ok=True)
    hashes = {}
    for p in HERE.glob("*.py"):
        shutil.copy2(p, source_snapshot / p.name)
        hashes[p.name] = digest(p)
    save(source_snapshot / "HASHES.json", hashes)
    notes = list((case / "researchers").glob("*/notes/*/v*.json"))
    current = sum(len(load(p)["notes"]) for p in (case / "researchers").glob("*/index.json"))
    final = {"status": "complete", "requested_model": "gpt-6-luna", "reasoning_effort": "low",
             "initial_pilot_stages": len(load(run / "state.json")["stages"]),
             "additional_full_evidence_check": 1, "completed_cli_responses_including_format_repair": len(successful),
             "candidate_count": len(load(run / "ideas.json")["ideas"]),
             "dialogue_triggered_learning_calls": len(list(run.glob("stages/03_learn_*/result.json"))),
             "shared_object_versions": len(list((run / "shared_objects").glob("v*.json"))),
             "current_branch_memories": current, "branch_memory_versions": len(notes),
             "main_researcher_store_modified": False, "previous_task_notes_supplied": 0,
             "fresh_session_continuation_executed": True,
             "new_cross_task_reuse_demonstrated_in_this_pilot": False,
             "protected_original_files_unchanged": load(run / "AUDIT.json")["status"] == "pass",
             "accepted_external_tool_events": sum(r["tool_events"] for r in records),
             "novelty": "unclear_in_small_pre_cutoff_corpus",
             "candidate_rationale_math": "obvious_error_confirmed; question_itself_retained",
             "correction_origin": "controller adopted final evidence-check result; no post-correction researcher uptake call",
             "checks": load(case / "reviews/evidence_001/result.json")["checks"],
             "software_tests": {"new_material_and_syntax_guard": 7, "unchanged_learning_tests": 11},
             "pretraining_exclusion_claimed": False}
    save(HERE / "FINAL_STATUS.json", final)
    print(json.dumps(final, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
