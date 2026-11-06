# Fresh continuation: wine ratings

## Retrieved memory used

- `wine_quality_estimand_boundary` v3, from `e2e_eval_20261106_wine`: aggregate-median prediction, absolute panel agreement, relative ranking, variance-source analysis, and construct validity are different targets. The note explicitly leaves a suitable ordinal statistic for three or more judges unresolved.
- `linked_panel_rating_design` v1, from `e2e_eval_20261106_wine`: retaining judge and wine IDs, with shared wines rated by the same judges, can help separate judge and sample effects. This design condition alone does not identify every interaction or establish construct validity.

## Continuation question

For a panel of at least three judges giving ordinal scores, what rating design and model can distinguish systematic judge severity from wine differences and judge-by-wine interaction, especially when the panel is incompletely crossed? The saved notes make clear why aggregate-median prediction and agreement are separate estimands, but they do not specify a suitable multi-rater ordinal coefficient or the replication needed for these components.

## Worked example (hypothetical)

Suppose three judges rate the same three wines on an ordinal 1–5 scale:

| Wine | Judge A | Judge B | Judge C | Median |
|---|---:|---:|---:|---:|
| X | 2 | 1 | 2 | 2 |
| Y | 3 | 2 | 3 | 3 |
| Z | 5 | 4 | 5 | 5 |

All three judges rank Z above Y above X, so their relative ordering agrees in this small example. Judge B is one point lower on every wine, so exact absolute agreement is absent for every wine even though the ranking is shared. The medians retain an aggregate ordering but erase which judge supplied the lower scores. This applies the saved agreement-versus-consistency distinction and shows why judge IDs matter for the severity question. It is a teaching example, not UCI data, a fitted model, or evidence that the one-point pattern is a real judge effect.

## Remaining gap

The example cannot tell whether a real panel's differences reflect stable judge severity, wine-by-judge interaction, or ordinal-scale behavior. The next useful step is to specify the intended estimand (absolute interchangeability, rank consistency, or variance attribution), then consult methods for multi-rater ordinal ratings under the actual crossing and repetition pattern. The supplied UCI table contains only aggregate medians, so it cannot answer judge-level questions. No novelty or empirical validation claim follows from this continuation.
