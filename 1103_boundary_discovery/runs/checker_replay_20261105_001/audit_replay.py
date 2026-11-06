"""Read-only artifact/trace audit; it does not establish semantic correctness."""
from collections import Counter
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
sys.path.insert(0, str(PROJECT / "src"))
from discover import read, write
from idea_check import validate_checks


def source_dois(record):
    value = record.get("doi", record.get("DOI", ""))
    return str(value).lower().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")


def main():
    plan = read(ROOT / "PLAN.json")
    rows = []
    for case in plan["cases"]:
        run = ROOT / "cases" / case["case"]
        if not (run / "check_report.json").exists():
            continue
        selected = Path(read(run / "STATUS.json").get("selected_report", str(run / "check_report.json"))) if (run / "STATUS.json").exists() else run / "check_report.json"
        report = read(selected)
        validate_checks(report, read(run / "ideas.json")["ideas"], require_claims=True)
        check = report["checks"][0]
        workspace = Path(report["check_result_path"]).parent
        events = workspace.parent / "events.jsonl"
        commands = []
        for line in events.read_text().splitlines():
            event = json.loads(line)
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                commands.append(item)
        retrieval_commands = [c for c in commands if any(s in c.get("command", "")
            for s in ("curl ", "urlopen(", "requests.get("))]
        explicit_forbidden_reads = [c["command"] for c in commands if any(
            path in c.get("command", "") for path in
            ["/baseline/", "/codex-shared/SHARED_MEMORY.md", "/.codex/memories/",
             "/runs/cross_domain_ideas_001/", "/runs/learn_20261104_community/",
             "/runs/learn_20261104_immune/"])]
        snapshots = []
        for search in report["searches"]:
            if search["status"] != "completed":
                continue
            path = Path(search["snapshot_path"])
            if not path.is_absolute():
                path = PROJECT / path
            try:
                data = json.loads(path.read_text())
                if isinstance(data, dict) and (data.get("error") or data.get("errCode") or data.get("status") == "failed"):
                    kind = "api_error_marked_completed"
                else:
                    kind = "json_response"
            except (ValueError, UnicodeError):
                content = path.read_text()
                kind = "ledger_or_summary" if any(w in content[:600].lower()
                    for w in ("ledger", "query", "retrieval", "检索")) else "non_json_response_needs_inspection"
            snapshots.append({"query": search["query"], "path": str(path), "kind": kind})
        source_types = []
        downloaded = []
        for path in workspace.rglob("*.json"):
            if path.name == "result.json":
                continue
            try:
                data = json.loads(path.read_text())
            except (ValueError, UnicodeError):
                continue
            if isinstance(data, dict):
                record = data.get("message", data)
                if isinstance(record, dict):
                    downloaded.append((path, record))
        for source in check["prior_work"]["sources"]:
            doi = source_dois({"doi": source["url"]})
            matches = [(path, record) for path, record in downloaded if source_dois(record) == doi]
            source_types.append({"source_id": source["source_id"], "title": source["title"],
                "evidence_level": source["evidence_level"], "url": source["url"],
                "downloaded_metadata_type": matches[0][1].get("type") if matches else None,
                "metadata_path": str(matches[0][0]) if matches else None})
        rows.append({"case": case["case"], "contract_passed": True,
            "reported_searches": len(report["searches"]),
            "reported_search_status": dict(Counter(s["status"] for s in report["searches"])),
            "retrieval_command_count": len(retrieval_commands),
            "search_snapshot_kinds": dict(Counter(s["kind"] for s in snapshots)),
            "search_snapshots": snapshots, "source_metadata": source_types,
            "explicit_forbidden_read_commands": explicit_forbidden_reads,
            "scope_note": "Trace scan checks explicit recorded commands only; absence does not prove no contextual exposure. Snapshot existence and quote matching do not prove semantic entailment."})
    result = {"cases": rows, "complete_cases_audited": len(rows),
        "contract_all_passed": all(r["contract_passed"] for r in rows),
        "explicit_forbidden_reads_found": any(r["explicit_forbidden_read_commands"] for r in rows)}
    write(ROOT / "ARTIFACT_AUDIT.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "cases"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
