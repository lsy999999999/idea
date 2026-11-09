## User

This is the beginning of a team meeting to discuss your research project. This is a meeting with the team lead, Principal Investigator, and the following team members: Domain Scientist, Dynamical and Statistical Physicist.

Here is context for this meeting:

[begin context 1]

{
  "case": "optical",
  "source": {
    "title": "Degree-of-polarization modulation for high-dimensional optical computing",
    "journal": "Nature",
    "published": "2026-08-12",
    "doi": "10.1038/s41586-026-10891-z",
    "repository": "https://zenodo.org/records/20775840",
    "files": [
      "Figure2/Fig2a.mat",
      "Figure2/Fig2b.mat"
    ]
  },
  "data_dictionary": {
    "scan": "Two different source scans; do not pool them as independent repeats.",
    "dphi": "Phase-distribution spread control, exported in Fig2a. Unit convention requires source verification.",
    "mean_phase": "Mean-phase control, exported in Fig2b, range 0 to 2pi.",
    "DOP": "Source-export degree of polarization. Fig2a uses approximately 0-100 scale; Fig2b approximately 0-1. Preserve units per scan; do not combine raw scales.",
    "S1/S2/S3": "Exported normalized polarization-direction components. Their squared norm should be inspected rather than assumed equal to the exported DOP."
  },
  "rows": 302,
  "statistics": {
    "dphi": {
      "n": 102,
      "min": 0.0,
      "max": 0.5050000000000003,
      "mean": 0.2525000000000001
    },
    "DOP": {
      "n": 302,
      "min": 0.6969392550000001,
      "max": 93.139824,
      "mean": 19.835836730452538
    },
    "S1": {
      "n": 302,
      "min": -0.9145613174158018,
      "max": 0.8667067186353989,
      "mean": 0.021601982294003574
    },
    "S2": {
      "n": 302,
      "min": -0.624171731610925,
      "max": 0.6596299670792776,
      "mean": 0.04424361624446888
    },
    "S3": {
      "n": 302,
      "min": -0.9210320760853088,
      "max": 0.999356739723518,
      "mean": 0.2731718502280629
    },
    "mean_phase": {
      "n": 200,
      "min": 0.0,
      "max": 6.283185307179586,
      "mean": 3.141592653589793
    }
  },
  "preview": [
    {
      "dphi": 0.0,
      "DOP": 93.139824,
      "S1": 0.0266768974263289,
      "S2": 0.0904556652152477,
      "S3": 0.995542027234643,
      "scan": "spread",
      "mean_phase": NaN
    },
    {
      "dphi": 0.13500000000000004,
      "DOP": 81.22475666666668,
      "S1": 0.0332872124063272,
      "S2": 0.0360823778113844,
      "S3": 0.998793039666925,
      "scan": "spread",
      "mean_phase": NaN
    },
    {
      "dphi": 0.27000000000000013,
      "DOP": 56.20188599999999,
      "S1": 0.0385011284133245,
      "S2": 0.141342386457727,
      "S3": 0.989210505647654,
      "scan": "spread",
      "mean_phase": NaN
    },
    {
      "dphi": 0.41000000000000025,
      "DOP": 31.001004333333334,
      "S1": 0.0659066296868944,
      "S2": 0.0964375957074724,
      "S3": 0.993147116494311,
      "scan": "spread",
      "mean_phase": NaN
    },
    {
      "dphi": NaN,
      "DOP": 0.7753992,
      "S1": 0.6147996963283668,
      "S2": 0.6538490269204854,
      "S3": 0.4410173477833979,
      "scan": "mean_phase",
      "mean_phase": 0.2210165685942568
    },
    {
      "dphi": NaN,
      "DOP": 0.822448405,
      "S1": 0.8574318227386268,
      "S2": 0.38017385015886074,
      "S3": -0.34680164860687224,
      "scan": "mean_phase",
      "mean_phase": 1.0735090474578188
    },
    {
      "dphi": NaN,
      "DOP": 0.787132115,
      "S1": 0.6139125800008035,
      "S2": -0.009068329948985484,
      "S3": -0.7893194741907164,
      "scan": "mean_phase",
      "mean_phase": 1.957575321834846
    },
    {
      "dphi": NaN,
      "DOP": 0.8427613900000002,
      "S1": 0.016982038798103026,
      "S2": -0.42962551483549394,
      "S3": -0.9028469706302319,
      "scan": "mean_phase",
      "mean_phase": 2.810067800698408
    },
    {
      "dphi": NaN,
      "DOP": 0.80507366,
      "S1": -0.612621571984825,
      "S2": -0.5872783336565545,
      "S3": -0.5289587003215568,
      "scan": "mean_phase",
      "mean_phase": 3.66256027956197
    },
    {
      "dphi": NaN,
      "DOP": 0.78688193,
      "S1": -0.9061455867173149,
      "S2": -0.2792955555365603,
      "S3": 0.31762685458867446,
      "scan": "mean_phase",
      "mean_phase": 4.546626553938997
    },
    {
      "dphi": NaN,
      "DOP": 0.72556984,
      "S1": -0.4334832324130062,
      "S2": 0.2738209229203421,
      "S3": 0.8585529788912355,
      "scan": "mean_phase",
      "mean_phase": 5.399119032802559
    },
    {
      "dphi": NaN,
      "DOP": 0.7301895649999999,
      "S1": 0.3510189584311359,
      "S2": 0.6284449571068913,
      "S3": 0.6941461789930579,
      "scan": "mean_phase",
      "mean_phase": 6.283185307179586
    }
  ],
  "additional_context": "The source study programs optical polarization statistics using spatial light modulators. We use two calibration/source scans, 102 and 200 rows. These are measurements supplied with the paper; no independent repeats or raw acquisition uncertainty are supplied in this subset.",
  "task": "Propose substantive follow-up scientific questions and explanatory hypotheses from the supplied actual source data. Distinguish published claims, observed measurements, and your new conditional proposals. Develop consequences and alternatives; do not require a completed proof or experiment. Do not claim independent rediscovery: the source study identity is visible.",
  "data_file": "measurements.csv",
  "retrieval_policy": "Use the same supplied source corpus for this controlled comparison; no external browsing. Data and source excerpts are shared with every system."
}

