# Cross-disciplinary research proposals — 4 November 2026

The pilot generated three proposals by combining disciplinary inputs before choosing
the questions. A final check assessed similar prior work and obvious mathematical or
logical errors. One direction was marked already done; two remain candidates after
a limited literature search. All three passed the broad coherence check.

| Proposal | Disciplinary crossing | Prior-work check | Mathematical check |
| --- | --- | --- | --- |
| I-01: Which rare histories determine ecological resilience? | Non-equilibrium physics × evolutionary ecology | No close match found in this search; substantial adjacent work | No obvious error |
| I-02: Which local rules allocate immune memory across tissues and response types? | Immunology × mechanism design | No close match found in this search; substantial adjacent work | No obvious error |
| I-03: How do institutions change the ecological conditions that determine their future incentives? | Evolutionary ecology × mechanism design | Already done at the level of a very similar direction | No obvious error |

## I-01 — Resilience as a competition between histories

Two ecosystems can have similar average population sizes and traits while differing
in their vulnerability to collapse. Ask whether this difference arises from the
rare sequences through which populations modify their environment and subsequently
adapt to it. Transfer the physics of rare paths and competing trajectory classes to
joint population–trait–environment histories. The proposed shift is to explain
resilience through the organization of possible histories.

The checker found close ingredients in [WKB theory of large deviations in stochastic
populations](https://doi.org/10.1088/1751-8121/aa669a) and [Noise driven phase transitions
in eco-evolutionary systems](https://doi.org/10.48550/arxiv.2310.08735). Its limited
search did not identify the specific research direction linking competing joint
histories to resilience. **Large-deviation methods in population biology are already
established; using them alone is not a new idea.**

## I-02 — Immune memory as distributed allocation rules

Immune cells carry different exposure histories, occupy different tissues, and
compete for resources. Ask which local signaling, survival, and migration rules
combine that dispersed information into a useful balance of specific memory,
broad trained responses, and tissue readiness—and when those rules amplify damage.
The mechanism-design contribution is to ask how local rules produce a collective
allocation. Cells need not possess conscious intentions.

The checker found [Organismal mucosal immunology: A perspective through the eyes of
game theory](https://doi.org/10.1016/j.mucimm.2024.12.003) and [Immune response from a
resource allocation perspective](https://doi.org/10.3389/fgene.2012.00267). It did not
identify a close match for the proposed local-information-to-memory-allocation
question. **Both economic perspectives on immunity and immune resource allocation
already exist; changing the label to “mechanism design” does not establish novelty.**

## I-03 — Institutions that reshape their own future incentives

Ask how participants' actions change a shared ecological environment, which then
changes future payoffs and feasible actions. This connects niche construction to
dynamic incentives and cooperation stability.

The checker marked this direction **already done** after reading [Spatial
coevolutionary dynamics in population games with environmental
feedbacks](https://doi.org/10.1103/k326-3y4g). Its abstract explicitly describes
strategy–environment feedback, strategy switching, and stability. Those shared
elements are sufficient under the user's broad similarity rule; matching every
institutional detail is unnecessary.

## What changed in the agent system

Four disciplinary roles supplied sourced structures and open questions from physics,
ecology, immunology, and economics. A synthesis role used those inputs to produce the
complete batch, including concrete concept mappings. A final check role assessed
every proposal. These six logical roles ran sequentially using requested model
`gpt-6-luna`; the checker received one bounded follow-up to correct its similarity
threshold. No scientific experiments were conducted.

Earlier SQLite work chose a question within systems research and added analogies
afterward. Here, multiple disciplines contribute before the research questions are
formed. The proposals contain explicit transfers, though the strength of each
connection varies: the immune proposal still relies heavily on a conceptual analogy.

The main observed weakness is novelty discrimination. The initial checker reported
no close work for all three proposals. Shorter searches using established terminology
changed I-03 to already done. The reusable prompt now explicitly forbids rescuing
novelty merely because an abstract omits some proposed details. Further improvement
should focus on sharper conceptual transfers and better similarity judgments, while
keeping immediate solvability out of idea selection.

The first two verdicts describe a bounded search, not established originality. All
mathematical verdicts mean only that the proposals contain no obvious contradiction;
hard open questions remain valid proposals.

## Saved outputs

- [Original proposals and concept mappings](runs/cross_domain_ideas_001/stages/synthesize/attempt-001/workspace/IDEAS.md)
- [Current final check](runs/cross_domain_ideas_001/stages/check_calibrated/attempt-001/workspace/CHECK.md)
- [Current structured judgments](runs/cross_domain_ideas_001/check_report_calibrated.json)
- [Retrieved abstracts extracted from execution records](runs/cross_domain_ideas_001/retrieved_source_abstracts.json)
- [Initial check, retained for comparison](runs/cross_domain_ideas_001/check_report.json)
- [Similarity-threshold correction](runs/cross_domain_ideas_001/CHECK_CALIBRATION.md)
- [Reusable workflow and run command](docs/CROSS_DOMAIN_IDEAS.md)

Seven existing checker contract tests and three cross-domain handoff tests passed.
The handoff tests check preservation and coverage of proposals, resumption without
new calls, and complete concept mappings; they do not evaluate scientific creativity.
