"""Compare actual replay outputs with frozen historical checks, without model calls."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from discover import read, write
from idea_check import validate_checks


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    plan = read(ROOT / "PLAN.json")
    rows, coverage_counts = [], Counter()
    for case in plan["cases"]:
        run = ROOT / "cases" / case["case"]
        idea = read(case["input"])["ideas"][0]
        old = read(ROOT / "baseline" / (case["case"] + ".json"))["check"]
        row = {"case": case["case"], "idea_id": idea["id"], "title": idea["title"],
            "old_prior_work": old["prior_work"]["verdict"], "old_math": old["math"]["verdict"],
            "new_prior_work": None, "new_math": None, "new_claim_coverage": None, "changed": None,
            "original_ideas_unchanged": digest(case["source_ideas"]) == case["source_sha256"],
            "original_report_unchanged": digest(case["source_report"]) == case["report_sha256"],
            "status": read(run / "STATUS.json")["status"] if (run / "STATUS.json").exists() else "pending"}
        selected = Path(read(run / "STATUS.json").get("selected_report", str(run / "check_report.json"))) if (run / "STATUS.json").exists() else run / "check_report.json"
        if selected.is_file():
            report = read(selected)
            validate_checks(report, [idea], require_claims=True)
            check = report["checks"][0]
            novelty = check["novelty"]
            sources = check["prior_work"]["sources"]
            row.update(status="complete", new_prior_work=check["prior_work"]["verdict"],
                new_math=check["math"]["verdict"], new_claim_coverage=novelty["overall_status"],
                changed=old["prior_work"]["verdict"] != check["prior_work"]["verdict"],
                math_changed=old["math"]["verdict"] != check["math"]["verdict"],
                new_reason=check["prior_work"]["reason"], claims=novelty["claims"],
                remaining_difference=novelty["remaining_difference"],
                recommended_action=novelty["recommended_action"], next_step=novelty["next_step"],
                search_count=len(report["searches"]), search_status=dict(Counter(s["status"] for s in report["searches"])),
                source_count=len(sources), evidence_levels=dict(Counter(s["evidence_level"] for s in sources)),
                source_titles=[s["title"] for s in sources], source_urls=[s["url"] for s in sources],
                facet_relation_counts={facet: dict(Counter(c["facets"][facet]["relation"]
                    for c in novelty["comparisons"])) for facet in novelty["idea_card"]},
                report=str(selected))
            initial = read(run / "check_report.json")
            row["initial_replay_prior_work"] = initial["checks"][0]["prior_work"]["verdict"]
            row["initial_replay_sources"] = len(initial["checks"][0]["prior_work"]["sources"])
            row["recovery_used"] = selected.name == "check_report_recovery.json"
            row["retrieval_failure_only"] = not sources and not any(s["status"] == "completed" for s in report["searches"])
            coverage_counts[novelty["overall_status"]] += 1
            manifest = read(run / "manifest.json")
            row["execution"] = [{"stage": sid, "status": record["status"],
                "model": record["requested_model"], "effort": record["reasoning_effort"],
                "elapsed_s": record["elapsed_s"]} for sid, record in manifest["stages"].items()]
            if (run / "RETRIEVAL_RECOVERY.md").exists() and not (run / "check_report_recovery.json").exists():
                row["status"] = "recovery_in_progress"
        rows.append(row)
    summary = {"status": "complete" if all(r["status"] == "complete" for r in rows) else "in_progress",
        "case_count": len(rows), "complete": sum(r["status"] == "complete" for r in rows),
        "prior_work_changed": sum(r["changed"] is True for r in rows),
        "math_changed": sum(r.get("math_changed") is True for r in rows),
        "coverage_counts": dict(coverage_counts),
        "originals_unchanged": all(r["original_ideas_unchanged"] and r["original_report_unchanged"] for r in rows),
        "rows": rows,
        "interpretation": "A diagnostic replay with fresh retrieval and changed prompt/model effort, not a controlled accuracy comparison or proof of scientific novelty."}
    write(ROOT / "COMPARISON.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "rows"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
