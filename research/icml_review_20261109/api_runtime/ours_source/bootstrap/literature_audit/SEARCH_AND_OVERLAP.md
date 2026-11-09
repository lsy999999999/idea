# Literature Search and Overlap Audit

Retrieved 2026-11-03 from public OpenAlex, Crossref, and Europe PMC APIs. This is a focused scoping search, not a systematic review. Searches used title/metadata and indexed abstracts; no full-text review or citation-chaining was completed.

## Closest records

1. **Automatic and Precise Data Validation for Machine Learning**, CIKM 2023, DOI [10.1145/3583780.3614786](https://doi.org/10.1145/3583780.3614786). OpenAlex record `W4387848581`; Crossref verified title, date (2023-10-21), and proceedings. Its indexed abstract describes partition summaries and a validation system (`gate`) intended to improve precision while finding corrupted data partitions in retraining pipelines. This directly overlaps automatic selection/operation of data checks and the false-positive/cost motivation. It does not, based on the abstract reviewed, establish the proposed workflow transformation-lineage state.
2. **PALADIN: A process-based constraint language for data validation**, *Information Fusion* 2024, DOI [10.1016/j.inffus.2024.102557](https://doi.org/10.1016/j.inffus.2024.102557). OpenAlex record `W4400336961`; Crossref verified title, date (2024-12), journal, and authors. Its indexed abstract describes constraints that vary across process stages, cross-stage data inconsistency checks, and evaluation on 20 datasets (18 synthetic) / 53 testbeds. This is a close match to the proposed multi-stage synthetic pipeline setting and already establishes process-state-aware validation as an existing area. It is not described in the abstract as adaptively selecting which check to execute.
3. **Adaptive test case selection for DNN-based perception functions**, IEEE ISSE 2021, DOI [10.1109/ISSE51541.2021.9582499](https://doi.org/10.1109/ISSE51541.2021.9582499). OpenAlex record `W3210250788`; Crossref verified title, date (2021-09-13), and venue. The indexed abstract describes risk-oriented adaptive selection among synthetic test cases under a compute budget and reports earlier fault detection. This is an adjacent domain, but it overlaps the core general move of allocating limited validation effort according to estimated risk.

The older **TensorFlow Data Validation: Data Analysis and Validation in Continuous ML Pipelines**, KDD 2020, DOI [10.1145/3318464.3384707](https://doi.org/10.1145/3318464.3384707), is another useful baseline for pipeline checks, schema inference, and distribution/skew monitoring. It is background rather than one of the three closest recent works.

## Queries and source behavior

- OpenAlex Works search `"data validation" adaptive`, filtered from 2020, top 50: surfaced the 2023 CIKM paper and several broad/noisy items. Search `"PALADIN" data validation constraint` surfaced the 2024 process-constraint paper.
- OpenAlex Works search `data validation risk adaptive testing pipeline`, filtered from 2020, top 50: surfaced the 2021 adaptive DNN test-selection paper, but also many unrelated or low-relevance engineering records. Do not use raw rank as a relevance assessment.
- Crossref title queries independently verified DOI, title, date, and venue for the three records above. OpenAlex indexed abstracts were inspected for those works.
- Europe PMC query over data validation with adaptive/provenance/workflow terms returned mostly biomedical and otherwise unrelated records; it was not a useful source for this computer-systems question.

## What the search supports

The proposed first topic is **not novel at the level currently phrased**. Process-aware validation, automated ML data validation, and risk-adaptive test selection each pre-exist. The searched records do not by themselves settle whether workflow transformation lineage plus independently checkable invariants provide a useful risk state beyond existing partition summaries, anomaly scores, static constraint priorities, and adaptive test-selection policies. That narrower intersection needs targeted review and direct baselines before a contribution claim.

Suggested narrower question: *At equal validation cost, do transformation lineage and invariant availability improve early detection of held-out silent fault types beyond data-anomaly summaries and fixed risk rankings, especially when a fault preserves plausible downstream distributions?* Define the state and check-selection rule before generation; compare cost-matched policies; vary whether lineage/invariants are informative or deliberately uninformative. This tests whether the proposed `y` adds information rather than only whether an adaptive policy beats a weak fixed-check baseline. Treat it as a hypothesis to investigate, not as established novelty.

## Exploration versus audit load

The protocol has useful protections against post-hoc claims, but applying the full ledger, source verification, baseline, explicit falsifier, and stopping logic to every early idea could make exploration bureaucratic. Keep early exploration cheap: capture only the boundary observation, candidate `y`, one cross-domain pointer or analogy, and one next discriminating action. Promote a candidate to the full evidence ledger only when a testable contrast exists. Allow speculative branches and quick throwaway calculations without acceptance labels. Apply full baselines and replication to the one or two candidates selected for focused testing. Put a small budget on each early branch so skeptical review informs exploration instead of blocking it.

