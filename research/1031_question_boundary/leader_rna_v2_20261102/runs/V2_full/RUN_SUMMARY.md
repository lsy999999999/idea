# V2 Full Run Summary

## Question and Candidate

Selected candidate C1 asks whether transcription-driven accumulation of connected RNA loop-junction load can outrun network relaxation, cross an effective threshold, and trap internal solvent-rich domains. This is a new, unconfirmed hypothesis (H1/H1a), not an evidence-established explanation.

The reduced model is
`dx/dt = alpha*r - x/tau`, with dimensionless effective load `x`, production rate `r` in h^-1, and relaxation time `tau` in h. Before arrest, `dq/dt = k_n max(x-x_c,0) - k_d q`; after the first upward crossing of `x_c`, the model imposes `dq/dt=0`. The post-threshold freeze and mapping from `q` to segmented area fraction are stipulated assumptions.

## Actual Results

- E0 shows similar initial segmented empty-area fractions (A 0.01487, B 0.01381) and a 24 h contrast (A 0.00446, B 0.08918). These are image area fractions, not concentration or free energy; fields are nested within two preparations.
- R1 returned four abstracts. R1_S1 supports exchange-dependent kinetic arrest in a different simulated sticker-spacer condensate system. R1_S3 describes protein LARKS percolation/gel-like trapping. Neither establishes the target RNA mechanism.
- E1 tracking summaries are ambiguous: B tracks are shorter and have a large selected displacement tail. They do not show uniform cavity immobilization.
- R2 returned zero sources; this is a retrieval result, not a biological negative.
- R3 returned five abstracts. R3_S3 reports a specific RNA-RNA kissing-loop interaction contributing to oskar RNP granule assembly with Bruno scaffold. This supports architectural plausibility in another system, not target exchange kinetics, transcription coupling, or cavities.
- E2 phase concentrations vary across reference/variant series, but no metadata maps those series to A/B or cavity state.
- C3 executed successfully. For `alpha=1`, `tau=5 h`, `x_c=0.5`, and equal integrated `r=1`, a fast schedule (`0.2 h^-1`, 5 h) crosses at 3.466 h and ends at `x=0.6321`; a slow schedule (`0.05 h^-1`, 20 h) ends at `x=0.2454` without crossing. Sensitivity shows this discriminator is parameter-dependent: at `tau=1 h` none of tested `alpha=.5,1,2` cross; at `tau=20 h, alpha=1`, both schedules cross. The computation is conditional, not a fit.
- E3 reports reference DNA read fraction 0.9466 and four listed other classes totaling 0.0500; the listed sum is 0.9966, leaving 0.0034 unitemized. Provenance and sequencing pipeline are unknown. These are DNA reads and do not establish transcript fractions or RNA concentrations.
- R4 included a phage-display library amplification analogy, confounded by biological propagation/selection. R5_S1 reports primer mismatch-dependent bias in controlled PCR; R5_S2 reports enzyme-dependent coverage and size/GC bias in NGS-library amplification. These sources make assay bias plausible in principle but do not establish the target protocol.
- E4 field medians are M 0.0000279 (n=3), M+L 0.04446 (n=5), M+S 0.09412 (n=2). Category semantics, fraction values, A/B mapping, and independent preparation structure are missing; this is descriptive only.

## Prediction and Limits

Committed held-out prediction: conditional on B having crossed the model threshold by 24 h, its segmented area fraction remains above A at 36 and 48 h, with a smaller 24-48 h increase than its 12-24 h increase. The held-out values were not present in this run, so the prediction is unscored.

H2, equilibrium composition-driven demixing after matched composition/equilibration, remains a meaningful alternative. Amplification-related DNA differences, reaction carryover, and measurement/selection effects also remain unresolved. G1 (target-compatible kinetics/arrest), G2 (amplification and template provenance), and G3 (phase/cavity mapping) remain open. No DNA read frequency was converted to RNA abundance. No target-study recognition or target-derived literature was used.

The executor's dissent: C3 is a valid model consequence but not evidence for H1. E4's apparent group differences cannot support a causal claim with undefined labels, small unequal field counts, and no independent replication. The held-out forecast is unscored.

## Run Counters

Logical actor replies: 12 (L1,R1,L2,R2,L3,R3,L4,R4,L5,R5,R6,L6). Search: 5/6. Compute: 1/10. Evidence requests: 4/4. No searches remain pending.

This V2 full run used the autonomous runtime handoff and should not be described as equal inference budget, token count, or provider identity relative to another run.