[end context 1]

Here are summaries of the previous meetings:

[begin summary 1]

The central assumption to challenge is a chain: nominal `dphi` represents the phase distribution realized in the optical field; that distribution changes ensemble coherence; and the exported DOP change reflects that coherence rather than calibration or export effects. In the supplied spread scan, exported DOP decreases as `dphi` increases while the displayed Stokes direction remains near positive S3. DOP is reported on an approximately 0–100 scale in this scan. These are observations, not independent evidence for the mechanism: the `dphi` convention and implementation are unverified, and this subset supplies neither acquisition uncertainty nor independent repeats.

**Conditional consequence:** If the phase program and optical-field model are verified, two distributions with matched implemented mean and variance but different shapes may yield different calibrated raw Stokes vectors. Select a pair for which the verified model predicts a resolvable contrast. Preregister the vector contrast between conditions as the primary test, and estimate its uncertainty from repeated acquisitions with calibration references. A measured contrast consistent with the model would support phase averaging over explanations based only on nominal spread. A null result would weaken that model only if the predicted contrast exceeds the experiment’s resolution; otherwise it is inconclusive. A contrary result would also challenge the specified model but would not identify a unique alternative cause.

The raw calibrated Stokes vector should be primary; exported DOP and direction stability are secondary diagnostics until their conventions are verified. Still unresolved are the `dphi` definition and units, the phase-program-to-field mapping, the DOP and Stokes export conventions, and measurement uncertainty.

The mean-phase scan is a separate question, not resolved by this spread-shape test. If mean phase drives a periodic response, at least two independently reacquired calibrated full sweeps should show a reproducible trajectory and endpoint closure within measurement and between-sweep uncertainty. Fit using the actual, nonuniform phase values and analyze this scan separately: its DOP is on an approximately 0–1 scale, and it is not an independent repeat of the spread scan.

