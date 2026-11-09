"""Screen measured trajectories and broker explicit, reproducible data operations."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.io import loadmat

from prepare import HERE, save


PROPOSAL = HERE / 'proposals/collective_motion_20261105'
CASE = HERE / 'cases/fish_001'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def sources():
    """Only actual indexed abstracts read during source preparation; no generated abstracts."""
    sensory = json.loads((PROPOSAL / 'controller_only/sensory_foundation.json').read_text())['message']['items'][0]
    import re
    abstract = re.sub(r'<[^>]+>', '', sensory['abstract'])
    foundation = [
        ('F1', 'A Blind Fish Can School', '1976-11-26', '10.1126/science.982056', abstract,
         'Crossref JSON, archived before the trial'),
        ('F2', 'Collective memory and spatial sorting in animal groups', '2002-09-01', '10.1006/jtbi.2002.3065',
         'We present a self-organizing model of group formation in three-dimensional space, and use it to investigate the spatial dynamics of animal groups such as fish schools and bird flocks. We reveal the existence of major group-level behavioural transitions related to minor changes in individual-level interactions. Further, we present the first evidence for collective memory in such animal groups (where the previous history of group structure influences the collective behaviour exhibited as individual interactions change) during the transition of a group from one type of collective behaviour to another. The model is then used to show how differences among individuals influence group structure, and how individuals employing simple, local rules of thumb, can accurately change their spatial position within a group (e.g. to move to the centre, the front, or the periphery) in the absence of information on their current position within the group as a whole. These results are considered in the context of the evolution and ecological importance of animal groups.',
         'Verbatim abstract from browser-rendered Europe PMC DOI query; firstPublicationDate supplied by the same record'),
        ('F3', 'The ontogeny of fin function during routine turns in zebrafish Danio rerio', '2007-10-01', '10.1242/jeb.007484',
         'Zebrafish Danio rerio exhibit spontaneous, routine turns as part of their normal foraging behavior from the early free-swimming stage to adulthood. Given the importance of this behavior and its pervasiveness during zebrafish life history, the functional requirements of routine turning should play an important role in development. Conversely, the ontogeny of turning performance should reflect morphological development. In this paper we analyze the kinematics of routine turning during ontogeny in zebrafish and compare the scaling of turning kinematics to predictions from two existing models. Twenty-nine fish ranging in size from 0.38 to 1.97 cm in fork length (FL) were filmed at 1000 frames s(-1) while performing routine turns. Images were analyzed using image cross-correlation to calculate body and fin velocities. We performed piecewise linear regression to identify variables that do not have a constant rate of change across ontogeny and found that two variables, turn angle and angular velocity, have a transition in slope at a body size of approximately 1 cm. Other variables show a constant positive (pectoral and caudal fin velocity, turn duration), negative (body curvature) or zero (head velocity) rate of change across ontogeny. We interpret these trends in light of morphological changes over ontogeny as well as relevant hydrodynamic conditions. We also compare the slope of the log-transformed variables to predictions from two scaling models of change in function with increasing size. We find mixed support for both models with no single model being better at predicting a single type of variable such as linear velocities. We conclude that morphological development of the paired and median fins and of the skeleton, is an important factor in determining the performance of routine turning over ontogeny. Three-dimensional kinematics and ecological behavior information will further elucidate the ontogenetic patterns observed here.',
         'Verbatim abstract from browser-rendered Europe PMC query restricted to publications before 2010'),
        ('F4', 'Prey tracking by larval zebrafish: axial kinematics and visual control', '2005-07-25', '10.1159/000087158',
         "High-speed imaging was used to record the prey-tracking behavior of larval zebrafish as they fed upon paramecium. Prey tracking is comprised of a variable set of discrete locomotor movements that together align the larva with the paramecium and bring it into close proximity, usually within one body length. These tracking behaviors are followed by a brief capture swim bout that was previously described [Borla et al., 2002]. Tracking movements were classified as either swimming or turning bouts. The swimming bouts were similar to a previously characterized larval slow swim [Budick and O'Malley, 2000], but the turning movements consisted of unique J-shaped bends which appear to minimize forward hydrodynamic disturbance when approaching the paramecium. Such J-turn tracking bouts consisted of multiple unilateral contractions to one side of the body. J-turns slowly and moderately alter the orientation of the larva - this is in contrast to previously described escape and routine turns. Tracking behaviors appear to be entirely visually guided. Infra-red (IR) imaging of locomotor behaviors in a dark environment revealed a complete absence of tracking behaviors, even though the normal repertoire of other locomotive behaviors was recorded. Concomitantly, such larvae were greatly impaired in consuming paramecia. The tracking behavior is of interest because it indicates the presence of sophisticated locomotor control circuitry in this relatively simple model organism. Such locomotor strategies may be conserved and elaborated upon by other larval and adult fishes.",
         'Verbatim abstract from browser-rendered Europe PMC query restricted to publications before 2010'),
    ]
    return [{'id': sid, 'title': title, 'date': date, 'doi': 'https://doi.org/' + doi,
             'url': 'https://doi.org/' + doi, 'text': text, 'access': 'indexed_abstract_only',
             'extraction_provenance': origin} for sid, title, date, doi, text, origin in foundation]


def prepare(case=CASE):
    case = Path(case)
    if case.exists():
        verify(case)
        return
    archive = PROPOSAL / 'controller_only/materials.zip'
    if hashlib.md5(archive.read_bytes()).hexdigest() != 'c4788f6ab6fc9ded2ffdbcd8ae907558':
        raise ValueError('Archive does not match the public file manifest')
    allowed, private = case / 'allowed', case / 'controller_only'
    (allowed / 'records').mkdir(parents=True)
    private.mkdir()
    records, provenance = [], []
    with zipfile.ZipFile(archive) as z:
        names = sorted(n for n in z.namelist() if n.startswith('materials/forcemaps/trajectoriesvideo_') and n.endswith('.mat'))
        if len(names) != 13:
            raise ValueError('Unexpected trajectory file inventory')
        for i, name in enumerate(names, 1):
            d = loadmat(io.BytesIO(z.read(name)), simplify_cells=True)
            if set(d) - {'__header__', '__version__', '__globals__', 'trajectories', 'probtrajectories'}:
                raise ValueError('Unexpected variables require screening')
            p, q = np.asarray(d['trajectories']), np.asarray(d['probtrajectories'])
            if p.ndim != 3 or p.shape[1:] != (2, 2) or q.shape != p.shape[:2]:
                raise ValueError('Unexpected measurement layout')
            rid = f'R{i:02d}'
            path = allowed / 'records' / (rid + '.npz')
            # Preserve every measured value; no model, smoothing, time crop or quality filter.
            np.savez_compressed(path, positions=p, tracker_score=q)
            records.append({'record_id': rid, 'frames': len(p), 'objects': 2,
                            'position_shape': list(p.shape), 'file': 'records/' + path.name,
                            'sha256': digest(path), 'nonfinite_positions': int(np.sum(~np.isfinite(p)))})
            provenance.append({'record_id': rid, 'archive_member': name,
                               'member_sha256': hashlib.sha256(z.read(name)).hexdigest()})
    save(allowed / 'measurements.json', {'records': records,
         'schema': 'positions[frame, object, coordinate]; tracker_score[frame, object]',
         'coordinates': ['x', 'y'], 'objects': ['A', 'B'], 'unit': 'native image coordinate unit',
         'time_unit': 'frame index', 'physical_calibration_supplied': False,
         'score_meaning': 'Recorded tracker output; includes negative codes and fractional values. Not a calibrated probability. Semantics not documented in the measurement files.',
         'identity_scope': 'Labels A/B are local tracking labels; no cross-record identity or within-record swap-free guarantee.',
         'sampling_limits': 'Frames are consecutive in each record. No independent frame-rate or spatial calibration was found in the measurement files.',
         'missing_measurements': ['body pose and length', 'neural activity', 'actual sensory inputs', 'independent wall geometry', 'stimulus interventions', 'individual identity across records']})
    save(allowed / 'sources.json', sources())
    save(private / 'provenance.json', {'archive_path': str(archive.resolve()), 'archive_sha256': digest(archive),
         'archive_md5': hashlib.md5(archive.read_bytes()).hexdigest(), 'mapping': provenance,
         'layout_basis': 'Author data-use script indexes trajectories(:,fish,coordinate). Only layout and optional scale declarations inspected; no author code executed or supplied.',
         'unused_scale_declarations': 'Author script uses scaleD=35/1000 and a factor of 30 in velocity conversion. These were not independently verified; actors work in native coordinate units and frames.',
         'excluded': ['all .m and .fig files', 'model and simulation folders', 'origin paper, abstract, metadata and later literature', 'original file names and recording timestamps']})
    save(private / 'restriction.json', {'allowed_before_exclusive': '2010-01-01',
         'source_paper': {'id': 'https://doi.org/10.1098/rspb.2017.0224',
                          'title': 'Signatures of optimal control in pairs of schooling zebrafish'},
         'data_doi': 'https://doi.org/10.5061/dryad.f0g32',
         'date_policy': 'Conservative pre-2010 scientific corpus, not a verified earliest-publication reconstruction',
         'raw_measurement_exception': True, 'originating_paper_body_downloaded': False})
    save(private / 'allowed_hashes.json', {str(p.relative_to(allowed)): digest(p) for p in allowed.rglob('*') if p.is_file()})
    protected = json.loads((PROPOSAL / 'controller_only/PROTECTED_BEFORE_TEST.json').read_text())
    save(private / 'protected_hashes.json', protected)


def verify(case):
    case = Path(case)
    for name, expected in json.loads((case / 'controller_only/allowed_hashes.json').read_text()).items():
        if digest(case / 'allowed' / name) != expected:
            raise ValueError('Allowed material mutated')
    for source in json.loads((case / 'allowed/sources.json').read_text()):
        if source['date'] >= '2010-01-01' or source['doi'] == 'https://doi.org/10.1098/rspb.2017.0224':
            raise ValueError('Forbidden scientific source')


def clean(value):
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return round(float(value), 7) if np.isfinite(value) else None
    if isinstance(value, np.integer):
        return int(value)
    return value


class Broker:
    def __init__(self, case):
        self.case = Path(case)
        self.catalog = json.loads((self.case / 'allowed/measurements.json').read_text())
        self.records = {r['record_id']: r for r in self.catalog['records']}
        self.sources = {s['id']: s for s in json.loads((self.case / 'allowed/sources.json').read_text())}

    def arrays(self, rid):
        if rid not in self.records:
            raise ValueError('Unknown record ID')
        data = np.load(self.case / 'allowed' / self.records[rid]['file'], allow_pickle=False)
        return data['positions'], data['tracker_score']

    def operation(self, op):
        if not isinstance(op, dict):
            raise ValueError('Operation must be an object')
        rid = op.get('record_id')
        p, q = self.arrays(rid)
        start, stop = op.get('start', 0), op.get('stop', len(p))
        if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= len(p):
            raise ValueError('Invalid frame range')
        kind = op.get('kind')
        if kind == 'window':
            stride = op.get('stride', 1)
            if type(stride) is not int or stride < 1 or len(range(start, stop, stride)) > 240:
                raise ValueError('Window budget exceeded (240 sampled rows)')
            return clean({'operation': op, 'rows': [[i, *p[i, 0], *p[i, 1], *q[i]] for i in range(start, stop, stride)],
                          'columns': ['frame', 'Ax', 'Ay', 'Bx', 'By', 'A_tracker_score', 'B_tracker_score'],
                          'processing': 'No smoothing or quality filtering. Display rounded to 7 decimals; full values retained.'})
        lag = op.get('derivative_lag', 1)
        smoothing = op.get('smoothing', 1)
        if type(lag) is not int or not 1 <= lag <= 60 or type(smoothing) is not int or not 1 <= smoothing <= 21:
            raise ValueError('Invalid derivative/smoothing choice')
        if stop-start < smoothing+lag:
            raise ValueError('Frame range too short for smoothing and derivative lag')
        selected, scores = p[start:stop].copy(), q[start:stop]
        mask_rule = op.get('score_filter', 'none')
        if mask_rule not in {'none', 'nonnegative'}:
            raise ValueError('Unknown score rule')
        if mask_rule == 'nonnegative':
            selected[np.any(scores < 0, axis=1)] = np.nan
        if smoothing > 1:
            # Valid trailing mean; do not zero-pad endpoints or smooth across missing values.
            selected = np.stack([np.mean(selected[i:i+smoothing], axis=0)
                                 for i in range(len(selected)-smoothing+1)])
        velocity = (selected[lag:] - selected[:-lag]) / lag
        # A finite pair of endpoints must not bridge a missing/filtered interior frame.
        for offset in range(1, lag):
            velocity[~np.isfinite(selected[offset:offset+len(velocity)]).all(axis=2)] = np.nan
        speed = np.linalg.norm(velocity, axis=2)
        distance = np.linalg.norm(selected[:, 1] - selected[:, 0], axis=1)
        finite = np.isfinite(velocity).all(axis=(1, 2))
        moving = finite & (speed[:, 0] > 0) & (speed[:, 1] > 0)
        alignment = np.sum(velocity[moving, 0]*velocity[moving, 1], axis=1)/(speed[moving, 0]*speed[moving, 1])
        result = {'operation': op, 'used_position_frames': len(selected), 'finite_velocity_pairs': int(finite.sum()),
                  'units': 'native coordinate unit/frame; distance in native coordinate unit',
                  'processing': {'derivative': '(position[t+lag]-position[t])/lag', 'lag': lag,
                                 'smoothing': smoothing, 'score_filter': mask_rule,
                                 'filter_assumption': 'nonnegative only excludes negative tracker codes; it does not establish valid identities'},
                  'limitations': 'Tracking labels may swap; displacement direction is not body orientation. Shared surroundings and tracking errors can produce correlations. No intervention or causal identification.'}
        if kind == 'motion':
            result.update(distance_quantiles=np.nanquantile(distance, [.1, .5, .9]).tolist(),
                          speed_quantiles_by_object=[np.nanquantile(speed[:, j], [.1, .5, .9]).tolist() for j in (0, 1)],
                          mean_cosine_displacement_alignment=float(np.mean(alignment)) if len(alignment) else None,
                          negative_score_rows=int(np.any(scores < 0, axis=1).sum()),
                          nonfinite_input_values=int(np.sum(~np.isfinite(p[start:stop]))))
        elif kind == 'lag_correlation':
            lags = op.get('lags', [-10, -3, 0, 3, 10])
            if not isinstance(lags, list) or not lags or len(lags) > 13 or any(type(x) is not int or abs(x) > 60 for x in lags):
                raise ValueError('Invalid correlation lags')
            corr = []
            for delay in lags:
                if abs(delay) >= len(velocity):
                    corr.append({'delay_frames': delay, 'paired_rows': 0, 'centered_vector_correlation': None})
                    continue
                a, b = (velocity[:len(velocity)-delay or None, 0], velocity[delay:, 1]) if delay >= 0 else (velocity[-delay:, 0], velocity[:delay, 1])
                keep = np.isfinite(a).all(axis=1) & np.isfinite(b).all(axis=1)
                aa, bb = a[keep], b[keep]
                if len(aa) > 2:
                    aa, bb = aa-aa.mean(axis=0), bb-bb.mean(axis=0)
                    den = np.sqrt(np.sum(aa*aa)*np.sum(bb*bb))
                    score = float(np.sum(aa*bb)/den) if den else None
                else:
                    score = None
                corr.append({'delay_frames': delay, 'paired_rows': int(keep.sum()), 'centered_vector_correlation': score})
            result.update(correlations=corr, delay_convention='positive delay: A earlier, B later; labels do not imply leaders')
        else:
            raise ValueError('Unknown operation; available: window/motion/lag_correlation')
        return clean(result)

    def request(self, request):
        if not isinstance(request, dict):
            raise ValueError('Request must be an object')
        ids = request.get('source_ids', [])
        records = request.get('record_ids', [])
        ops = request.get('operations', [])
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in self.sources for i in ids):
            raise ValueError('Source outside historical corpus')
        if not isinstance(records, list) or any(not isinstance(i, str) or i not in self.records for i in records):
            raise ValueError('Record outside measured corpus')
        if not isinstance(ops, list) or len(ops) > 3:
            raise ValueError('At most 3 explicit operations per request')
        if set(request) - {'source_ids', 'record_ids', 'operations', 'needed', 'gap', 'why_now'}:
            raise ValueError('Unsupported request fields; no external URL or executable code allowed')
        return {'request': request, 'sources': [self.sources[i] for i in ids],
                'record_metadata': [self.records[i] for i in records],
                'computed': [self.operation(op) for op in ops],
                'unavailable': 'No hidden paper, newer work, neural recordings, body posture, interventions or unrecorded calibration can be supplied.'}


if __name__ == '__main__':
    prepare()
    b = Broker(CASE)
    print(json.dumps({'case': str(CASE), 'records': len(b.records),
                      'frames': sum(r['frames'] for r in b.records.values())}))
