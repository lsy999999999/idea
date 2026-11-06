# Research Scout: Boundary Discovery (2026-11-03)

## Scope and method

This is a short, public-source scout, not a novelty determination or a result. I searched OpenAlex's public works API and checked live data endpoints on 2026-11-03. The two retained directions have concrete, inspectable time series and modest-compute first tests. Searches and access checks are recorded below; the API results are search leads, not systematic reviews. No large dataset was downloaded and no hypothesis was tested.

## 1. Stream-temperature recovery after heat events (recommended first)

**Question.** For stream reaches with comparable day-of-year, air-temperature forcing, and discharge, does the observed water-temperature recovery trajectory after one hot episode improve a forecast of the next episode's peak and duration above a fixed thermal threshold at held-out reaches? Compare it against a baseline with the same forcing, discharge, recent maxima, and cumulative heat exposure. This asks whether event order and the measured recovery response contain out-of-site predictive information; it does not assume groundwater is the cause.

**Explanatory gap.** River heatwave occurrence, trends, and predictive models are already studied. A narrower gap worth checking is whether event-to-event thermal recovery carries transportable information beyond common meteorological and flow covariates, and whether that information survives a site holdout. Plausible physical contributors include thermal storage, groundwater exchange, riparian shade, and channel form, but this dataset alone cannot identify which one caused a signal.

**Potential cross-domain bridge.** Pulse-and-relaxation response is studied in materials and control systems. A transfer would be methodological: test whether a measured relaxation curve is a portable state descriptor under repeated forcing. It would not establish that river and material mechanisms are the same.

**Data and feasibility.** USGS Water Services exposes machine-readable instantaneous values. A request for active Oregon stream-temperature stations returned 350 station records. A request for 2020-07-01 through 2020-07-03 returned 288 readings at each of USGS 10396000 (Donner und Blitzen River), 11501000 (Sprague River), and 11502500 (Williamson River below Sprague River). Rechecking the saved response showed 15-minute spacing, not five-minute spacing: each series covers 2020-07-01 00:00 through 2020-07-03 23:45 in the station's -07:00 timezone, with no duplicate times or missing 15-minute intervals. The 288 observations therefore match the requested three-day window and do not indicate truncation. The response had `Cache-Control: max-age=900` but no `Age`, `Via`, or cache-hit header; the body includes a fresh USGS request timestamp and request ID, although headers alone cannot rule out every intermediary cache. Example multi-station request: <https://waterservices.usgs.gov/nwis/iv/?format=json&sites=10396000%2C11501000%2C11502500&parameterCd=00010&startDT=2020-07-01&endDT=2020-07-03>. Station metadata can be queried at <https://waterservices.usgs.gov/nwis/site/?format=rdb&stateCd=OR&parameterCd=00010&siteType=ST&siteStatus=active>. Raw response, response headers, request URL, hash, and coverage audit are in `bootstrap/scout/evidence/`.

**Runnable first test.** Pull a predeclared set of stations and years; retain records with documented coverage; build event windows using a threshold defined from training years only; estimate cooling/recovery features on an earlier episode; predict the next episode's peak and duration. Compare (a) seasonal/air-temperature/discharge baseline, (b) baseline plus ordinary recent maxima and cumulative heat, and (c) baseline plus recovery-curve features. Evaluate forward in time and leave entire stations out; report calibration and uncertainty, not only pooled error. Check sensor gaps, rating/site metadata, event overlap, and station selection. A laptop can process the initial station subset.

**Closest work found (not exhaustive).**

- “Increasing heatwave frequency in streams and rivers of the United States” (2022), DOI <https://doi.org/10.1002/lol2.10284>.
- “Riverine heatwaves are an emergent climate change risk” (2025), DOI <https://doi.org/10.1038/s44221-025-00541-5>.
- “Exploring the exceptional performance of a deep learning stream temperature model and the value of streamflow data” (2020), DOI <https://doi.org/10.1088/1748-9326/abd501>.
- “Nocturnal river water temperatures: Spatial and temporal variations” (2014), DOI <https://doi.org/10.1016/j.scitotenv.2014.02.123>.
- A focused OpenAlex search also surfaced “Hysteresis and Longitudinal Variation in Air–Water Temperature Relationships in the Han River Basin” (2026), DOI <https://doi.org/10.3390/w18091013>. Its apparent closeness makes a targeted full-text check important before claiming any gap.