[end summary 1]

[begin summary 2]

The supplied spread scan shows exported DOP decreasing as `dphi` increases, while the displayed Stokes direction stays near positive S3. These are observations from one scan, not evidence by themselves for a mechanism. The mean-phase scan also shows varying components, but this subset cannot establish repeatability or closure. The two scans use different DOP scales and are not independent repeats.

The hypothesis to test is conditional: **if the programmed phase distributions are realized at the optical field and the verified field-to-measurement model applies, then changing distribution shape at fixed implemented mean and variance can change the calibrated raw Stokes vector.** The model must map the phase distribution’s characteristic function to a specific Stokes prediction; that relation is not universal. After verifying the phase convention and model, choose two distributions with equal implemented mean and variance but a sufficiently distinct, precomputed Stokes contrast to measure. A reproducible contrast consistent with that prediction would support ensemble averaging over a moments-only account. An absent or inconsistent contrast would weaken the hypothesis without identifying a unique alternative.

For the follow-up, verify the implemented distributions, record calibration references, randomize condition order, and repeat measurements to estimate uncertainty and reproducibility. Use calibrated raw Stokes vectors as the primary outcome, with derived magnitude and direction as secondary diagnostics once their conventions are confirmed. These checks address programming errors and drift; apparatus nonlinearity remains unresolved unless separately characterized.

The `dphi` definition and units, scan-specific DOP scales, Stokes normalization, and export-to-measurement pipeline remain unverified. Until they are resolved, the supplied measurements motivate the test but do not establish the model’s applicability to this apparatus.

[end summary 2]

Here is the agenda for the meeting:

Compare the developed alternatives and record final specific research questions and hypotheses, their consequences and evidence limits.

Principal Investigator will convene the meeting. Then, each team member will provide their thoughts on the discussion one-by-one in the order above. After all team members have given their input, Principal Investigator will synthesize the points raised by each team member, make decisions regarding the agenda based on team member input, and ask follow-up questions to gather more information and feedback about how to better address the agenda. This will continue for 2 rounds. Once the discussion is complete, Principal Investigator will summarize the meeting in detail for future discussions, provide a specific recommendation regarding the agenda, and answer the agenda questions (if any) based on the discussion while strictly adhering to the agenda rules (if any).

## User

Principal Investigator, please provide your initial thoughts on the agenda as well as any questions you have to guide the discussion among the team members.

## Principal Investigator

**Principal Investigator:** The key decision is how to turn the two scans into specific, falsifiable follow-up questions without treating them as replicates or claiming more than these measurements support.

The spread scan reports a pronounced decrease in exported DOP as nominal `dphi` increases, while the exported Stokes direction remains near positive S3. That pattern is compatible with phase averaging, but it does not establish it: the `dphi` convention and phase-to-field mapping are unverified, and calibration, export conventions, or apparatus response could also contribute. The mean-phase scan varies across a cycle, but its distinct DOP scale and single-scan status mean it should be considered separately. Neither scan supplies independent repeats or acquisition uncertainty.

My starting proposal is to retain two questions, with calibrated raw Stokes vectors as the primary outcome in any follow-up:

1. **Spread-distribution question:** At fixed *verified, implemented* mean and variance, do different phase-distribution shapes produce the model-predicted contrast in the calibrated raw Stokes vector? This tests whether distribution shape matters beyond those moments, conditional on a specified phase-to-field model.
2. **Mean-phase question:** Does a repeated, calibrated sweep show a reproducible periodic Stokes trajectory and endpoint closure, using the actual phase values? This tests repeatability and periodic response; the current scan alone cannot establish either.

For the first question, a reproducible contrast consistent with a preregistered prediction would support the specified phase-averaging model over a moments-only account. A null or contrary result would weaken that model only in relation to measurement resolution and validated implementation; neither outcome alone identifies an alternative mechanism. For the second, reproducibility and closure would support a stable periodic response, but would not by themselves establish its physical cause.

