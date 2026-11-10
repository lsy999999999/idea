"""Prepare a source-screened data-only situation without source-paper text."""
from __future__ import annotations
import csv
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0, str(PROJECT / "src"))
from learning_memory import digest


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def abstract(work):
    positions = work.get("abstract_inverted_index") or {}
    return " ".join(token for _, token in sorted(
        (i, token) for token, indices in positions.items() for i in indices))


def prepare():
    case = HERE / "cases" / "airfoil_001"
    if case.exists():
        raise ValueError("Case already exists; preserve it")
    private = case / "controller_only"
    allowed = case / "allowed"
    private.mkdir(parents=True)
    allowed.mkdir()
    # Freeze protected code, memory and completed learning runs before any new research.
    protected = {}
    roots = [PROJECT / "src", PROJECT / "learning_lab", PROJECT / "tests",
             *PROJECT.glob("runs/learn_*")]
    for root in roots:
        for p in root.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                protected[str(p)] = digest(p)
    save(private / "protected_hashes.json", protected)

    raw = Path("/private/tmp/airfoil_data_20261105.csv")
    shutil.copy2(raw, allowed / "data.csv")
    metadata = json.loads(Path("/private/tmp/uci_airfoil_metadata_20261105.json").read_text())["data"]
    shutil.copy2(Path("/private/tmp/uci_airfoil_metadata_20261105.json"), private / "repository_metadata.json")
    works = json.loads(Path("/private/tmp/airfoil_openalex_20261105.json").read_text())["results"]
    target = next(w for w in works if w["title"].lower() == "airfoil self-noise and prediction")
    # Never save the target's abstract or full text, even in the actor's parent directory.
    save(private / "restriction.json", {
        "source_paper": {"id": target["id"], "title": target["title"],
                         "indexed_publication_date": target["publication_date"],
                         "nasa_id": "19890016302", "report": "NASA-RP-1218"},
        "source_association": "Repository creators/year and NASA report authors/year match; repository intro_paper is null.",
        "date_evidence": "OpenAlex metadata only; NASA blocked (403). Earliest release/preprint not independently verified.",
        "allowed_before_exclusive": "1988-01-01",
        "date_policy": "Conservative pre-1988 corpus; target and all later work excluded. Do not claim exact earliest-publication reconstruction.",
        "raw_data_exception": "User permits source-associated data but forbids the associated paper. Modern repository metadata is controller-only; actors get field names/units and raw values.",
        "data_url": metadata["data_url"], "data_sha256": digest(allowed / "data.csv"),
        "target_body_downloaded": False,
    })
    corpus = []
    for sid, name in [("F1", "buckingham"), ("F2", "lighthill"), ("F3", "curle"), ("F4", "welch")]:
        w = json.loads(Path(f"/private/tmp/inquiry_{name}_20261105.json").read_text())
        assert w["publication_date"] < "1988-01-01" and w["id"] != target["id"]
        corpus.append({"id": sid, "title": w["title"], "date": w["publication_date"],
                       "doi": w["doi"], "url": w["id"], "access": "abstract_or_indexed_excerpt_only",
                       "text": abstract(w), "limitations": "Not full text. F1 has OCR artifacts; use its general premise cautiously."})
    save(allowed / "sources.json", corpus)
    rows = list(csv.DictReader(io.StringIO(raw.read_text())))
    columns = list(rows[0])
    units = ["Hz", "deg", "m", "m/s", "m", "dB"]
    fields = [{"name": key, "units": unit,
               "range": [min(float(r[key]) for r in rows), max(float(r[key]) for r in rows)]}
              for key, unit in zip(columns, units)]
    groups = {}
    for r in rows:
        k = tuple(float(r[c]) for c in columns[1:5])
        groups.setdefault(k, []).append([float(r[columns[0]]), float(r[columns[-1]])])
    spectra = [{"id": i, "conditions": dict(zip(columns[1:5], k)),
                "frequency_and_level": sorted(v)} for i, (k, v) in enumerate(groups.items())]
    save(allowed / "spectra.json", spectra)
    save(allowed / "situation.json", {
        "situation": "Wing-section aerodynamic/acoustic measurements in a low-noise wind tunnel; explore which questions the recorded spectra support.",
        "source_scope": "Only numeric data and measurement metadata. No source-paper interpretation, title, authors or conclusions supplied.",
        "count": len(rows), "fields": fields,
        "conditions": "Nominal NACA0012 geometry family; span and observer position fixed per repository metadata. Scaling/calibration of the reported dB level is unspecified.",
        "observed": "Frequency-indexed reported sound levels at combinations of geometric and flow variables. These are not independently randomized trials or raw time signals.",
        "expected": None, "why_expected": None,
        "preprocessing": "Unknown expectations are retained. Each researcher must state its own expectation and its reason, including source and conditions.",
        "spectrum_count": len(spectra),
        "sample_spectra": [spectra[i] for i in [0, len(spectra)//2, len(spectra)-1]],
        "data_access": "All CSV rows can be requested through the controller; individual spectra can be requested by id. No autonomous browser/shell access.",
        "source_catalog": [{k: s[k] for k in ("id", "title", "date", "access")} for s in corpus],
    })
    save(private / "allowed_hashes.json", {p.name: digest(p) for p in allowed.iterdir()})
    # Existing notes are not erased or copied wholesale into a historical actor context.
    exclusions = []
    for p in (PROJECT / "learning_lab/researchers").glob("*/notes/*/v*.json"):
        exclusions.append({"path": str(p), "sha256": digest(p),
                           "reason": "No closed, verified pre-cutoff source dependency chain; not exposed in this task."})
    save(private / "memory_screen.json", {"excluded_versions": exclusions,
         "policy": "Fail closed for unaudited old notes. Use existing Memory class in a separate task branch; main researcher store remains unchanged."})
    print(json.dumps({"case": str(case), "rows": len(rows), "spectra": len(spectra), "protected_files": len(protected)}))


if __name__ == "__main__":
    prepare()
