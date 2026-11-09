"""Review the actual numerical rationale; retain the original checker and all ideas."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import sys

from isolated_cli import invoke
from prepare import HERE, PROJECT, save
from run import COMMON, verify_sources
sys.path.insert(0, str(PROJECT / "src"))
from learning_memory import Memory, digest


def load(path):
    return json.loads(Path(path).read_text())


def main(case=None):
    case = Path(case) if case is not None else HERE / "cases/airfoil_001"
    verify_sources(case)
    run = case / "run"
    review = case / "reviews/evidence_001"
    review.mkdir(parents=True, exist_ok=True)
    spectra = load(case / "allowed/spectra.json")
    computed = []
    for g in spectra:
        f, level = max(g["frequency_and_level"], key=lambda row: row[1])
        c = g["conditions"]
        computed.append({"spectrum_id": g["id"], **c, "sampled_peak_hz": f,
                         "reported_level_at_peak": level,
                         "sampled_peak_fc_over_U": f*c["chord-length"]/c["free-stream-velocity"]})
    save(review / "data_facts.json", {"method": "Group raw rows by all four measured conditions; take maximum reported level at sampled frequencies. Ties select first ordered row. No continuous peak estimate or new experiment.",
                                      "source_sha256": digest(case / "allowed/data.csv"), "facts": computed})
    stages = {p.parent.name: load(p) for p in sorted((run / "stages").glob("*/result.json"))}
    prompt = COMMON + """
You are the final evidence-check agent. Exactly two duties remain: similar existing core
directions in the approved corpus, and concrete obvious mathematical/logical errors.
The previous final checker saw candidates and abstracts; now inspect the actual reasoning
and recorded numerical examples as well. Do not invent new research or rewrite any idea.
Check that comparisons use the SAME coordinate and units and that numbers quoted as evidence
actually justify the inference. Separate any error in a premise/motivation from whether the
question itself remains coherent. Lack of proof or validation is not an error.
Return summary, artifacts, evidence, claims, limitations, next_actions arrays as appropriate,
checks (one per idea: idea_id, prior_work {status: already_done/unclear,reason,sources},
math {status: no_obvious_error/obvious_error,reason}), and rationale_findings
(array: stage, claim, verdict, explanation, candidate_implication). Cite supplied data facts.
Do not use any tool or outside source. The original checks and candidates remain preserved.
INPUTS:
""" + json.dumps({"stages": stages, "recorded_data_facts": load(review / "data_facts.json"),
                    "sources": load(case / "allowed/sources.json")}, ensure_ascii=False)
    result_path = review / "result.json"
    if not result_path.exists():
        result = invoke(prompt, review / "attempt-001", timeout=240)
        if {c["idea_id"] for c in result.get("checks", [])} != {c["id"] for c in load(run / "ideas.json")["ideas"]}:
            raise ValueError("Evidence review has incomplete idea coverage")
        save(result_path, result)
    result = load(result_path)
    # Attach this later review to the current research-experience note, without replacing history.
    experience = copy.deepcopy(load(run / "research_experience.json"))
    note = experience["memory_notes"][0]
    note.update(kind="correction", title="翼型讨论：完整推理复核后的研究经历",
                understanding=note["understanding"] + "\n后续完整推理复核：" + json.dumps(result, ensure_ascii=False),
                revision_reason="最终复核补看了数值例子与原推理；保留原候选和旧检查，补记新的错误或范围判断。",
                sources=[str(run / "check_report.json"), str(result_path)],
                tags=["flow", "spectrum", "state", "scaling", "研究经历", "correction", "纠正"])
    reviewed = review / "research_experience_reviewed.json"
    if not reviewed.exists():
        save(reviewed, experience)
    memory = Memory(case / "researchers")
    for rid in ("aeroacoustician", "nonequilibrium_physicist"):
        memory.commit(rid, case.name, "evidence_review", reviewed)
    # The false interpretation was also stored as concept knowledge. Correct that current
    # version explicitly; attaching a warning only to the experience note would leave it live.
    if any(c["math"]["status"] == "obvious_error" for c in result["checks"]):
        keys = {"aeroacoustician": "dimensional_similarity_for_spectra",
                "nonequilibrium_physicist": "dimensional_similarity_as_testable_reframing"}
        for rid, key in keys.items():
            source = review / ("concept_correction_" + rid + ".json")
            if not source.exists():
                previous = load(memory.index(rid)["notes"][key]["path"])
                note = {k: previous[k] for k in ("key", "title", "kind", "mastery", "understanding",
                        "conditions", "example", "open_questions", "tags", "sources")}
                note.update(title="谱峰比较：撤回先前的坐标混淆", kind="correction", mastery="read",
                    understanding="必须在同一坐标比较谱峰。谱50与88的Hz峰频为3150与1600，但fc/U为4.0409与4.1051，约差1.6%；原记录用Hz频率比1.97反驳fc/U下峰位接近，推论错误。该两点也不能证明完整谱形或所有工况均能对齐。",
                    example="3150×0.0508/39.6=4.0409；1600×0.1016/39.6=4.1051。数据为离散采样峰。",
                    conditions="由控制器依据最终数值复核记入；未观察研究者在纠正后重新解释或使用。只纠正这一个算例的推论。",
                    sources=[str(result_path), str(review / "data_facts.json")],
                    revision_reason="最终检查发现此前混用Hz与fc/U坐标；保留旧版本，撤回该例作为缩放失败反例的解释。",
                    correction_origin="controller_adopted_final_check")
                save(source, {"memory_notes": [note]})
            memory.commit(rid, case.name, "evidence_concept_correction", source)
    print(json.dumps({"review": str(result_path), "checks": result.get("checks"),
                      "rationale_findings": result.get("rationale_findings")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