**Questions for the team**

- **Domain Scientist:** What source conventions or optical-measurement details must be verified before interpreting `dphi`, DOP, and S1/S2/S3? Which competing physical or calibration explanations should we explicitly keep in scope?
- **Dynamical and Statistical Physicist:** What phase-distribution model yields a concrete, testable Stokes-vector prediction for the matched-moments comparison? What contrast and uncertainty criterion would make a null result meaningfully informative?
- **Both:** Should we treat the mean-phase sweep as a separate follow-up question, or is there a principled reason to prioritize it differently? What evidence would be sufficient to distinguish a reproducible programmed response from drift or export artifacts?

I suggest we first settle the observables and unresolved conventions, then specify the conditional hypotheses and what outcomes would support, weaken, or leave each inconclusive.

## User

Domain Scientist, please provide your thoughts on the discussion (round 1 of 2). If you do not have anything new or relevant to add, you may say "pass". Remember that you can and should (politely) disagree with other team members if you have a different perspective.

## Domain Scientist

**Domain Scientist, Round 1:** I agree with keeping the spread and mean-phase scans as separate questions, and with using calibrated raw Stokes vectors as the primary outcome. I would tighten one point: a matched nominal mean and variance is not enough. The *implemented optical-field phase distributions* must be matched on those moments; otherwise a contrast cannot isolate distribution shape from programming or transfer errors.

For the spread scan, the observed decline in exported DOP alongside a direction near positive S3 is consistent with reduced polarization magnitude while the displayed direction stays approximately fixed. But that interpretation is provisional: the spread scan’s DOP is on an approximately 0–100 scale, the mean-phase scan’s is approximately 0–1, and the exported Stokes-vector norm must not be assumed to equal either DOP. We should verify the source’s `dphi` convention, DOP scaling, and Stokes normalization before comparing quantities or calling the trend a change in degree of polarization.

I would keep calibration and export behavior as explicit alternatives to ensemble phase averaging. In particular, a stable displayed direction does not rule out a scale or normalization artifact in the exported DOP, and a changing Stokes vector does not by itself identify phase averaging. The follow-up should retain raw calibrated components and report derived magnitude and direction separately, with calibration references and repeated acquisitions to estimate uncertainty.

For the mean-phase question, endpoint closure is useful only if the sweep is reacquired and the endpoint comparison accounts for uncertainty and any phase-setting or measurement drift. The current single sweep motivates that test but cannot establish periodicity or reproducibility.

A question for the team: what verified mapping from the programmed phase distribution to the measured Stokes vector will we use to preregister a predicted contrast? Without that, the matched-moments experiment remains a sensible discrimination test, but its direction and expected size are not yet specified.

## User

Dynamical and Statistical Physicist, please provide your thoughts on the discussion (round 1 of 2). If you do not have anything new or relevant to add, you may say "pass". Remember that you can and should (politely) disagree with other team members if you have a different perspective.

## Dynamical and Statistical Physicist

**Dynamical and Statistical Physicist, Round 1:** I agree that these scans motivate distinct follow-ups and that raw calibrated Stokes vectors should be primary. I would sharpen the proposed “matched moments” test: it is not a universal test of phase averaging. Its prediction depends on the verified map from the phase distribution to the optical field and then to the measured Stokes vector.

For a simple coherent averaging model, the ensemble response can depend on the phase distribution’s characteristic function, not just its mean and variance. Thus two distributions with matched mean and variance can differ in predicted response, but only for a specified phase coupling and measurement model. We should calculate that predicted vector contrast before selecting conditions, then compare it with a resolution threshold set from repeated acquisitions and calibration references. If the predicted contrast is below that threshold, a null result is uninformative; if it is resolvable and absent, it weakens that particular model, not phase averaging in general.

I also want to avoid treating the near-constant exported Stokes direction as independent confirmation of the falling DOP. The direction and DOP may be derived from related exported quantities, and their normalization relationship is unverified. Preserve the scan-specific DOP scales and analyze each scan separately until the export conventions are established.

