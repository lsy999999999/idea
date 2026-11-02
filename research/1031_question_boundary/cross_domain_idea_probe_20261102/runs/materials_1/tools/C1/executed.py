import pandas as pd
DF=pd.read_csv('/Applications/ideas/research/1031_question_boundary/cross_domain_idea_probe_20261102/sources/uci_165_data.csv')
TABLES={"main":DF}
import json
import numpy as np
cols=['Cement','Blast Furnace Slag','Fly Ash','Water','Superplasticizer','Coarse Aggregate','Fine Aggregate']
target='Concrete compressive strength'
d=DF.copy()
keys=d[cols].apply(lambda r: tuple(r.tolist()),axis=1)
d['_recipe']=keys
d['_scm']=(d['Blast Furnace Slag']+d['Fly Ash'])/(d['Cement']+d['Blast Furnace Slag']+d['Fly Ash'])
recipe_age=d.groupby(['_recipe','Age'],sort=False).agg(strength=(target,'mean'),scm=('_scm','first')).reset_index()
ages=sorted(int(x) for x in d['Age'].unique())
counts={str(a):{'rows':int((d['Age']==a).sum()),'recipes':int(recipe_age.loc[recipe_age.Age==a,'_recipe'].nunique())} for a in ages}
wide=recipe_age.pivot(index='_recipe',columns='Age',values='strength')
scm=recipe_age.groupby('_recipe').scm.first()
out={'n_rows':int(len(d)),'n_recipes':int(len(scm)),'recipes_repeated_across_ages':int((recipe_age.groupby('_recipe').Age.nunique()>1).sum()),'age_counts':counts,'intervals':{}}
for a,b in [(1,7),(7,28),(28,56)]:
 name=f'{a}-{b}'
 if a in wide.columns and b in wide.columns:
  gain=(wide[b]-wide[a]).dropna(); s=scm.loc[gain.index]; zero=gain[s==0]; nonzero=gain[s>0]
  corr=float(np.corrcoef(s.to_numpy(),gain.to_numpy())[0,1]) if len(gain)>1 and np.std(s)>0 and np.std(gain)>0 else None
  def stats(x): return {'n_recipes':int(len(x)),'mean_MPa':float(x.mean()) if len(x) else None,'median_MPa':float(x.median()) if len(x) else None}
  out['intervals'][name]={'n_with_pair':int(len(gain)),'missing_pairs_of_all_recipes':int(len(scm)-len(gain)),'zero_SCM':stats(zero),'nonzero_SCM':stats(nonzero),'SCM_share_gain_Pearson_r':corr,'status':'descriptive; recipe recurrence is not verified batch linkage'}
 else:
  out['intervals'][name]={'n_with_pair':0,'missing_pairs_of_all_recipes':int(len(scm)),'zero_SCM':{'n_recipes':0,'mean_MPa':None,'median_MPa':None},'nonzero_SCM':{'n_recipes':0,'mean_MPa':None,'median_MPa':None},'SCM_share_gain_Pearson_r':None,'status':'endpoint age absent; comparison infeasible'}
print(json.dumps(out,separators=(',',':'),allow_nan=False))