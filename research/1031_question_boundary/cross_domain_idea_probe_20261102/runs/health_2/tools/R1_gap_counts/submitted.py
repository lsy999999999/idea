import json
from collections import defaultdict
by_subject = defaultdict(list)
for sid, t in zip(DF['subject#'], DF['test_time']):
    by_subject[int(sid)].append(float(t))
rows = []
for sid in sorted(by_subject):
    times = sorted(by_subject[sid])
    n = len(times)
    c1 = 0
    c7 = 0
    r1 = 1
    r7 = 1
    for i, t in enumerate(times):
        r1 = max(r1, i + 1)
        while r1 < n and times[r1] - t <= 1.0:
            r1 += 1
        c1 += r1 - i - 1
        r7 = max(r7, i + 1)
        while r7 < n and times[r7] - t <= 7.0:
            r7 += 1
        c7 += r7 - i - 1
    rows.append({'subject': sid, 'recordings': n, 'pairs_le_1_day': c1, 'pairs_le_7_days': c7})
print(json.dumps({'definition': 'unordered distinct-row within-subject pairs; absolute test_time gap in days', 'subjects': rows, 'totals': {'subjects': len(rows), 'recordings': sum(x['recordings'] for x in rows), 'pairs_le_1_day': sum(x['pairs_le_1_day'] for x in rows), 'pairs_le_7_days': sum(x['pairs_le_7_days'] for x in rows)}}, separators=(',', ':')))