For the mean-phase sweep, periodicity should be tested against the actual, nonuniform phase settings rather than an assumed uniform grid. Endpoint agreement is a useful diagnostic, but it is not enough on its own: a periodic fit and reproducibility across reacquired sweeps are needed to distinguish a stable response from drift.

My question for the group is whether we can obtain a sufficiently specified field-to-Stokes model from the source materials and apparatus documentation to make a preregistered, quantitative prediction. If not, I recommend treating model specification and calibration as prerequisites, not interpreting a matched-moments experiment as a decisive mechanism test.

## User

This concludes round 1 of 2 of discussion. Principal Investigator, please synthesize the points raised by each team member, make decisions regarding the agenda based on team member input, and ask follow-up questions to gather more information and feedback about how to better address the agenda.

## Principal Investigator

**Principal Investigator, Round 1 Synthesis**

Both team members support treating the spread and mean-phase scans as separate investigations, using calibrated raw Stokes vectors as the primary follow-up outcome, and avoiding mechanistic claims from these single scans. The Domain Scientist emphasized verifying the source conventions and the *implemented optical-field* distributions, not just nominal settings. The Dynamical and Statistical Physicist added that matched mean and variance is informative only under a specified phase-to-field-to-Stokes model, and that a quantitative predicted contrast must be compared with a resolution threshold.

I agree with both points. The agenda will retain two questions, but the matched-moments experiment is conditional on first establishing the implementation and model. We will not present it as a universal test of phase averaging. The exported DOP trend and near-positive-S3 direction remain observations; neither establishes that DOP and Stokes norm correspond, nor excludes calibration or export effects. The mean-phase scan remains separate: its nonuniform settings should be analyzed at their actual values, and endpoint closure alone will not establish periodicity or reproducibility.

**Decisions for the agenda**

1. **Spread scan:** Ask whether distinct, verified phase distributions with matched implemented mean and variance produce the quantitatively predicted contrast in calibrated raw Stokes vectors. Before testing, verify `dphi` units and convention, phase-program-to-field mapping, DOP scaling, Stokes export conventions, and the field-to-measurement model. Preregister the predicted vector contrast and determine whether it exceeds an uncertainty/resolution threshold derived from repeated acquisitions and calibration references.
2. **Mean-phase scan:** Ask whether independently reacquired, calibrated sweeps show a reproducible periodic Stokes trajectory and endpoint closure within uncertainty. Fit using actual phase settings, without pooling this scan with the spread scan.
3. **Evidence limits:** Treat calibration drift, apparatus response, and export/normalization artifacts as unresolved alternatives. A model-consistent contrast would support that specified model over a moments-only account; a null or contrary result would weaken it only if implementation is verified and the contrast is resolvable. Neither result alone identifies a unique mechanism.

**Follow-up for Round 2**

- **Domain Scientist:** Which source or apparatus conventions can realistically be verified from the supplied materials, and which require new calibration or acquisition? Are there specific calibration or export-artifact alternatives we should name in the final research question?
- **Dynamical and Statistical Physicist:** What minimal field-to-Stokes model and distribution pair would give a concrete predicted contrast? What uncertainty or resolution criterion would make the proposed null result interpretable?
- **Both:** Given these prerequisites, should the immediate recommendation be to prioritize model/convention verification before either experiment, or can the mean-phase repeatability test proceed independently while that work is underway?

## User

Domain Scientist, please provide your thoughts on the discussion (round 2 of 2). If you do not have anything new or relevant to add, you may say "pass". Remember that you can and should (politely) disagree with other team members if you have a different perspective.

## Domain Scientist

**Domain Scientist, Round 2:** I support the decisions. I would make one distinction explicit in the final recommendation: source-file verification and apparatus verification are different tasks. The supplied excerpt identifies the scans and their reported scales, but it does not establish the `dphi` unit convention, whether nominal distributions were realized at the optical field, or how DOP and Stokes components were computed and normalized. Those points may require source documentation, apparatus records, or new calibration measurements; we should not imply that inspecting the supplied rows alone can settle them.

