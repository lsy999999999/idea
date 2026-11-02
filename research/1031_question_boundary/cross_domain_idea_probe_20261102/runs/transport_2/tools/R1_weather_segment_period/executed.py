import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/sources/uci_275_data.csv')
TABLES={"main":DF}
import json
import numpy as np
import pandas as pd

x=DF.copy()
x["_w"]=1.0
x['period']=np.where((x.workingday.eq(0)) & x.hr.between(10,18),'leisure',np.where(x.workingday.eq(1) & (x.hr.between(7,9)|x.hr.between(16,18)),'commute','other'))
x=x[x.period.ne('other')].copy()
x['wx']=np.where(x.weathersit.isin([3,4]),1,np.where(x.weathersit.isin([1,2]),0,-1))
x=x[x.wx.ge(0)].copy()
keys=['yr','mnth','weekday','hr']
def estimate(z):
 out={}
 for p in ['leisure','commute']:
  q=z[z.period.eq(p)]
  a=q.groupby(keys+['wx']).agg(n=('_w','sum'),c=('casual','sum'),r=('registered','sum')).reset_index()
  wide=a.pivot_table(index=keys,columns='wx',values='n',fill_value=0)
  if 0 not in wide.columns or 1 not in wide.columns: out[p]=None; continue
  common=wide.index[(wide[0]>0)&(wide[1]>0)]
  a=a.set_index(keys).loc[common].reset_index()
  if len(common)==0: out[p]=None; continue
  ns=a.groupby(keys).n.sum(); w=ns/ns.sum()
  vals={}
  for seg,col in [('casual','c'),('registered','r')]:
   rates=[]
   for wx in [0,1]:
    b=a[a.wx.eq(wx)].set_index(keys)
    rates.append(float((w*b[col].div(b.n)).sum()))
   vals[seg]=float(np.log(rates[1]/rates[0]))
  out[p]={'support_strata':int(len(common)),'casual_log_rr':vals['casual'],'registered_log_rr':vals['registered'],'segment_log_rr_difference':vals['casual']-vals['registered']}
 out['triple_contrast']=None if out['leisure'] is None or out['commute'] is None else out['leisure']['segment_log_rr_difference']-out['commute']['segment_log_rr_difference']
 return out
point=estimate(x)
cat_counts=x.groupby(['period','weathersit']).size().rename('hour_rows').reset_index().to_dict('records')
dates=x.dteday.unique(); rng=np.random.default_rng(731); boots=[]
for _ in range(300):
 draw=rng.choice(dates,size=len(dates),replace=True); mult=pd.Series(draw).value_counts(); z=x.copy(); z['_w']=z.dteday.map(mult).fillna(0); z=z[z._w.gt(0)].copy()
 z['casual']=z.casual*z._w; z['registered']=z.registered*z._w
 e=estimate(z)
 if e['triple_contrast'] is not None: boots.append(e['triple_contrast'])
ci=np.quantile(boots,[0.025,0.975]).tolist() if len(boots)>=30 else None
print(json.dumps({'n_rows':int(len(x)),'n_dates':int(x.dteday.nunique()),'weather_category_hour_rows':cat_counts,'estimate':point,'date_bootstrap_replicates_valid':len(boots),'triple_contrast_percentile_95_interval':ci},separators=(',',':')))