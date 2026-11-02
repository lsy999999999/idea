"""Post-run verification. Reads frozen runs; writes only this review directory.

Replays establish reproducibility, not scientific validity. The separate time-unit
diagnostic tests an observed semantic defect without changing the submitted code.
"""
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import harness as h


def same(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, (float, int)) and isinstance(b, (float, int)):
        return abs(a - b) <= 1e-9 * max(1, abs(a), abs(b))
    return a == b


def main():
    import numpy as np
    import pandas as pd

    outdir = ROOT / 'review'
    records = []
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1',
               PYTHONDONTWRITEBYTECODE='1')
    for run in sorted((ROOT / 'runs').iterdir()):
        for tool in h.state(run)['tools']:
            if tool['type'] != 'compute':
                continue
            path = run / 'tools' / tool['id'] / 'executed.py'
            started = time.monotonic()
            p = subprocess.run([h.PYTHON, str(path)], cwd=outdir, env=env,
                               text=True, capture_output=True, timeout=60)
            try:
                equal = same(json.loads(p.stdout), json.loads(tool['result']['stdout']))
            except (ValueError, TypeError):
                equal = False
            row = dict(run=run.name, tool_id=tool['id'],
                       executed_sha256=h.sha(path), returncode=p.returncode,
                       stdout=p.stdout, stderr=p.stderr,
                       elapsed_seconds=time.monotonic() - started,
                       same_json_with_numeric_tolerance_1e_9=equal)
            records.append(row)
            print(run.name, 'replay', 'MATCH' if equal else 'DIFFERENT', flush=True)

    cfg = h.read(ROOT / 'runs/energy_1/config.json')
    d = pd.read_csv(cfg['data_path'])
    timestamps = pd.to_datetime(d.date, format='%Y-%m-%d%H:%M:%S', errors='coerce')
    order = np.argsort(timestamps.to_numpy(), kind='stable')
    t = timestamps.to_numpy()[order]
    app = d.Appliances.to_numpy(float)[order]

    def event_count(threshold, fixed):
        def contiguous(a, b):
            if b > len(t):
                return False
            if b - a <= 1:
                return True
            if fixed:
                return bool(np.all(np.diff(t[a:b]) == np.timedelta64(10, 'm')))
            return bool(np.all(np.diff(t[a:b].astype('int64')) == 600000000000))
        count = 0
        i = 1
        while i + 1 < len(app):
            if app[i] > threshold and app[i+1] > threshold and app[i-1] <= threshold:
                start, end = i, i+1
                k = end+1
                while (k+2 < len(app) and app[k] <= threshold
                       and app[k+1] > threshold and app[k+2] > threshold):
                    end = k+2
                    k = end+1
                if start >= 6 and start+6 <= len(t) and contiguous(start-6, start+6):
                    count += 1
                i = end+1
            else:
                i += 1
        return count

    steps, counts = np.unique(np.diff(t.astype('int64')), return_counts=True)
    diagnostic = dict(
        pandas_version=pd.__version__, numpy_version=np.__version__,
        data_sha256=h.sha(Path(cfg['data_path'])), rows=len(d),
        missing_parsed_timestamps=int(timestamps.isna().sum()),
        timestamp_dtype=str(t.dtype),
        integer_step_counts={str(int(s)): int(n) for s, n in zip(steps, counts)},
        submitted_integer_step=600000000000,
        actual_ten_minute_spacing=bool(np.all(np.diff(t) == np.timedelta64(10, 'm'))),
        thresholds=[dict(threshold_wh=threshold,
                         raw_adjacent_high_onsets=int(np.sum(
                             (app[1:-1] > threshold) & (app[2:] > threshold)
                             & (app[:-2] <= threshold))),
                         original_window_eligible_events=event_count(threshold, False),
                         corrected_time_comparison_eligible_events=event_count(threshold, True))
                    for threshold in [100, 150]],
        conclusion='Zero events is an implementation artifact; it is not a data-feasibility result.',
        scope='Post-run counting diagnostic only. No matched thermal-effect estimate or new role reply. Original files unchanged.')

    h.dump(outdir / 'NUMERICAL_REVIEW.json', dict(
        time=h.now(), verification_script_sha256=h.sha(Path(__file__)),
        replay_count=len(records), all_replays_match=all(
            r['returncode'] == 0 and r['same_json_with_numeric_tolerance_1e_9'] for r in records),
        replays=records, energy_time_unit_diagnostic=diagnostic))
    print(json.dumps(diagnostic, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
