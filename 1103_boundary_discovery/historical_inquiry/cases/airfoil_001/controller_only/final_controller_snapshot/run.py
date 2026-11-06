"""Additive historical-material pilot. Imports, but never edits, existing memory code."""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from isolated_cli import invoke, parse_response
from prepare import HERE, PROJECT, save
sys.path.insert(0, str(PROJECT / "src"))
from learning_memory import Memory, digest
from learning_lab import NOTE_SCHEMA

COMMON = """You are a peer researcher in a small collaborative inquiry, using a persistent
research notebook. Respond in clear Chinese and valid JSON, without Markdown fences.
The only permitted research evidence is supplied in this message. Do not invoke any tool,
read files, search, contact other agents, or consult global/project memory. You can request
additional approved source IDs or data via learning_request; the controller supplies them.
No scientific work dated 1988-01-01 or later is permitted. The source report behind the
numeric table is withheld and forbidden. Do not reconstruct or quote it from pretraining.
If something feels familiar, explicitly mark possible_pretraining_familiarity. A cutoff
does not erase pretrained knowledge. Do not cite a remembered work absent from our corpus.
Data arrived as a table; raw data are permitted despite the report being withheld.
Published concepts, your interpretation and a new untested hypothesis are different.
An idea may be a question, a hypothesis, a relation or a method. It need not be solved,
proved, implemented or empirically validated now. Preserve unfinished and rejected branches.
Both researchers can initiate, change their own question, or develop a shared third question.
Do not make one researcher the other's fixed helper or critic. Do not force interdisciplinarity,
agreement, a theory jump, novelty, a new formula, or an interesting-looking disagreement.
State observation / expectation / reason for expectation / conditions separately.
All result JSONs include summary (string), artifacts, evidence, claims, limitations,
next_actions (arrays), and possible_pretraining_familiarity (string; unknown is valid).
Include claims even if it is []. Sources for supplied measurement metadata are ["data.csv"].
memory_use describes PREVIOUSLY RETRIEVED notes only; it is [] when the supplied memory is empty.
Do not claim reading full text: the supplied foundation sources are indexed abstracts/excerpts.
Keep the whole response below 1800 Chinese characters unless specific fields require more.
"""

RESEARCHERS = [
    ("aeroacoustician", "气动声学、流动中的声源与固体边界"),
    ("nonequilibrium_physicist", "非平衡动力学、状态、记忆和观测"),
]


def load(path):
    return json.loads(Path(path).read_text())


def verify_sources(case):
    private = case / "controller_only"
    for name, expected in load(private / "allowed_hashes.json").items():
        if digest(case / "allowed" / name) != expected:
            raise ValueError("Allowed input mutated")
    policy = load(private / "restriction.json")
    for source in load(case / "allowed/sources.json"):
        if source["date"] >= policy["allowed_before_exclusive"]:
            raise ValueError("Post-cutoff source")
        if source["url"] == policy["source_paper"]["id"]:
            raise ValueError("Forbidden source report")


def broker(case, request):
    """A closed corpus, not a search query against a current literature service."""
    corpus = {s["id"]: s for s in load(case / "allowed/sources.json")}
    spectra = {s["id"]: s for s in load(case / "allowed/spectra.json")}
    source_ids = request.get("source_ids", [])
    spectrum_ids = request.get("spectrum_ids", [])
    if (not isinstance(source_ids, list) or not isinstance(spectrum_ids, list)
            or any(s not in corpus for s in source_ids)
            or any(not isinstance(i, int) or i not in spectra for i in spectrum_ids)):
        raise ValueError("Requested item is outside the approved corpus")
    return {"request": request, "sources": [corpus[s] for s in source_ids],
            "spectra": [spectra[i] for i in spectrum_ids],
            "all_rows_csv": (case / "allowed/data.csv").read_text() if request.get("all_rows") is True else None,
            "unavailable_gaps": "No extra publication or unrecorded variable can be obtained in this pilot."}


