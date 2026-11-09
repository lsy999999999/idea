"""Versioned researcher notes, provenance and bounded lexical retrieval."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re

from discover import read, write, now


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tokens(text):
    return set(re.findall(r"[a-z][a-z0-9_]+|[\u4e00-\u9fff]", text.lower()))


class Memory:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def identity(self, researcher, domain):
        path = self.root / researcher / "identity.json"
        if path.exists():
            value = read(path)
            if value["domain"] != domain:
                raise ValueError("Stable identity domain changed")
        else:
            write(path, {"id": researcher, "domain": domain, "created_at": now()})
        return read(path)

    def index(self, researcher):
        path = self.root / researcher / "index.json"
        return read(path) if path.exists() else {"notes": {}, "commits": {}}

    def commit(self, researcher, task, stage, result_path):
        result = read(result_path)
        notes = result.get("memory_notes", [])
        idx = self.index(researcher)
        key = task + "/" + stage
        source_hash = digest(result_path)
        if key in idx["commits"]:
            if idx["commits"][key]["source_sha256"] != source_hash:
                raise ValueError("Committed source mutated")
            return
        # Validate every note before writing any version.
        for note in notes:
            for field in ("key", "title", "understanding", "conditions", "example"):
                if not isinstance(note.get(field), str) or not note[field].strip():
                    raise ValueError(f"Invalid memory note {field}")
            questions = note.get("open_questions")
            if not ((isinstance(questions, str) and questions.strip()) or
                    (isinstance(questions, list) and questions and
                     all(isinstance(q, str) and q.strip() for q in questions))):
                raise ValueError("Invalid memory note open_questions")
            if not re.fullmatch(r"[a-z0-9_]{1,80}", note["key"]):
                raise ValueError("Unsafe memory key")
            if note.get("kind") not in {"source_knowledge", "interpretation", "hypothesis", "correction"}:
                raise ValueError("Invalid knowledge kind")
            if note.get("mastery") not in {"read", "explained", "used"}:
                raise ValueError("Invalid mastery evidence level")
            if not isinstance(note.get("sources"), list) or not isinstance(note.get("tags"), list):
                raise ValueError("sources/tags must be arrays")
            if note["kind"] == "source_knowledge" and not note["sources"]:
                raise ValueError("Source knowledge requires provenance")
            if note["key"] in idx["notes"] and not note.get("revision_reason"):
                raise ValueError("Revision requires reason")
        if len({n["key"] for n in notes}) != len(notes):
            raise ValueError("Duplicate keys in one commit")
        for note in notes:
            previous = idx["notes"].get(note["key"])
            version = previous["version"] + 1 if previous else 1
            path = self.root / researcher / "notes" / note["key"] / f"v{version:03d}.json"
            entry = {**note, "version": version, "researcher": researcher,
                     "source_task": task, "source_stage": stage,
                     "source_result": str(result_path), "source_sha256": source_hash,
                     "supersedes": previous["path"] if previous else None, "saved_at": now()}
            if path.exists() and read(path).get("source_sha256") != source_hash:
                raise ValueError("Version collision")
            write(path, entry)
            idx["notes"][note["key"]] = {"path": str(path), "sha256": digest(path),
                "version": version, "title": note["title"], "tags": note["tags"],
                "kind": note["kind"], "source_task": task}
        idx["commits"][key] = {"source_sha256": source_hash, "keys": [n["key"] for n in notes]}
        write(self.root / researcher / "index.json", idx)

    def retrieve(self, researcher, query, limit=4):
        idx = self.index(researcher)
        ranked = []
        for key, item in idx["notes"].items():
            path = Path(item["path"])
            if digest(path) != item["sha256"]:
                raise ValueError("Stored memory hash mismatch")
            note = read(path)
            score = len(tokens(query) & tokens(json.dumps(note, ensure_ascii=False)))
            if score:
                ranked.append((score, key, note))
        ranked.sort(key=lambda x: (-x[0], x[1]))
        return {"researcher": researcher, "query": query, "method": "lexical overlap; current versions only",
                "available_index": idx["notes"], "retrieved": [
                    {"overlap_score": score, "note": note} for score, _, note in ranked[:limit]]}
