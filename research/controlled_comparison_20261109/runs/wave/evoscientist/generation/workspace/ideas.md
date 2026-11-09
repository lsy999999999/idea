# Follow-up Ideas: Coarsening, Shear, and Alternative Explanations

## Evidence boundary

Only `/dossier.json` and `/measurements.csv` are treated as scientific evidence. The visible source paper is identified in the dossier and already discusses spatial coarsening; this note does not claim to rediscover that result. The supplied CSV has 2,199 sequential samples at 300 Hz from one exported aggregate trajectory of a 111-unit two-dimensional array, spanning 7.3267 s. These are not independent runs. No unit-resolved trajectories, replicate identifiers, unit coordinates, or derivation details for the small `width_ste_export` are supplied.

The observed `correlation_width` is a spatial correlation-length proxy. The normalized inverse column is the source notebook normalization `fwhm[1]/fwhm`, not an independently fitted inverse length or exponent. It is infinite where width is zero (five rows); those values cannot be interpreted as infinite physical wave number. `width_ste_export` is zero in the last portion and its aggregation/independence semantics are unspecified, so it is not a dependable confidence interval.

## Descriptive cues in the supplied measurements

- Samples are evenly spaced by 1/300 s, timestamps increase monotonically, and no fields have missing entries.
- Coarse one-second summaries show width rising from a mean near 2.1 in the first second to about 10.7 by the third second; later one-second means remain broadly elevated, around 11-13, with substantial within-window fluctuations.
- Mean shear rises from about 0.046 at the first sample to a higher band early; its one-second mean is around 0.175-0.180 for most of the interval after the first second.
- The all-sample correlation between width and shear is about 0.55. This is descriptive only: common time trends and serial dependence can induce it, so it does not establish coupling or causal ordering.
- The trajectory supports asking why apparent spatial organization grows while mean shear later changes little. It cannot establish a mechanism, a population effect, or a universal scaling law.

## Competing explanatory hypotheses

### H1: Coupling-mediated growth of spatial coordination

**Question:** Does strengthening spatial dependence among nearby units contribute to the increase in correlation width?

**Mechanism proposal:** Local interactions could progressively align or entrain neighboring units, producing a larger characteristic spatial scale. The aggregate time series is consistent with this possibility but does not directly observe inter-unit influence or propagation.

**Discriminating prediction:** Unit-resolved data should show distance-structured correlations or lagged propagation that grows with time, and this structure should survive removal of a common temporal component. Spatial permutation or appropriate time-preserving surrogates should weaken it.

**Conditional consequence:** If local, distance-dependent and lagged structure strengthens robustly, a coupling-mediated account gains support. If the width rise disappears after common-mode adjustment, coupling alone is insufficient. Without unit-level data, the claim remains untested.

### H2: Shared drive or common relaxation

**Question:** Could a global time-varying drive, startup transient, or relaxation process jointly account for early shear increase and width change?

**Mechanism proposal:** A common input can change aggregate amplitude and apparent spatial statistics without one unit progressively causing its neighbors to coordinate. A single common transient could produce temporal co-movement and a positive raw association.

**Discriminating prediction:** A common-mode estimate from unit-level signals should explain appreciable temporal change; conditioning on it should substantially reduce the apparent growth in width or its association with shear. Altering drive while holding coupling/configuration fixed should shift the transient if this account dominates.

**Conditional consequence:** Strong attenuation after common-mode removal would favor shared drive/relaxation as a major contributor, while leaving room for residual interactions. No drive record or unit series is supplied, so aggregate co-movement cannot choose this account.

### H3: Finite-size limitation or approach to a bounded late regime

**Question:** Does the late high width approach the array's resolvable spatial extent or a plateau rather than continuing to grow freely?

**Mechanism proposal:** In a finite array, correlation length estimates can become bounded by geometry or estimator support. Late fluctuations around a high level could therefore reflect saturation, finite-size sensitivity, or changing uncertainty rather than sustained coarsening.

**Discriminating prediction:** Compare the estimated width with the array's effective span and estimator maximum. A size-limited account predicts late values near that bound and sensitivity to array size; a genuine plateau should remain after window and boundary choices are varied.

**Conditional consequence:** If width nears the measurement or system-size ceiling, late changes should not be read as unbounded growth. A single array cannot establish finite-size scaling; arrays of different sizes or a validated estimator bound are needed.

### H4: Estimator, aggregation, or nonstationarity artifact

**Question:** How much of the apparent trend depends on how the trajectory is pooled and correlation width is estimated?

**Mechanism proposal:** Nonstationary signals pooled over time, finite observation windows, spatial boundaries, or changing image/measurement quality could alter the correlation-width estimate. The supplied export does not provide enough method detail to rule these out.

**Discriminating prediction:** Re-estimation under defensible windowing, detrending, boundary handling, and aggregation choices should preserve the principal pattern if it is robust. Surrogates preserving temporal autocorrelation/common trend but disrupting relevant spatial structure should not reproduce spatial signatures under a genuine interaction account.

**Conditional consequence:** Strong dependence on analysis choices or reproduction by suitable surrogates would downgrade mechanistic interpretation and prioritize measurement validation. Robustness across estimators would reduce, but not eliminate, this alternative.

## Concrete follow-up questions

1. Does the early increase in correlation width persist in per-unit spatial correlation after subtracting global/common-mode motion?
2. Is there a directional or lagged propagation signature, or only simultaneous common movement?
3. Does width approach a bound set by array geometry or by the correlation estimator?
4. Are early width growth and shear increase reproducible across independent runs, or peculiar to this aggregate trajectory?
5. Which conclusions survive alternative time windows, detrending, edge handling, and treatment of zero-width samples?
6. Do controlled changes to drive and coupling yield the distinct responses predicted by H1 and H2?

## Minimal discriminating work, conditional on data availability

- First recover and document the exact correlation-width definition, boundary handling, aggregation, and meaning of `width_ste_export`; plot width and shear against time without treating frames as independent replicates.
- If unit-resolved signals and coordinates exist, compare early and late distance-dependent and lagged correlations, before and after common-mode adjustment, with spatial/time-preserving controls.
- If repeats exist, report run-level trajectories and uncertainty across runs; do not use 2,199 frames as the sample size for population inference.
- If the apparatus permits interventions, vary global drive while holding coupling fixed, and vary coupling while holding drive fixed. Preserve other settings and replicate each condition. State predictions before inspecting outcomes.
- If only the current aggregate export is available, restrict inference to descriptive trend and robustness analyses; mechanisms remain unresolved.

## What these measurements can and cannot establish

**Can establish:** the values and temporal pattern in this supplied aggregate export; regular sampling and absence of missing cells; that width is relatively low early and broadly higher later; that mean shear rises early and is comparatively stable afterward; and that the two raw series co-vary descriptively over this one trajectory.

**Cannot establish:** independent replication, statistical significance across systems, causal direction, unit-to-unit interactions, wave propagation, whether shear drives coarsening or vice versa, the cause of the late regime, universal power-law scaling, or absence of measurement artifacts. The uncertainty export cannot repair these limits because its construction is not described and it becomes zero late. No conclusion should be generalized beyond this trace without additional evidence.