class Pilot:
    def __init__(self, case, timeout):
        self.case = case
        self.run = case / "run"
        self.run.mkdir(exist_ok=True)
        self.timeout = timeout
        self.memory = Memory(case / "researchers")
        self.state_path = self.run / "state.json"
        self.state = load(self.state_path) if self.state_path.exists() else {"stages": {}}
        verify_sources(case)
        self.situation = load(case / "allowed/situation.json")
        self.corpus = {s["id"]: s for s in load(case / "allowed/sources.json")}
        for rid, domain in RESEARCHERS:
            identity = case / "researchers" / rid / "identity.json"
            original = PROJECT / "learning_lab/researchers" / rid / "identity.json"
            if not identity.exists() and original.exists():
                identity.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(original, identity)
            self.memory.identity(rid, domain)

    def packet(self, sid, rid, query):
        path = self.run / "memory_retrieval" / (sid + ".json")
        if not path.exists():
            save(path, self.memory.retrieve(rid, query))
        return load(path)

    def call(self, sid, role, task, context, notes=False):
        prompt = COMMON + "\nResearcher/role: " + role + "\n" + task
        if notes:
            prompt += "\n" + NOTE_SCHEMA + "\nUse only supplied source URLs. A note is personal understanding, not proof of mastering a field."
        prompt += "\nINPUTS:\n" + json.dumps(context, ensure_ascii=False)
        fingerprint = hashlib.sha256(prompt.encode()).hexdigest()
        path = self.run / "stages" / sid / "result.json"
        if sid in self.state["stages"]:
            record = self.state["stages"][sid]
            if fingerprint != record["input_sha256"] or digest(path) != record["output_sha256"]:
                raise ValueError("Frozen stage inputs/output changed")
            return load(path)
        root = path.parent
        root.mkdir(parents=True, exist_ok=True)
        # Never overwrite an interrupted/invalid attempt.
        attempt = max([int(p.name.split("-")[-1]) for p in root.glob("attempt-*")], default=0) + 1
        print(json.dumps({"stage": sid, "status": "started", "requested_model": "gpt-6-luna"}), flush=True)
        last = root / f"attempt-{attempt-1:03d}"
        if (attempt > 1 and (last / "execution_audit.json").exists()
                and load(last / "execution_audit.json")["returncode"] == 0
                and load(last / "execution_audit.json")["tool_events"] == 0):
            # Reuse a completed but unadmitted answer; never regenerate its scientific content.
            result = parse_response((last / "final.txt").read_text())
        else:
            result = invoke(prompt, root / f"attempt-{attempt:03d}", self.timeout)
            attempt += 1
        result = self.admit_bookkeeping(result)
        try:
            self.validate(result, notes, role)
        except ValueError as error:
            repair = (prompt + "\nFORMATTING/PROVENANCE REPAIR ONLY. Keep the scientific questions, "
                      "interpretations and examples unchanged. Original answer is preserved. "
                      "Add absent runtime arrays as []; supply data.csv for a note based on "
                      "given measurement metadata. memory_use must be [] if no old notes were "
                      "retrieved. Correct the schema/source error: " + str(error)
                      + "\nUNADMITTED ANSWER:\n" + json.dumps(result, ensure_ascii=False))
            result = invoke(repair, root / f"attempt-{attempt:03d}", self.timeout)
            result = self.admit_bookkeeping(result)
            self.validate(result, notes, role)
        save(path, result)
        if notes:
            self.memory.commit(role, self.case.name, sid, path)
        # Save every shared-object version as an artifact; later roles may revise it.
        if "shared_object" in result:
            versions = sorted((self.run / "shared_objects").glob("v*.json"))
            save(self.run / "shared_objects" / f"v{len(versions)+1:03d}.json",
                 {"stage": sid, "researcher": role, "previous_version": len(versions) or None,
                  "shared_object": result["shared_object"],
                  "question_before": result.get("question_before"), "question_after": result.get("question_after"),
                  "reason": result.get("changed_because", result.get("response_to_peer"))})
        self.state["stages"][sid] = {"input_sha256": fingerprint, "output_sha256": digest(path)}
        save(self.state_path, self.state)
        print(json.dumps({"stage": sid, "status": "complete"}), flush=True)
        return result

    @staticmethod
    def admit_bookkeeping(result):
        # Preserve the raw answer. Missing administrative arrays do not warrant regenerating
        # scientific content; an empty claims array does not assert absence of prose claims.
        changes = []
        for key in ("artifacts", "evidence", "claims", "limitations", "next_actions"):
            if key not in result:
                result[key] = []
                changes.append("Missing administrative array initialized empty: " + key)
        if changes:
            result["controller_admission"] = {"changes": changes, "scientific_content_changed": False}
        return result

    def validate(self, result, notes, role):
        if not isinstance(result.get("summary"), str) or not result["summary"].strip():
            raise ValueError("Missing summary")
        for key in ("artifacts", "evidence", "claims", "limitations", "next_actions"):
            if not isinstance(result.get(key), list):
                raise ValueError("Missing runtime array " + key)
        sources = {s["url"] for s in self.corpus.values()} | {s["doi"] for s in self.corpus.values()} | {"data.csv"}
        if notes and not result.get("memory_notes"):
            raise ValueError("No learning note")
        for note in result.get("memory_notes", []):
            if any(s not in sources for s in note.get("sources", [])):
                raise ValueError("Memory note cites an unapproved source")
            if note["key"] in self.memory.index(role)["notes"] and not note.get("revision_reason"):
                raise ValueError("Existing memory key requires a revision reason")
        if notes:
            # Exercise the existing memory validator without touching the real notebook yet.
            with tempfile.TemporaryDirectory(prefix="inquiry-note-validation-") as tmp:
                path = Path(tmp) / "result.json"
                save(path, result)
                Memory(Path(tmp) / "memory").commit(role, "validation", "validation", path)

    def execute(self):
        initial = []
        for i, (rid, domain) in enumerate(RESEARCHERS):
            sid = f"01_initial_{i}"
            initial.append(self.call(sid, rid, """Independently study the situation and your supplied
foundation excerpt. Explain a concrete concept using an explicit small example; then form your
OWN question and question_to_peer. Do not guess the withheld paper's method. Return observation,
expectation, expectation_basis, conditions, initial_question, question_to_peer (strings).
Keep 1-2 reusable memory_notes. Avoid using unexplained dB scaling as if it were raw pressure.
""", {"situation": self.situation, "domain": domain,
       "foundations": [self.corpus["F1"], self.corpus["F2" if i == 0 else "F3"]],
       "memory": self.packet(sid, rid, "flow spectrum observation similarity state 边界 声源 观测")}, notes=True))

        exchanges = []
        for i, (rid, _) in enumerate(RESEARCHERS):
            sid = f"02_exchange_{i}"
            exchange = self.call(sid, rid, """Read both independent understandings. Answer the
other researcher's actual question and pursue YOUR question too. You may propose a shared
third question, preserve two branches, or find the perspectives do not connect. Return
shared_object, question_before, question_after, response_to_peer, disagreement (strings),
branches (array), and learning_request: {needed: boolean, gap: string, why_now: string,
source_ids: array of F1/F2/F3/F4, spectrum_ids: array of integer IDs, all_rows: boolean}.
Only request learning caused by this exchange. No need to invent a gap.
""", {"situation": self.situation, "initial": initial, "earlier_exchanges": exchanges,
       "memory": self.packet(sid, rid, "flow spectrum observation similarity state 边界 声源 观测")})
            if not isinstance(exchange.get("learning_request", {}).get("needed"), bool):
                raise ValueError("Missing learning decision")
            exchanges.append(exchange)

        learned = []
        for i, (rid, _) in enumerate(RESEARCHERS):
            request = exchanges[i]["learning_request"]
            if request["needed"]:
                sid = f"03_learn_{i}"
                supplied = broker(self.case, request)
                save(self.run / "broker" / (sid + ".json"), supplied)
                learned.append(self.call(sid, rid, """Address YOUR actual gap with the brokered
materials. Use a concrete calculation or counterexample, state what changes and what is still
unknown, and distinguish reasoning from an executed calculation. Return learning_change,
worked_example, remaining_gap (strings), and memory_notes. If the available material cannot
answer the request, say so. Do not invent a measurement or use an external source.
""", {"situation": self.situation, "your_initial": initial[i], "exchanges": exchanges,
       "broker_reply": supplied,
       "memory": self.packet(sid, rid, request["gap"] + " flow spectrum state")}, notes=True))

        returned = []
        for i, (rid, _) in enumerate(RESEARCHERS):
            sid = f"04_return_{i}"
            returned.append(self.call(sid, rid, """Return as a peer, with what each researcher
actually learned. Respond to the other's revised interpretation and develop your own line.
Return shared_object, question_before, question_after, changed_because (strings), branches
(array of questions/hypotheses/methods including abandoned branches with reasons), and
memory_notes. Quote the specific other researcher statement that matters. If the question
did not change, say unchanged; do not narrate an imaginary conceptual breakthrough.
""", {"situation": self.situation, "initial": initial, "exchanges": exchanges,
       "learning": learned, "previous_return": returned,
       "memory": self.packet(sid, rid, "flow spectrum observation similarity state 边界 声源 观测")}, notes=True))

        ideas = self.call("05_candidates", "discussion_recorder", """Record only ideas that
actually emerged. Do not invent a synthesis. Return ideas (0-4 objects with id,title,idea,
motivation,emergence quoting stage IDs and actual changes), question_trajectory (array),
preserved_branches (array). An unfinished question is valid; neither feasibility nor novelty
filters it out. Distinguish initial questions from genuinely shared reformulations.
""", {"initial": initial, "exchanges": exchanges, "learning": learned, "returned": returned})
        if not isinstance(ideas.get("ideas"), list):
            raise ValueError("Missing ideas array")
        save(self.run / "ideas.json", ideas)
        checked = self.call("06_check", "idea_check_agent", """Exactly two duties: (1) identify
a very similar existing core direction, even when details differ, (2) identify concrete obvious
mathematical/logical mistakes. Unsolved questions, missing validation, implementation or proof
are not errors. Use only the approved historical excerpts: DO NOT retrieve modern work or the
withheld report. Return checks array, each {idea_id, prior_work: {status: already_done or
unclear, reason, sources}, math: {status: no_obvious_error or obvious_error, reason}}.
If four excerpts cannot establish literature originality, prior_work MUST be unclear. Even a
close foundation need not entail an entire specific proposal; compare carefully, by core idea.
This is a bounded historical-corpus check, not a claim of world novelty.
""", {"ideas": ideas["ideas"], "sources": list(self.corpus.values())})
        if {c["idea_id"] for c in checked.get("checks", [])} != {c["id"] for c in ideas["ideas"]}:
            raise ValueError("Check coverage mismatch")
        for c in checked["checks"]:
            if c["prior_work"]["status"] not in {"already_done", "unclear"} or c["math"]["status"] not in {"no_obvious_error", "obvious_error"}:
                raise ValueError("Invalid two-part judgment")
        save(self.run / "check_report.json", checked)
        # Preserve outcomes with the research experience using the existing versioned memory API.
        path = self.run / "research_experience.json"
        if not path.exists():
            save(path, {"memory_notes": [{"key": "airfoil_historical_experience", "title": "翼型数据讨论与限定检查",
                 "kind": "interpretation", "mastery": "read", "understanding": json.dumps({"ideas": ideas["ideas"], "checks": checked["checks"]}, ensure_ascii=False),
                 "conditions": "任务分支；未读数据来源报告，仅历史摘要；未证明新颖性。", "example": "实际候选和检查保存在本次运行。",
                 "open_questions": "继续追踪保留的未决分支，并核实适用条件。", "tags": ["flow", "spectrum", "state", "研究经历"], "sources": [str(self.run / "check_report.json")]}]})
        for rid, _ in RESEARCHERS:
            self.memory.commit(rid, self.case.name, "06_check_experience", path)
        rid = RESEARCHERS[1][0]
        fresh = self.call("07_fresh_continuation", rid, """This is a fresh session. Use only
the retrieved notebook and the short situation, not the full dialogue. Select a saved unresolved
question and advance or correct it with a small example. Return memory_use with exact key,
version, source_task and scope_check, continuation_question, worked_example, remaining_gap.
Distinguish an existing stored idea from a new discovery.
""", {"brief": self.situation["situation"], "memory": self.packet("07_fresh_continuation", rid, "flow spectrum state 研究经历")})
        self.state["status"] = "complete"
        save(self.state_path, self.state)
        audit(self.case)