**Originality and claim risk.** High risk: lag, hysteresis, groundwater buffering, and river heatwaves are established topics, and a recovery feature may be a repackaging of known thermal inertia. The potentially useful contribution would be a strict sequential, out-of-station test against strong matched-forcing baselines, if the nearest literature has not already done that exact test. Even a positive forecast result would not by itself establish a new physical mechanism.

## 2. GOES soft-X-ray background and flare-event timing (exploratory backup)

**Question.** Within the same GOES platform and solar-cycle interval, does the pre-event background and decay/recovery shape add stable lead-time information about the next catalogued flare's class beyond recent peak flux and event cadence, when evaluation is split chronologically? A later independent check would need another satellite era, because GOES-15 alone is not an independent instrument validation.

**Explanatory gap.** Flare forecasting and precursor signals are mature areas. The scout's narrower possible angle is whether event-history and background-relaxation information retain incremental forecast value under strict temporal separation and a calibrated rare-event baseline. It is not evidence for a novel flare state or trigger.

**Potential cross-domain bridge.** The same pulse/recovery analysis used in the stream candidate could be applied to a driven event series, with the important caveat that the sensors and underlying physics differ. A bridge is only justified if an invariant forecast relation survives separate tests in both domains.

**Data and feasibility.** NOAA NCEI's GOES-15 XRS directory lists yearly 1-minute science-quality NetCDF files (2010–2020) and yearly flare-summary NetCDF files. On 2026-11-03, I read the first 512 bytes of the 2012 XRS 1-minute file; the server returned HTTP 206 and the HDF5/NetCDF signature. File URL: <https://www.ncei.noaa.gov/data/goes-space-environment-monitor/access/science/xrs/goes15/xrsf-l2-avg1m_science/sci_xrsf-l2-avg1m_g15_y2012_v2-2-1.nc>. Event-summary directory: <https://www.ncei.noaa.gov/data/goes-space-environment-monitor/access/science/xrs/goes15/xrsf-l2-flsum_science/>. Limits: older instrument era only, instrument changes and data-quality flags require care, and event-level flux is not active-region-resolved.

**Runnable first test.** Download one year and its event-summary file, inspect variables/quality flags, then construct event-free intervals and predict fixed-horizon event onset or class. Split by time (not random rows), keep an untouched final year, compare with a persistence/cadence baseline, and assess class imbalance, calibration, and lead-time utility. Do not tune event windows on the final period.

**Closest work found.**

- “A DEFT Way to Forecast Solar Flares” (2021), DOI <https://doi.org/10.3847/1538-4357/ac2840>.
- “Improving Solar Flare Nowcasting with the Hot Onset Precursor Event Technique” (2025), DOI <https://doi.org/10.3847/1538-4357/ae0705>.
- “How to Train Your Flare Prediction Model: Revisiting Robust Sampling of Rare Events” (2021), DOI <https://doi.org/10.3847/1538-4365/abec88>.
- OpenAlex also returned a 2026 multimodal forecasting dataset paper, “Solar Situation Awareness and Flare Forecasting Dataset for Operational Applications,” DOI <https://doi.org/10.1038/s41597-026-08005-5>.

**Originality and claim risk.** Very high. Both precursor timing and X-ray nowcasting are active research areas, including a 2025 precursor technique and 2026 data/forecasting work. This direction is suitable only as a quick feasibility/protocol exercise unless a full-text search identifies a sharply unstudied event-history estimand. Single-platform results cannot support cross-instrument generalization.

## Disposition

Start with the stream test if the goal is a usable same-day computation: its API returns real multi-site measurements directly and permits a clean station holdout. Before interpreting any gain as a research contribution, check the 2026 Han River hysteresis work and the 2025 riverine-heatwave paper in full text. If they already test the proposed estimand, discard or substantially revise the question. Solar flare work is a lower-priority backup because the closest literature is dense.

I checked, but did not retain, lithium-battery cycling as a candidate. OpenAlex returned papers explicitly titled “Path Dependence of Battery Degradation” (2018 and 2019) and a 2025 paper “Degradation path prediction of lithium-ion batteries under dynamic operating sequences”; the queried Harvard Dataverse dataset API returned HTTP 403, and the NASA page redirected to a repository landing page rather than a confirmed raw-file download. It fails this scout's combined novelty and source-verification bar.
