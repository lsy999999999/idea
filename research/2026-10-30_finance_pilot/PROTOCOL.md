# Financial pilot protocol

Written before running the experiments. Date: 2026-10-30.

## Scope

These are offline data/retrieval baseline experiments. No LLM API or local model is configured in the current execution environment. Do not describe these results as an LLM/agent comparison, an audit fraud detector, or a clinical/financial outcome study.

Use the previously downloaded Apple and Microsoft SEC Company Facts snapshots and all 883 FinQA development records. Record SHA-256 hashes. Freeze SEC visibility at 2026-10-30. No parameter search or model training.

## Experiment 1: historical disclosure lookup

- Include US-GAAP facts filed as 10-K or 10-K/A. Include instant facts and duration facts spanning 300–400 days; exclude shorter quarterly periods and invalid dates. Group by company, tag, unit, start and end.
- Require at least two distinct filing dates. Exclude groups with differing values within the same filing date because date-only metadata cannot disambiguate them. Report exclusions.
- Query checkpoints: first filing date, middle distinct filing date, and 2026-10-30; deduplicate checkpoints. Same-day data is treated as available at end of day; no intraday claim.
- Generate reference answers by chronological replay. At each checkpoint, use the last then-visible disclosure. These are snapshot-derived labels, not independently verified archival ground truth.
- Compare earliest-disclosure lookup, latest-disclosure lookup, mode-value lookup (with latest supporting citation), and exact-key cutoff-filtered lookup. All receive the same snapshot and structured query fields. This isolates date handling, not metric-language understanding.
- Score numeric equality with very tight floating tolerance, citation filing date <= cutoff, and joint correct value/valid citation. Track changed and unchanged groups separately; report company-level and pooled results.
- The cutoff-filtered rule is a deterministic reference implementation. Perfect performance would be a consistency check, not a novel research contribution.

## Experiment 2: evidence retrieval on FinQA development data

- Build each local corpus only from `pre_text`, `post_text`, and `table`. Text IDs concatenate pre/post text; table rows carry column headers. Do not expose answers, gold evidence, programs, retrieved passages, or other dataset-provided retrieval outputs to retrieval methods.
- Question is the only query. Compare seeded random ranking, BM25, and a fixed BM25 pseudo-relevance-feedback baseline (top result, six new nonnumeric terms, weight 0.30). BM25 k1=1.5, b=0.75. Fixed simple tokenizer and stopword list, no tuning.
- Budgets k=1,3,5,8,12 chunks. Measure annotated-evidence macro recall, complete annotated-evidence coverage, and average returned words. Gold labels are used only by the scorer, after ranking.
- Report unresolvable gold IDs explicitly. Treat exact annotated-evidence coverage as a retrieval metric, not answer accuracy or proof of semantic completeness. Equivalent unannotated evidence may exist.
- This is within-page/table retrieval on a development set, not full-report retrieval or a held-out benchmark claim. Report unique source-page counts and results for one versus multiple annotated evidence pieces.

## Diagnostic 3: split-compatible candidates

Use the already downloaded Apple 2020 four-for-one split announcement and exact per-share tags. Identify historical periods with values on both sides of 2020-08-31 whose transition is numerically compatible with dividing by four. Report these only as candidates requiring the actual accounting note; do not label all value changes as errors or restatements.

## Verification and decisions

Test boundary cases for future evidence, same value with future citation, ambiguous same-day values, and corpus/gold separation. Preserve row-level outputs and input hashes. Show failures and negative results. Decide whether the next step should be better evidence acquisition or an LLM experiment, based on actual findings.

## Post-hoc addition after the initial run

Measure the size of the entire supplied FinQA context (the same serialized corpus, whitespace-delimited words), and verify whether returning every chunk covers all annotated evidence. Use nearest-rank p95. This checks whether chunk retrieval creates an artificial bottleneck when a full-context model baseline is practical. It is not answer-accuracy evaluation. Added a direct same-day ambiguity fixture to the implementation; primary retrieval parameters and endpoints remain unchanged.
