"""Version personal and shared questions separately, with controller-owned provenance."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import re


PROTOCOL = """
QUESTION STATE PROTOCOL v2:
question_state.self is YOUR authoritative current personal question. peer_questions belong
to their named owners. shared_question is the discussion's current shared question, or null.
Do not reconstruct your prior question from the latest peer message. The controller records
the actual before-state; do NOT return question_before or question_after.
Return personal_question_update: {base: the exact self.ref object, action: retain/revise,
question: your current or revised personal question, reason: a nonempty explanation,
influenced_by: array of exact question ref objects from this supplied packet}.
Retain means the question text stays exactly the same. Revise may include adopting a peer's
line or the shared question: explain why; use influenced_by to identify relevant question refs.
You need not preserve disagreement or a distinct personal question if you decide to change it.
Separately return shared_question_update: null, or {base: the exact shared_question.ref (null
if none yet), action: propose/revise/retain, question: shared question text, reason: nonempty,
influenced_by: array of refs from this packet}. Propose is only for a first shared question.
A shared question is a versioned proposal, not proof of peer agreement. Revising it NEVER
changes another researcher's personal question. Your own personal update is independent too.
"""


def read(path):
    return json.loads(Path(path).read_text())


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def object_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ref(question):
    return {key: question[key] for key in ("id", "owner", "version")}


class QuestionState:
    def __init__(self, root, researchers):
        self.root = Path(root)
        self.researchers = list(researchers)

    def events(self):
        events = [read(p) for p in (self.root / "events").glob("*.json")]
        events.sort(key=lambda event: event["sequence"])
        for i, event in enumerate(events, 1):
            if event["sequence"] != i:
                raise ValueError("Question history sequence changed")
            if file_hash(event["source_result"]) != event["source_sha256"]:
                raise ValueError("Question source result changed")
        return events

    def current(self):
        state = {"personal": {}, "shared": None}
        for event in self.events():
            for update in event["updates"]:
                if update["scope"] == "personal":
                    state["personal"][update["owner"]] = update
                else:
                    state["shared"] = update
        return state

    def packet(self, stage, researcher):
        """Freeze the state this particular call actually saw, including ownership labels."""
        self._safe(stage)
        if researcher not in self.researchers:
            raise ValueError("Unknown question owner")
        path = self.root / "inputs" / (stage + ".json")
        if path.exists():
            packet = read(path)
            if packet["researcher"] != researcher:
                raise ValueError("Question packet belongs to a different researcher")
            return packet
        state = self.current()
        if researcher not in state["personal"]:
            raise ValueError("Personal question has not been initialized")
        packet = {"researcher": researcher,
                  "self": self._view(state["personal"][researcher]),
                  "peer_questions": [self._view(q) for rid, q in state["personal"].items()
                                     if rid != researcher],
                  "shared_question": self._view(state["shared"]) if state["shared"] else None}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            json.dump(packet, stream, ensure_ascii=False, indent=2)
        return packet

    def history_packet(self, stage):
        """A recorder must not see future question events when a run is resumed."""
        self._safe(stage)
        path = self.root / "inputs" / (stage + "_history.json")
        if path.exists():
            return read(path)
        packet = {"question_history": self.events(), "current_questions": self.current()}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            json.dump(packet, stream, ensure_ascii=False, indent=2)
        return packet

    @staticmethod
    def _view(question):
        return {"ref": ref(question), "question": question["question"],
                "source_stage": question["source_stage"], "source_result": question["source_result"],
                "proposed_by": question["proposed_by"], "reason": question["reason"]}

    @staticmethod
    def _safe(stage):
        if not re.fullmatch(r"[A-Za-z0-9_]+", stage):
            raise ValueError("Unsafe question stage")

    @staticmethod
    def _text(value, name):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Missing question " + name)

    def validate(self, stage, researcher, result, packet=None, initial=False):
        self._safe(stage)
        if researcher not in self.researchers:
            raise ValueError("Unknown question owner")
        events = self.events()
        previous = next((e for e in events if e["stage"] == stage), None)
        if previous:
            if previous["researcher"] != researcher or previous["result_object_sha256"] != object_hash(result):
                raise ValueError("Already recorded question result changed")
            return  # Idempotent recovery after committing an event but before the stage manifest.
        state = self.current()
        if initial:
            if researcher in state["personal"]:
                raise ValueError("Cannot overwrite an initialized personal question")
            self._text(result.get("initial_question"), "initial text")
            return
        if not packet or packet["researcher"] != researcher:
            raise ValueError("Missing owner-specific question state")
        if "question_before" in result or "question_after" in result:
            raise ValueError("Ambiguous before/after fields are forbidden; use separate personal/shared updates")
        views = [packet["self"], *packet["peer_questions"]]
        if packet["shared_question"]:
            views.append(packet["shared_question"])
        known = [v["ref"] for v in views]
        if "personal_question_update" not in result or "shared_question_update" not in result:
            raise ValueError("Explicit personal and shared question decisions required")
        self._validate_update(result["personal_question_update"], state["personal"][researcher],
                              packet["self"], known, "personal")
        update = result["shared_question_update"]
        if update is not None:
            self._validate_update(update, state["shared"], packet["shared_question"], known, "shared")

    def _validate_update(self, update, current, supplied, known, scope):
        if not isinstance(update, dict):
            raise ValueError("Question update must be an object")
        expected = supplied["ref"] if supplied else None
        if "base" not in update or update["base"] != expected:
            raise ValueError("Question update has the wrong owner or base version")
        if (ref(current) if current else None) != expected:
            raise ValueError("Question update refers to a stale version")
        self._text(update.get("question"), "text")
        self._text(update.get("reason"), "change/retain reason")
        refs = update.get("influenced_by")
        if not isinstance(refs, list) or any(r not in known for r in refs):
            raise ValueError("Question influence must cite supplied question refs")
        action = update.get("action")
        allowed = {"retain", "revise"} if current else {"propose"}
        if scope == "personal" and not current:
            raise ValueError("Personal questions require initialization first")
        if action not in allowed:
            raise ValueError("Invalid question update action")
        if action == "retain" and update["question"] != current["question"]:
            raise ValueError("Retain cannot change question text")

    def accept(self, stage, researcher, result, result_path, packet=None, initial=False):
        self.validate(stage, researcher, result, packet, initial)
        path = self.root / "events" / (stage + ".json")
        if path.exists():
            return read(path)
        state = self.current()
        source = {"source_stage": stage, "source_result": str(Path(result_path).resolve()),
                  "proposed_by": researcher}
        updates = []
        decisions = {}
        if initial:
            updates.append({"id": "personal:" + researcher, "owner": researcher,
                            "scope": "personal", "version": 1, "question": result["initial_question"],
                            "reason": "Independent initial question", "influenced_by": [], **source})
        else:
            for scope, field in (("personal", "personal_question_update"), ("shared", "shared_question_update")):
                decision = result[field]
                decisions[scope] = copy.deepcopy(decision)
                if decision is None or decision["action"] == "retain":
                    continue
                previous = state["personal"][researcher] if scope == "personal" else state["shared"]
                updates.append({"id": previous["id"] if previous else "shared:discussion",
                                "owner": researcher if scope == "personal" else "shared",
                                "scope": scope, "version": previous["version"] + 1 if previous else 1,
                                "question": decision["question"], "reason": decision["reason"],
                                "influenced_by": decision["influenced_by"], **source})
        event = {"stage": stage, "researcher": researcher, "sequence": len(self.events()) + 1,
                 "source_result": source["source_result"], "source_sha256": file_hash(result_path),
                 "result_object_sha256": object_hash(result),
                 "before": copy.deepcopy(packet), "decisions": decisions, "updates": updates}
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x") as stream:
            json.dump(event, stream, ensure_ascii=False, indent=2)
        return event
