"""Independent post-run source/hash and elementary numerical checks; no model calls."""
from pathlib import Path
import csv,json,hashlib,math,statistics
ROOT=Path(__file__).resolve().parents[1]
report={}
for case in ['wave','optical']:
 d=ROOT/'cases'/case;p=d/'measurements.csv';manifest=json.loads((d/'source_manifest.json').read_text())
 digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==manifest['normalized_sha256']
 with p.open() as f:rows=list(csv.DictReader(f))
 report[case]={'rows':len(rows),'sha256':digest,'source_hash_valid':True}
 if case=='wave':
  t=[float(x['time_s']) for x in rows];w=[float(x['correlation_width']) for x in rows];y=[float(x['mean_shear_magnitude']) for x in rows]
  delta=[b-a for a,b in zip(t,t[1:])];mu=statistics.mean(w);my=statistics.mean(y)
  corr=sum((a-mu)*(b-my) for a,b in zip(w,y))/math.sqrt(sum((a-mu)**2 for a in w)*sum((b-my)**2 for b in y))
  report[case].update(sampling_hz=1/statistics.mean(delta),interval_s=statistics.mean(delta),duration_s=t[-1]-t[0],width_zero_count=w.count(0),pearson_width_shear=corr)
  assert math.isclose(report[case]['sampling_hz'],300,rel_tol=1e-12)
 else:
  spread=[r for r in rows if r['scan']=='spread'];phase=[r for r in rows if r['scan']=='mean_phase']
  avg=lambda group,col:statistics.mean(float(r[col]) for r in group)
  squared=[sum(float(r[k])**2 for k in ['S1','S2','S3']) for r in phase]
  gap=math.sqrt(sum((float(phase[-1][k])-float(phase[0][k]))**2 for k in ['S1','S2','S3']))
  ratio=avg(spread,'DOP')/100/avg(phase,'DOP')
  report[case].update(spread_n=len(spread),phase_n=len(phase),spread_dop_mean_percent=avg(spread,'DOP'),phase_dop_mean_fraction=avg(phase,'DOP'),corrected_ratio=ratio,phase_stokes_squared_norm_mean=statistics.mean(squared),endpoint_direction_distance=gap)
  expected=json.loads((ROOT/'preparation/optical_correction_truth.json').read_text())['O1']['corrected_ratio_of_scan_means']
  assert math.isclose(ratio,expected,rel_tol=1e-12)
report['scope']='Controller post-run checks. Not scientific computations performed by every research agent.'
(ROOT/'DATA_VERIFICATION.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
