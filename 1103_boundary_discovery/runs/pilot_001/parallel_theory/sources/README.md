# Literature and Source Records

Retrieved on 2026-11-03 for a focused scoping search; this is not a systematic review. Raw public API responses are preserved here.

## Literature records

1. Fogg, Reinhold, O'Daniel, Hyman, and Poole (2023), “Thermal insulation versus capacitance: A simulation experiment comparing effects of shade and hyporheic exchange on daily and seasonal stream temperature cycles,” *Hydrological Processes*. DOI: [10.1002/hyp.14973](https://doi.org/10.1002/hyp.14973). Crossref metadata and abstract are in `crossref_thermal_insulation_capacitance.json`. This is the closest conceptual match: the authors distinguish mechanisms that can both damp a daily cycle but differ seasonally. “Thermal capacitance” is already an established construct; the proposal does not claim it as new.
2. Leach, Kelleher, Kurylyk, Moore, and Neilson (2023), “A primer on stream temperature processes,” *WIREs Water*. DOI: [10.1002/wat2.1643](https://doi.org/10.1002/wat2.1643). Crossref metadata and abstract are in `crossref_stream_temperature_primer.json`. It frames stream temperature through water/energy balance, including advection and stream-atmosphere and stream-bed exchange.
3. García Molinos, Nobuo, Sueyoshi, and Nakamura (2022), “Timescale mediates the effects of environmental controls on water temperature in mid- to low-order streams,” *Scientific Reports*. DOI: [10.1038/s41598-022-16318-9](https://doi.org/10.1038/s41598-022-16318-9). Crossref metadata and abstract are in `crossref_stream_temperature_timescale.json`. Its 130-station, four-year daily/monthly comparison supports treating temporal aggregation as part of the estimand.
4. Toffaletti et al. (2019), “SESTET: A spatially explicit stream temperature model based on equilibrium temperature,” *Hydrological Processes*. DOI: [10.1002/hyp.13591](https://doi.org/10.1002/hyp.13591). It appeared in the OpenAlex search response `openalex_diel_stream_temperature.json`; use it as an established process-model entry point, not a claim of novelty.

## Search provenance

- `openalex_diel_stream_temperature.json`: OpenAlex Works API query `search=stream temperature diel range groundwater discharge`, filtered to publication date 2018 onward, top 30. The ranked result includes the 2023 primer, 2023 insulation/capacitance paper, 2022 timescale paper, and SESTET.
- `crossref_thermal_insulation_capacitance.json`: Crossref title query for the insulation/capacitance paper, top five. DOI/title/date/journal/authors and abstract match.
- `crossref_stream_temperature_primer.json`: Crossref lookup by DOI `10.1002/wat2.1643`, including abstract and authors.
- `crossref_stream_temperature_timescale.json`: Crossref title query for the timescale paper, top three. DOI/title/date/journal/authors and abstract match.

The search is deliberately small. Daily stream-temperature ranges, diel harmonics, thermal storage, hyporheic exchange, and time-scale dependence are established topics. Any contribution would need to be a carefully bounded test of the specific transfer relation in these paired USGS/NOAA data, not a renamed physical concept.

