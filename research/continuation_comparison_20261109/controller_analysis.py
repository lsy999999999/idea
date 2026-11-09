"""Local exploratory audit; never an input to the independent research actors."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
data = ROOT / 'cases/optical/measurements.csv'
frame = pd.read_csv(data)
spread = frame.loc[frame['scan'] == 'spread'].copy()
vectors = spread[['S1', 'S2', 'S3']].to_numpy()
norm2 = (vectors ** 2).sum(axis=1)
unit = vectors / np.sqrt(norm2)[:, None]
angle = np.degrees(np.arccos(np.clip(unit @ unit[0], -1, 1)))
polarization = spread['DOP'].to_numpy() / 100

def row(index):
    return {k: (None if pd.isna(v) else v) for k, v in spread.iloc[index].to_dict().items()}

groups = []
for label, mask in [('P>=0.5', polarization >= .5),
                    ('0.2<=P<0.5', (polarization >= .2) & (polarization < .5)),
                    ('P<0.2', polarization < .2)]:
    groups.append({'group': label, 'n': int(mask.sum()),
                   'median_angle_deg': float(np.median(angle[mask])),
                   'max_angle_deg': float(angle[mask].max())})

# Analytic illustration, NOT a model fitted to these apparatus measurements.
# Jones vectors (1, exp(i*phi))/sqrt(2), equal intensities, incoherent averaging.
# P=|E exp(i phi)|. Both unwrapped distributions have mean 0 and variance 1.
# A: +/-1 with equal weight. B: 0 with weight .75, +/-2 with weight .125.
moment_a = float(np.cos(1))
moment_b = float(.75 + .25 * np.cos(2))
assert abs((.5 * 1**2 + .5 * (-1)**2) - (.125 * 2**2 + .125 * (-2)**2)) < 1e-14
assert moment_b > moment_a > 0
assert len(spread) == 102 and np.isfinite(angle).all()

phases = np.array([-1., 1.])
global_jones = np.exp(1j * phases)[:, None] * np.array([1., 1.])[None, :] / np.sqrt(2)
relative_jones = np.column_stack([np.ones(2), np.exp(1j * phases)]) / np.sqrt(2)
def ensemble_dop(fields):
    coherency = np.einsum('ni,nj->ij', fields, fields.conj()) / len(fields)
    values = np.linalg.eigvalsh(coherency)
    return float((values[1] - values[0]) / values.sum())
common_phase_dop = ensemble_dop(global_jones)
relative_phase_dop = ensemble_dop(relative_jones)
assert abs(common_phase_dop - 1) < 1e-12
assert abs(relative_phase_dop - np.cos(1)) < 1e-12

result = {
    'status': 'local_controller_exploratory_analysis_not_agent_output',
    'data_sha256': hashlib.sha256(data.read_bytes()).hexdigest(),
    'source': 'Nature DOI 10.1038/s41586-026-10891-z; Zenodo 20775840; Figure2/Fig2a.mat normalized export',
    'spread_rows': len(spread),
    'direction_norm_squared_range': [float(norm2.min()), float(norm2.max())],
    'angle_reference': 'unit-normalized first spread row, Euclidean sphere angle in degrees',
    'angle_median_deg': float(np.median(angle)),
    'angle_max_deg': float(angle.max()),
    'angle_max_row': row(int(np.argmax(angle))),
    'angle_last_deg': float(angle[-1]),
    's3_min_row': row(int(np.argmin(spread['S3'].to_numpy()))),
    'exploratory_dop_groups': groups,
    'equal_moments_illustration': {
        'assumptions': 'equal-intensity Jones (1,exp(i phi))/sqrt(2); incoherent ensemble averaging; exact phase implementation; common ideal measurement map',
        'distribution_A': {'phi': [-1, 1], 'weights': [.5, .5]},
        'distribution_B': {'phi': [-2, 0, 2], 'weights': [.125, .75, .125]},
        'unwrapped_mean': 0, 'unwrapped_variance': 1,
        'phase_range': '[-2,2] radians within one fixed unwrap; circular variance differs',
        'first_circular_moment_A': moment_a,
        'first_circular_moment_B': moment_b,
        'predicted_DOP_contrast': moment_b - moment_a,
        'predicted_direction': 'same positive axis in both; coordinate labels depend on convention',
        'meaning': 'Concrete instance of Virtual Lab question, derived by controller after reading its frozen output. Standard ideal-model result, not a new agent discovery or source-apparatus fit.'
    },
    'normalization_sensitivity': {
        'relation': 'For s=P*u and small additive error e, delta_u approximately (I-u*u^T)e/P. Equal transverse component-error scales yield direction variance proportional to 1/P^2.',
        'scope': 'Local first-order formula for P>0 and ||e|| much less than P. At P=0 direction undefined. Requires common component-noise assumptions; no noise estimate supplied here.'
    },
    'assumption_audit_after_content_probe': {
        'target': 'Content-only H1 says local fields have the same polarization and a random phase, then uses relative-phase coherence attenuation.',
        'necessary_distinction': 'A random GLOBAL phase multiplying an identical Jones vector does not depolarize. Relative phase between components, or apparatus-generated differing polarization states, can depolarize after averaging.',
        'exact_two_phase_example': 'Equal mixture phi=-1,+1 radians. Common phase: E=exp(i phi)*(1,1)/sqrt(2). Relative phase: E=(1,exp(i phi))/sqrt(2).',
        'common_phase_DOP': common_phase_dop,
        'relative_phase_DOP': relative_phase_dop,
        'review_status': 'Controller identified missing/ambiguous assumption; the model critic did not submit a finding and the author has not responded.'
    },
    'limitations': [
        'Data inspected before grouping: descriptive and exploratory, not preregistered confirmation.',
        'Angles relative to a noisy first row do not identify physical rotation or its cause.',
        'No independent repeats, raw unnormalized Stokes or acquisition-error model in this subset.',
        'A global excursion does not refute a conditional direction-stability hypothesis.',
        'No new model calls and no new completed v4 research workflow.'
    ]
}
(ROOT / 'LOCAL_ANALYSIS.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
