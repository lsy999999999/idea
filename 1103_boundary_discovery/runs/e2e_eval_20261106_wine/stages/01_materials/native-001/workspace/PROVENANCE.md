# Provenance

- Retrieval date: 2026-11-06 (Asia/Shanghai).
- Dataset archive: https://archive.ics.uci.edu/static/public/186/wine+quality.zip; downloaded as `data/wine_quality.zip`. SHA-256: `3ed56667f4b828242bd732d7d1dd7f2861e54432239d7fa63877014cbb0304d4`.
- Dataset description: https://archive.ics.uci.edu/dataset/186/wine+quality; `data/winequality.names` is included in the archive. It identifies Cortez et al. 2009 and describes measurements, rows, attributes and score construction.
- Original study DOI: https://doi.org/10.1016/j.dss.2009.05.016. Crossref metadata saved in `sources/cortez_crossref.json`; no abstract was present. The UCI-listed preprint URL was attempted, but no PDF was retrieved. `sources/original_study_excerpt.txt` clearly attributes its summary to UCI rather than presenting it as paper text.
- Sensory foundation/review search: Crossref query result saved as `sources/review_search_crossref.json`; no relevant accessible review abstract was found within this bounded pass. `sources/sensory_foundation_excerpt.txt` uses retrieved UCI dataset documentation as a foundation source and is explicitly not called an independent review.
- Network access initially failed DNS in the sandbox; public URL access succeeded after escalation for the archive and Crossref. The preprint host did not complete.
- Run `python3 audit_dataset.py` in this workspace to reproduce row/column/missingness/range/hash checks; output saved in `data_audit.txt`.
