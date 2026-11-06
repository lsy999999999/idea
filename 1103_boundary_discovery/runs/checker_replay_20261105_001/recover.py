"""One bounded retrieval recovery; preserve the initial report and its failure."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from discover import read, stage_run, write
from idea_check import CHECKER_PROMPT, POLICY, SCHEMA_VERSION, validate_checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", type=int, required=True)
    args = parser.parse_args()
    plan = read(ROOT / "PLAN.json")
    case = plan["cases"][args.case - 1]
    run = ROOT / "cases" / case["case"]
    original = read(run / "check_report.json")
    note = run / "RETRIEVAL_RECOVERY.md"
    if not note.exists():
        note.write_text("""The initial completed checker report is preserved and all its literature searches failed due to OpenAlex connection timeouts. This is an operational retrieval failure, not evidence changing prior-work coverage. Make ONE bounded recovery using different public services, especially Crossref or Europe PMC, rather than repeating OpenAlex. Use at most TWO focused new search queries, with direct source retrieval as needed, and inspect at most three closest accessible sources. Save raw search responses and source text. Reuse the supplied original idea and its extracted claims faithfully, adjusting extraction only to correct an explicit error. Read no historical baseline reports, prior runs or shared memories. Record exactly which claims have source evidence and which remain unknown. Produce a complete claim-centric-v1 report; do not force a positive or negative result. This recovery is additional to the initial failed retrieval and must be described as such. Validate the saved result with the current validate_checks(result, packet['ideas'], require_claims=True).\n""")
    path, result = stage_run(run, "check_recovery", "idea_check_agent",
        CHECKER_PROMPT + "\nFollow RETRIEVAL_RECOVERY.md; its narrower retrieval budget overrides the general query budget.",
        [run / "ideas.json", POLICY, Path(original["check_result_path"]), note],
        plan["model"], plan["effort"], 600)
    checks = validate_checks(result, read(run / "ideas.json")["ideas"], require_claims=True)
    output = run / "check_report_recovery.json"
    write(output, {"schema_version": SCHEMA_VERSION, "ideas_path": str(run / "ideas.json"),
        "check_result_path": str(path), "initial_report": str(run / "check_report.json"),
        "checks": checks, "searches": result["searches"]})
    write(run / "STATUS.json", {"status": "complete", "selected_report": str(output),
        "initial_report": str(run / "check_report.json"), "result": str(path)})
    print({"case": case["case"], "recovery": "complete", "prior": checks[0]["prior_work"]["verdict"],
        "coverage": checks[0]["novelty"]["overall_status"]})


if __name__ == "__main__":
    main()
