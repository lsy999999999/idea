import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/sources/uci_381_data.csv')
TABLES={"main":DF}
import json, numpy as np, pandas as pd
x=DF.sort_values("No").reset_index(drop=True).copy()
required={"No","year","month","hour","pm2.5","cbwd","Iws","DEWP","TEMP","PRES"}
assert required.issubset(x.columns)
x["episode"]=-1; eid=0; i=0
while i<len(x):
    if pd.isna(x.at[i,"pm2.5"]) or x.at[i,"pm2.5"]<150: i+=1; continue
    x.at[i,"episode"]=eid; j=i+1
    while j<len(x) and x.at[j,"No"]==x.at[j-1,"No"]+1 and pd.notna(x.at[j,"pm2.5"]) and x.at[j,"pm2.5"]>=150:
        x.at[j,"episode"]=eid; j+=1
    eid+=1; i=j
rows=[]
for eid,g in x[x.episode>=0].groupby("episode",sort=True):
    inds=g.index.to_list()
    anchor=next((k for k in inds if k+6<len(x) and all(x.at[q,"No"]==x.at[q-1,"No"]+1 and pd.notna(x.at[q,"pm2.5"]) for q in range(k+1,k+7))),None)
    if anchor is None or anchor==0 or x.at[anchor-1,"No"]!=x.at[anchor,"No"]-1: continue
    ev=x.at[anchor-1,"cbwd"]=="cv" and x.at[anchor,"cbwd"]!="cv" and x.at[anchor,"Iws"]>x.at[anchor-1,"Iws"]
    clean=not any(x.at[q-1,"cbwd"]=="cv" and x.at[q,"cbwd"]!="cv" and x.at[q,"Iws"]>x.at[q-1,"Iws"] for q in range(anchor,anchor+7))
    if not ev and not clean: continue
    z=x.loc[anchor]; prev=x.at[anchor-1,"pm2.5"]
    if pd.isna(prev): continue
    rows.append({"episode":int(eid),"year":int(z.year),"month":int(z.month),"hour":int(z.hour),"treated":int(ev),"y":int(all(x.at[q,"pm2.5"]>=150 for q in range(anchor+1,anchor+7))),"pm":float(z["pm2.5"]),"lag1":float(prev),"temp":float(z.TEMP),"dewp":float(z.DEWP),"pres":float(z.PRES),"iws":float(z.Iws)})
a=pd.DataFrame(rows)
r={"eligible_episodes":len(a),"treated_episodes":int(a.treated.sum()) if len(a) else 0,"control_episodes":int((1-a.treated).sum()) if len(a) else 0,"unmatched_continuation_rates":{},"matched_pairs":0,"matched_difference_treated_minus_control":None,"month_block_bootstrap_95pct":None}
if len(a):
    r["unmatched_continuation_rates"]={str(k):float(v) for k,v in a.groupby("treated").y.mean().items()}
    cols=["pm","lag1","temp","dewp","pres","iws"]; mu=a[cols].mean(); sd=a[cols].std().replace(0,1).fillna(1); a[cols]=(a[cols]-mu)/sd
    tr=a[a.treated==1].sort_values(["year","month","hour"]); co=a[a.treated==0].copy(); pairs=[]
    for _,t in tr.iterrows():
        pool=co[(co.month.sub(1)//3)==((t.month-1)//3)]; pool=pool[(pool.hour//6)==(t.hour//6)]
        if pool.empty: continue
        cidx=((pool[cols]-t[cols])**2).sum(axis=1).idxmin(); c=co.loc[cidx]
        pairs.append({"delta":float(t.y-c.y),"block":str(int(t.year))+"-"+str(int(t.month))}); co=co.drop(cidx)
    r["matched_pairs"]=len(pairs)
    if pairs:
        r["matched_difference_treated_minus_control"]=float(np.mean([p["delta"] for p in pairs]))
        rng=np.random.default_rng(381); blocks=sorted(set(p["block"] for p in pairs)); boots=[]
        for _ in range(1000):
            sampled=rng.choice(blocks,size=len(blocks),replace=True); vals=[p["delta"] for b in sampled for p in pairs if p["block"]==b]
            if vals: boots.append(float(np.mean(vals)))
        r["month_block_bootstrap_95pct"]=[float(np.quantile(boots,.025)),float(np.quantile(boots,.975))] if boots else None
print(json.dumps(r,separators=(",",":")))