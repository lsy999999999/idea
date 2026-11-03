# 隐藏组名的语义复核规则

This is a pre-specified evaluation of research candidates. You are not the generator. Use only the supplied records. Do not use tools, files, memory, network or external papers. Record what the evidence permits. Return JSON directly, with no markdown. No private reasoning trace is requested.

The records are shuffled and have opaque ids. Do not infer or reward the method, verbosity, apparent sophistication or family names proposed by a generator. Assign your own coarse semantic families jointly across ALL records in this task. Same core question with a new name, threshold, model, routine subgroup or time window remains the same family. A different intervention/comparison or scientific relation may be a different family if its central discriminating prediction changes. Same-family refinements can be useful: record them separately rather than dismissing them. Do not force everything with the same outcome into one family. Initial and final variants often belong together.

Judge candidate quality by four criteria: specific question/action, falsifiable contrast, coherent measurement/logic, feasible research plan with explicit necessary measurements. Current data need not settle the question, but a vague wish to collect unspecified new data is insufficient. Generic feature selection, fit-a-better-model or merely repeating a limitation in the dataset documentation is insufficient input increment. Existing conventional methods can form testable proposals, but do not count as established literature originality.

For final records, additionally inspect the actual tool request/code/output and final evidence claim. A code exit 0 is not scientific validation. Check if code computes the stated contrast, correct unit/independent sample, direction, temporal availability, target leakage, sample selection and causal scope. A computed feasibility count does not support an effect. A revised but uncomputed question may remain a useful proposal; it cannot inherit empirical support for a different question. Negative findings and correct withdrawals are useful evidence updates. Do not count withdrawn/blocked/null final candidates as delivered usable final ideas.

Main judgement usable_final requires a valid concrete final candidate AND no material mismatch between its claimed evidence status and actual evidence. A proposal-only final can pass when the plan is feasible and correctly labeled. A scientifically invalid evidence claim can fail even if the question itself is interesting. Report both proposal_quality and usable_final.

This review does not establish literature novelty or real-world causal effects. Do not penalize honest uncertainty. Do not invent statistical or code errors. If an issue cannot be settled from supplied records, label needs_check and state the exact unresolved issue.

Return JSON with:
- families: [{family_id, label, core_definition, boundary_rationale}]
- records: exactly one entry per opaque input id, each {id,family_id,criteria:{specific:boolean,falsifiable:boolean,coherent:boolean,feasible:boolean,input_increment:boolean},proposal_quality:boolean,usable_final:boolean|null,material_acceptance_error:boolean,error_type:string,reason:string,needs_check:string}.
- cross_record_observations: concise facts about repeated families and meaningful refinements without guessing strategies.

Every candidate id must occur exactly once; every family_id must exist. For a null final use family_id NONE, proposal_quality false, usable_final false, and define NONE. Explanations may be in Chinese. Limit each record's reason to around 45 English words or comparable Chinese length.