def audit(case):
    verify_sources(case)
    protected = load(case / "controller_only/protected_hashes.json")
    changes = [p for p, expected in protected.items() if not Path(p).is_file() or digest(p) != expected]
    audits = list((case / "run/stages").glob("*/attempt-*/execution_audit.json"))
    tool_events = sum(load(p)["tool_events"] for p in audits)
    state = load(case / "run/state.json")
    record = {"protected_files": len(protected), "changed_protected_files": changes,
              "stages": len(state["stages"]), "tool_events": tool_events,
              "source_cutoff_checked": True, "source_report_body_supplied": False,
              "pretraining_exclusion_claimed": False,
              "status": "pass" if not changes and not tool_events else "fail"}
    save(case / "run/AUDIT.json", record)
    if record["status"] != "pass":
        raise ValueError("Artifact/isolation audit failed")
    print(json.dumps(record), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="airfoil_001")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--audit-only", action="store_true")
    args = parser.parse_args()
    if not args.case.replace("_", "").isalnum():
        parser.error("Unsafe case name")
    case = HERE / "cases" / args.case
    with (case / ".run.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.audit_only:
            audit(case)
        else:
            Pilot(case, args.timeout).execute()
            # Keep the summary-only historical record, but always include actual rationale
            # and numeric evidence in the final assessment before the entrypoint returns.
            from review import main as review_evidence
            review_evidence(case)
            audit(case)
