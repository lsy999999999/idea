import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/sources/uci_374_data.csv')
TABLES={"main":DF}
import json, math
import numpy as np
import pandas as pd

d = DF.reset_index(drop=True).copy()
d["_time"] = pd.to_datetime(d["date"], format="%Y-%m-%d%H:%M:%S", errors="coerce")
d = d.sort_values("_time", kind="stable").reset_index(drop=True)
t = d["_time"].to_numpy()
app = d["Appliances"].to_numpy(float)
temp = ((d["T3"].to_numpy(float) + d["T7"].to_numpy(float)) / 2.0)
t6, tout = d["T6"].to_numpy(float), d["T_out"].to_numpy(float)
dow = d["_time"].dt.dayofweek.to_numpy()
minute = (d["_time"].dt.hour * 60 + d["_time"].dt.minute).to_numpy()

def contiguous(a, b):
    return b <= len(t) and (b-a <= 1 or np.all(np.diff(t[a:b].astype("int64")) == 600000000000))
def contrasts(i):
    if i < 6 or i+6 > len(t) or not contiguous(i-6, i+6): return None
    pre = float(np.mean(temp[i-3:i]))
    post = float(np.mean(temp[i+3:i+6]))
    lead = float(np.mean(temp[i-3:i]) - np.mean(temp[i-6:i-3]))
    return post-pre, lead, pre

def run(threshold):
    events=[]
    i=1
    while i+1 < len(app):
        if app[i] > threshold and app[i+1] > threshold and app[i-1] <= threshold:
            start=i; end=i+1; k=end+1
            while k+2 < len(app) and app[k] <= threshold and app[k+1] > threshold and app[k+2] > threshold:
                end=k+2; k=end+1
            c=contrasts(start)
            if c is not None: events.append((start,c))
            i=end+1
        else: i += 1
    controls=[]
    for j in range(6, len(app)-6):
        if app[j] <= threshold and np.all(app[j-6:j+7] <= threshold) and contrasts(j) is not None:
            controls.append(j)
    used=set(); pairs=[]
    for i, ec in events:
        choices=[]
        for j in controls:
            if j in used or dow[j] != dow[i]: continue
            td=abs(int(minute[j])-int(minute[i])); td=min(td,1440-td)
            cc=contrasts(j)
            if td > 60 or abs(ec[2]-cc[2]) > 1 or abs(t6[i]-t6[j]) > 2 or abs(tout[i]-tout[j]) > 2: continue
            score=(td/60)**2+(ec[2]-cc[2])**2+(t6[i]-t6[j])**2/4+(tout[i]-tout[j])**2/4
            choices.append((score,j,cc))
        if choices:
            _,j,cc=min(choices)
            used.add(j); pairs.append((i,ec,j,cc))
    if not pairs:
        return {"threshold_wh":threshold,"events":len(events),"matched":0,"event_days":0,"post_mean_c":None,"post_ci95_c":None,"lead_mean_c":None,"lead_ci95_c":None}
    byday={}
    for i,ec,j,cc in pairs:
        day=str(pd.Timestamp(t[i]).date())
        byday.setdefault(day,[]).append((ec[0]-cc[0],ec[1]-cc[1]))
    days=list(byday)
    vals=np.array([np.mean(byday[x],axis=0) for x in days],float)
    rng=np.random.default_rng(42)
    boots=np.empty((1000,2))
    for b in range(1000):
        ix=rng.integers(0,len(days),len(days)); boots[b]=vals[ix].mean(axis=0)
    return {"threshold_wh":threshold,"events":len(events),"matched":len(pairs),"event_days":len(days),"post_mean_c":float(vals[:,0].mean()),"post_ci95_c":[float(x) for x in np.percentile(boots[:,0],[2.5,97.5])],"lead_mean_c":float(vals[:,1].mean()),"lead_ci95_c":[float(x) for x in np.percentile(boots[:,1],[2.5,97.5])],"uncertainty":"bootstrap of event-day mean paired contrasts; 1000 resamples, seed 42"}

print(json.dumps({"rows":len(d),"main":run(100.0),"threshold_sensitivity":run(150.0)},separators=(",",":"),allow_nan=False))