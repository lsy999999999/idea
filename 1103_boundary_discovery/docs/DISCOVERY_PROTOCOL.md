# Discovery Protocol

## Purpose

Run a small, evidence-led search for ideas that add an explanatory state or relation and make a new, falsifiable prediction. A better fit or a new model variant alone is not a discovery. Synthetic and software experiments can establish reproducible behavior in their stated environment; they do not establish a mechanism in the natural world.

## One discovery cycle

Exploration starts in **seed mode**: record an observation, a possible distinction or analogy, and one cheap next action. Do not demand a complete ledger or exhaustive novelty review for every early thought. Promote a branch to the full evidence record below once it has a concrete, distinguishable prediction. An established neighboring concept can be useful raw material; check whether its actual mapping, implications, or test in this problem add something.

1. **Observe a boundary.** Record a concrete result, failure, or disagreement and the conditions under which it occurs. State what the current explanation predicts and where it stops distinguishing outcomes.
2. **Name the missing distinction.** Ask whether the observations collapse cases that behave differently. Propose a measurable variable or state `y` that separates them. Search another field for a useful construct or relation, recording the source and the mapping rather than borrowing terminology alone.
3. **Write the smallest hypothesis.** State a relation among the existing variables and `y`, its direction or conditions, and one prediction that differs from the leading alternative. Include at least one outcome that would count against it.
4. **Choose discriminating evidence.** Identify the cheapest file inspection, source retrieval, calculation, or Python experiment that can separate the accounts. Prefer an intervention, held-out regime, or counterexample over another fit to the same observations. Make the baseline and success criterion explicit before running it.
5. **Acquire and log evidence.** Use ordinary project files, targeted literature/source retrieval, and small executable experiments. Record inputs, commands or code paths, seeds, outputs, and limitations. Do not treat a model answer or a plausible citation as evidence until checked against its source.
6. **Update, revise, or pivot.** Compare the result with the prewritten predictions. A failed prediction should cause a named revision, a narrower scope, or abandonment. Re-run only when the revision changes a prediction or addresses a documented implementation defect.

Each cycle should produce a short ledger update and a next action. Cycles may be sequential or selectively parallel. Wake a role only when its judgment or work is needed; roles can be invoked repeatedly, and no claim is made that six agents run simultaneously.

## Logical roles

- **boundary**: Finds the observation/explanation mismatch, checks the measurement and its conditions, and states what remains unidentified.
- **bridge**: Searches adjacent fields for a variable, state representation, or relationship that could resolve that mismatch; records provenance and a precise mapping.
- **theorist**: Builds the minimal account connecting the old variables and proposed `y`; derives competing predictions and assumptions.
- **experimentalist**: Turns predictions into the smallest executable or retrievable evidence plan, then runs and records it.
- **skeptic**: Looks for leakage, confounding, implementation mistakes, weak baselines, post-hoc criteria, and explanations that make the same prediction.
- **coordinator**: Maintains the ledger, resolves contradictions, selects which role to wake next, and applies continuation/stopping rules.

One person or model may fill several roles. Keep role outputs attributable in the ledger so that a proposal is not mistaken for an independent check.

## Candidate and evidence ledger

Use one JSON object per candidate (or a small JSON file while the run is tiny). Preserve prior versions; append revisions and evidence rather than silently replacing them.

```json
{
  "candidate_id": "C001",
  "version": 1,
  "parent_id": null,
  "status": "proposed",
  "boundary": {
    "observation": "",
    "conditions": [],
    "current_explanation": "",
    "unexplained_distinction": ""
  },
  "bridge": {
    "candidate_y": "",
    "operational_measurement": "",
    "mapping": "",
    "sources": []
  },
  "hypothesis": {
    "claim": "",
    "assumptions": [],
    "predictions": [{"condition": "", "outcome": ""}],
    "discriminates_from": "",
    "falsifier": ""
  },
  "experiment": {
    "unit": "",
    "intervention_or_split": "",
    "baseline": "",
    "metric_and_threshold": "",
    "inputs_seed_code": ""
  },
  "evidence": [],
  "revisions": [],
  "decision": {"continue_or_stop": "", "reason": "", "next_action": ""},
  "claim_scope": ""
}
```

Each `sources` item should include a stable URL or local path, title/author/year when available, access date, and what it supports. Each `evidence` item should include an ID, type (`file`, `literature`, `calculation`, or `experiment`), exact locator or command, observed result, relation (`supports`, `contradicts`, or `limits`), and provenance (including seed/version where relevant). Store candidate ideas separately from evidence: an unverified proposal is not evidence.

## From data to a testable idea

Start from a specific contrast in the data, not from a target score. Ask what distinction the current representation loses; define a candidate state `y` that can be measured independently; explain why it should vary before or with the outcome; then derive a conditional prediction that a competing account does not share. Design the smallest test that makes those predictions diverge. Report the tested population, regimes, measurement, and uncertainty. If the proposal only changes an architecture, prompt, optimizer, or fit criterion and yields no new state, relationship, or discriminating prediction, classify it as an engineering variant rather than an explanatory idea.

## Continue, pivot, stop

- **Continue** when an unresolved prediction can still change the decision and a concrete, affordable evidence action exists.
- **Revise** only when evidence identifies a specific failed assumption, measurement, or implementation step. Preserve the old version and write the revised prediction before another run.
- **Pivot or reject** when the proposed `y` cannot be measured, the predicted contrast is not identifiable with available evidence, a key prediction fails, or a simpler account explains the result equally well. Do not rescue a candidate by changing its success criterion after seeing the output.
- **Stop a candidate** when its key prediction survives the predeclared discriminating test, the strongest accessible alternative has been checked, and a separate seed or regime reproduces the effect at its stated scope; or when further affordable evidence is unlikely to change the conclusion. State what was not tested.
- **Stop the search** when no live candidate has a discriminating, affordable next action. A promising result is a reason to write a scoped claim and a follow-up, not to assert broad novelty.

## Claim boundary

For a generated simulator or software testbed, claims concern that simulator, workload, implementation, and tested conditions. Independent code execution and source checking improve reproducibility but do not validate an unobserved natural mechanism. Literature screening can inform positioning; it cannot establish novelty without a systematic, current search and expert review.