I also think the mean-phase repeatability test can proceed in parallel with spread-model work, provided it is treated strictly as a separate calibrated acquisition. Reacquiring the sweep can test whether its trajectory and endpoint behavior reproduce without assuming a phase-to-Stokes mechanism. It still requires verified phase settings and calibration references, and should use the actual nonuniform phase values. I would not delay that descriptive repeatability check until the matched-moments model is complete.

For the spread question, I agree that no quantitative prediction should be preregistered until the phase-to-field-to-measurement mapping is specified. I would name calibration drift and export/normalization behavior as explicit alternatives, while recognizing that their presence cannot be inferred from the current data. The evidence supports a follow-up design, not a mechanism conclusion.

## User

Dynamical and Statistical Physicist, please provide your thoughts on the discussion (round 2 of 2). If you do not have anything new or relevant to add, you may say "pass". Remember that you can and should (politely) disagree with other team members if you have a different perspective.

## Dynamical and Statistical Physicist

**Dynamical and Statistical Physicist, Round 2:** I agree with the distinction between verifying the supplied source conventions and validating the apparatus. I also agree that a calibrated repeat of the mean-phase sweep can proceed in parallel with model development for the spread test. That sweep can establish reproducibility of the measured trajectory without first resolving its mechanism, as long as phase settings are verified and the nonuniform values are used in the analysis.

One refinement: endpoint closure is a useful preregistered diagnostic, but the primary repeatability criterion should be agreement of the full calibrated trajectory across independent sweeps, with uncertainty estimated from repeated acquisitions. Closure at the endpoints alone could occur despite differences elsewhere in the cycle.

For the spread experiment, I would require the model to predict a vector-valued contrast between chosen distributions, not merely a scalar DOP change. Set the resolution criterion from acquisition and calibration uncertainty before collecting the comparison data. Until such a prediction is available, the matched-moments question is well-posed as a *conditional* research question, but it is not yet an executable mechanism test.

## User

Principal Investigator, please summarize the meeting in detail for future discussions, provide a specific recommendation regarding the agenda, and answer the agenda questions (if any) based on the discussion while strictly adhering to the agenda rules (if any).

As a reminder, here is the agenda for the meeting:

Compare the developed alternatives and record final specific research questions and hypotheses, their consequences and evidence limits.

Your summary should take the following form.

### Agenda

Restate the agenda in your own words.

### Team Member Input

Summarize all of the important points raised by each team member. This is to ensure that key details are preserved for future meetings.

### Recommendation

Provide your expert recommendation regarding the agenda. You should consider the input from each team member, but you must also use your expertise to make a final decision and choose one option among several that may have been discussed. This decision can conflict with the input of some team members as long as it is well justified. It is essential that you provide a clear, specific, and actionable recommendation. Please justify your recommendation as well.

### Next Steps

Outline the next steps that the team should take based on the discussion.

## Principal Investigator

### Agenda
Compare the candidate explanations for the supplied optical measurements and record specific follow-up questions, conditional hypotheses, predicted consequences, and limits on what the existing evidence supports.

### Team Member Input

**Principal Investigator:** The two scans should be treated as separate investigations, not pooled as repeats. The spread scan reports declining exported DOP as nominal `dphi` increases, alongside a displayed Stokes direction near positive S3. These are observations from one scan, not evidence that phase averaging caused the trend. The mean-phase scan varies over a cycle but likewise cannot establish reproducibility or periodicity from a single sweep. Both scans lack supplied acquisition uncertainty and independent repeats.

The PI proposed calibrated raw Stokes vectors as the primary outcome for follow-up, with derived DOP and direction as secondary diagnostics after verifying conventions. Calibration, export behavior, and apparatus response remain alternatives to phase-averaging explanations.

