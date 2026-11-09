# Reusable Research Note: Single-Trajectory Spatial Coarsening Case

## Provenance and constraints

Use only the supplied `/dossier.json` and `/measurements.csv` as evidence. External browsing/downloads are disallowed for this case. The dossier identifies the source study and says its authors discuss spatial coarsening; do not present coarsening itself as a novel discovery. Do not train models or create synthetic replacement data. Computation must remain CPU-only, at most four threads, and within 120 seconds.

## Evidence summary

The export contains 2,199 uniformly spaced samples (300 Hz, 0-7.3267 s) from one aggregate trajectory of a 111-unit 2D mechatronic array. It is not 2,199 independent experiments. No repeated-run identifiers, per-unit time series, coordinates, or detailed uncertainty-generation method are provided in the supplied dossier. Data have no missing cells; the normalized inverse-correlation column is infinite at zero correlation width (five rows). The `width_ste_export` reaches exact zero throughout the final segment and cannot be assumed to be a valid standard error or confidence interval.

The correlation-width proxy rises strongly during the early portion (coarse one-second mean around 2.1 in the first second and around 10.7 in the third), then remains broadly elevated around 11-13 with fluctuations. Mean shear rises early and then is comparatively stable around 0.175-0.180 in coarse bins. Raw width-shear correlation is approximately 0.55 but is confounded by time trend and serial dependence; it is not causal evidence.

## Hypothesis discipline

Retain multiple explanations until discriminating evidence exists:

1. **Local interaction/coupling:** predicts strengthening distance-structured or lagged dependence after common-mode removal.
2. **Shared drive/startup relaxation:** predicts common temporal change; removing common-mode signal should attenuate apparent spatial growth or co-movement.
3. **Finite-size/estimator saturation:** predicts late width near array or estimator scale and dependence on array size/boundary choices.
4. **Aggregation, nonstationarity, or measurement artifact:** predicts sensitivity to pooling, detrending, windows, edge handling, or surrogate controls.

These are explanatory hypotheses, not results established by the aggregate CSV. State conditional consequences for each: what would favor it, what would weaken it, and what follow-up it motivates.

## Questions worth carrying forward

- Does early width growth survive adjustment for global/common-mode motion?
- Are there spatial distance and time-lag signatures of propagation, beyond synchronous aggregate behavior?
- Does late width approach a physical/estimator bound?
- Are patterns replicated across independent runs?
- Are they robust to reasonable alternative estimators and windows?
- What changes under separately controlled drive and coupling perturbations?

## Inference and reporting safeguards

- Distinguish source-paper claims, direct observations in this export, and proposed explanations.
- Treat the trace as descriptive; do not calculate frame-level p-values as if frames were independent replicates.
- Do not call the normalized reciprocal a fitted exponent or infer a scaling law from it.
- Treat zero-width inverse values as undefined for physical interpretation, not extreme observations.
- Do not use `width_ste_export` as inferential uncertainty until its aggregation and independence semantics are documented.
- If only aggregate values are available, conclusions stop at trend description and robustness; causal, spatial-interaction, population, and universal claims remain unestablished.
