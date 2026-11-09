# Continuation: Test Whether Condition Normalization Removes Aging Signal

## Revised assumption
The original direction assumes that temperature/SOC effects can be separated from persistent aging information through condition normalization while preserving useful mode-sensitive impedance structure. Revise that assumption: normalization may not be a separable preprocessing step at all. Temperature and SOC could interact with degradation mode, making the same physical aging change produce different impedance signatures across conditions; a condition-invariant representation might then suppress genuine aging information along with nuisance variation.

## Alternative research direction
Study the identifiability boundary between reversible operating-condition variation and persistent degradation in EIS. Rather than proposing normalization as the default, compare (1) raw impedance features with condition covariates, (2) condition-normalized features, and (3) a model with explicit condition-by-aging interactions. The primary question becomes: under which cells, aging trajectories, and held-out temperature/SOC ranges does condition correction help SOH estimation, and when does it erase or distort degradation evidence?

## Scientific consequence
This changes the central claim from seeking an estimator that integrates normalization and mode sensitivity to testing whether that decomposition is scientifically valid. A finding that interaction-aware modeling is needed would imply condition normalization is not generally safe and may bias SOH or degradation-mode inference. Conversely, comparable performance from a simpler normalized representation across held-out conditions would support treating condition effects as largely separable in the tested regime. Either outcome yields a falsifiable result about identifiability and generalization, rather than assuming the desired representation exists.

## Experimental implications
Use matched cells with reference capacity and EIS measured over controlled SOC and temperature points across documented aging trajectories. Split by cell or trajectory and hold out conditions; avoid spectrum-level random splits. Compare the three representations using SOH MAE/RMSE and uncertainty calibration, with mode diagnosis secondary and independently grounded. Include an interaction ablation and inspect errors by condition and aging protocol. The supplied materials provide no data or evidence resolving this question, so this is a proposed direction, not an empirical conclusion.

## Basis and limits
This continuation uses only `/memory/ideation-memory.md` and `/idea.md`. It follows their cautions that temperature/SOC affect EIS, degradation mechanisms may be non-identifiable, and abstract-level evidence does not establish performance or novelty. No online search was used.