**Domain Scientist:** Nominally matched phase-distribution moments are insufficient; the *implemented optical-field* distributions must be verified as matched. The `dphi` convention, DOP scale, Stokes normalization, and measurement/export pipeline require verification before interpreting or comparing these quantities. Source-file verification and apparatus verification are distinct: the supplied data alone do not establish field realization or measurement calibration. Calibration drift and export/normalization effects should remain explicit alternatives, not conclusions inferred from the scans.

The Domain Scientist supported a separate calibrated repeatability study of the mean-phase sweep in parallel with spread-model development. It should use verified phase settings and actual nonuniform values. Endpoint closure is useful but insufficient by itself; the trajectory should reproduce across independently reacquired sweeps.

**Dynamical and Statistical Physicist:** A matched-moments comparison is not a universal test of phase averaging. A specified phase-distribution-to-field-to-Stokes model is needed because the predicted response depends on the characteristic function and the optical and measurement model. Before testing, choose distributions for which that model predicts a vector-valued contrast and determine whether it exceeds a resolution threshold based on acquisition and calibration uncertainty. An absent contrast weakens only the specified model if implementation is verified and the contrast was resolvable; it does not rule out phase averaging generally.

For the mean-phase scan, analyze actual nonuniform phase settings. Assess full-trajectory reproducibility across independent sweeps; endpoint agreement is only a diagnostic. The repeatability study can proceed independently of completing the spread model, provided its settings and calibration are verified.

### Recommendation

Proceed with two separate follow-up questions, and prioritize verification of conventions and calibration before interpreting the existing trends mechanistically. In parallel, acquire a calibrated repeatability study of the mean-phase sweep; it does not depend on completing the spread model and can establish whether the measured trajectory reproduces.

1. **Spread-distribution question:** If the phase-to-field-to-measurement mapping is specified and the implemented distributions are verified, do different phase-distribution shapes with matched implemented mean and variance produce the model-predicted contrast in calibrated raw Stokes vectors?

   **Conditional hypothesis:** Under that verified model, the chosen distributions will yield a predicted vector contrast. A reproducible, model-consistent contrast would support that specified model over an account depending only on the matched moments. A null result would weaken the model only if the predicted contrast exceeds the preregistered resolution threshold. A contrary result would challenge the specified model but would not identify a unique alternative.

2. **Mean-phase question:** Do independently reacquired, calibrated sweeps show a reproducible Stokes trajectory across the cycle, including endpoint closure within uncertainty?

   **Conditional hypothesis:** If the response is stable and periodic under verified phase settings, the full calibrated trajectory should reproduce across sweeps and the endpoints should agree within measurement and between-sweep uncertainty. Reproducibility would support a stable periodic response, but would not establish its physical cause.

This recommendation preserves the useful distinction between a mechanism-discriminating spread test and a descriptive repeatability test. The existing measurements motivate both; they do not establish either hypothesis. In particular, the scans use different DOP scales (approximately 0–100 in the spread scan and 0–1 in the mean-phase scan), and the Stokes-vector norm must not be assumed to equal exported DOP.

### Next Steps

1. Verify from source documentation and acquisition records the `dphi` convention and units, mean-phase settings, DOP scaling, and Stokes export and normalization conventions. Record which questions cannot be answered from the supplied files.
2. Separately validate the apparatus: confirm that programmed phase distributions are realized at the optical field, characterize calibration references and drift, and document the field-to-measurement mapping.
3. For the mean-phase study, independently reacquire calibrated sweeps, use actual phase values in analysis, and preregister a full-trajectory reproducibility criterion and endpoint-closure diagnostic with uncertainty estimates.
4. For the spread study, specify the phase-to-field-to-Stokes model, select verified matched-moments distributions, calculate the predicted vector contrast, and preregister a resolution criterion based on repeated acquisitions and calibration uncertainty before collecting the comparison data.
5. Preserve scan-specific scales and analyze calibrated raw Stokes components as primary outcomes. Report derived magnitude, direction, and DOP only with their conventions stated; do not pool the scans as independent repeats.

