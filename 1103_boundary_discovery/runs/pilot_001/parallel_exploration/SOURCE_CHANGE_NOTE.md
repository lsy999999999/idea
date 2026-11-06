# Exploration Script Version Trace

## Recovered input version

`versions/exploration.pre_predictions_2026-11-03T13-31-56Z.py` is a byte-for-byte copy of the script content captured in the r02 skeptic event log, item `item_7` (`sed -n '1,300p' .../parallel_exploration/exploration.py`). The captured output is 13,807 bytes. Its SHA-256 is `735b0517f71a4baa8ad3cbe73a13cd4540e5ed201ed88cd30f949442a962fd35`, matching the `exploration.py` input hash in `runs/pilot_001/manifest.json` for r02. This is an exact recovery, not a reconstruction from memory.

## Difference from the current script

The current `exploration.py` hash is `0daf43ed01c2740cea979e5281f89ab348a90b770f2b2d8872c790df2a59e802`. A unified diff against the recovered input shows only:

- Added `export_time_holdout_predictions(df)`, which fits the same baseline, air-range, and air-range-plus-low-flow models for `water_mean`, `water_range`, `water_max`, and `water_min` on 2014–2019 and writes the 2020–2024 row-level predictions to `heldout_predictions.csv`.
- Added one call to that export function after the low-flow feature is constructed.

No data parsing, quality filters, low-flow cutoff, feature definitions, train/test years, model specifications used for `numeric_results.json`, or panel-writing logic changed in this diff. The extra prediction fits do not overwrite `numeric_results.json` or `paired_daily_panel.csv`.

## Timing and artifact check

The manifest records r02's input snapshot at `2026-11-03T13:31:56Z`. The current script's filesystem modification time is `2026-11-03 21:32:44 CST` (`2026-11-03T13:32:44Z`). The event log preserves the original script bytes but not a write event timestamp, so the supported time window for this code addition is after the r02 input snapshot and no later than the current script's recorded mtime; its exact edit time is unavailable.

The current `numeric_results.json` SHA-256 is `8c1c8d351c9fcff22d304b93c313142e277d1b3fe10eb5476be2a6841200136b`, matching the r02 manifest input. The current `paired_daily_panel.csv` SHA-256 is `00344671e67c088de57a7cff146700fbdf950a53ba7f4b2418d1a30e49512fcb`, also matching the manifest. No other source, data, or report files were changed for this trace.
