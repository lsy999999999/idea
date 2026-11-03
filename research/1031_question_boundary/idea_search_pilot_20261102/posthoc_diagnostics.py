"""Organizer postfreeze diagnostics; never feed back to generation or model judge."""
import json
from pathlib import Path
import subprocess
import sys
sys.dont_write_bytecode=True
import pilot as p
BASE=p.ROOT
REC=BASE/'format_recovery'
OUT=BASE/'organizer_diagnostics'

def coefficient():
    source=REC/'runs/wine_C/r2/tools/compute_0/executed.py'
    text=source.read_text();old='return r.x[3],bool(r.success)';new='return r.x[2],bool(r.success)'
    assert text.count(old)==1
    folder=OUT/'wine_C_r2_coefficient';folder.mkdir(parents=True,exist_ok=True)
    fixed=folder/'corrected_index_only.py';p.write(fixed,text.replace(old,new))
    p.write(folder/'DIAGNOSTIC_DESIGN.json',{'time':p.now(),'original_code':str(source),'original_sha256':p.sha(source),'corrected_sha256':p.sha(fixed),'columns':['volatile_acidity','citric_acid','volatile_acidity_times_citric_acid','fixed_acidity','residual_sugar','chlorides','free_sulfur_dioxide','total_sulfur_dioxide','density','pH','sulphates','alcohol'],'original_extracted_index':3,'correct_interaction_index':2,'change':'Only output coefficient selection; fitting, rows, standardization, 80 bootstrap samples, seeds and loss unchanged','scope':'Postfreeze organizer diagnostic; not an actor repair or an independent confirmatory scientific experiment'})
    proc=subprocess.run([p.PYTHON,str(fixed)],capture_output=True,text=True,timeout=60,env={'PATH':'/opt/homebrew/bin:/usr/bin:/bin','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','PYTHONDONTWRITEBYTECODE':'1'},cwd=folder)
    p.write(folder/'stdout.txt',proc.stdout);p.write(folder/'stderr.txt',proc.stderr)
    assert proc.returncode==0
    p.write(folder/'RESULT.json',json.loads(proc.stdout))
    print(proc.stdout,flush=True)

def ties():
    import pandas as pd
    import numpy as np
    df=pd.read_csv(REC/'setup/uci468.csv')
    total=df[['Administrative_Duration','Informational_Duration','ProductRelated_Duration']].sum(axis=1)
    x=df.loc[total>0].copy();x['share']=x.ProductRelated_Duration/total.loc[total>0]
    x['rank_decile']=pd.qcut(x['share'].rank(method='first'),10,labels=False)
    grouped=x.groupby('rank_decile').agg(n=('Revenue','size'),share_min=('share','min'),share_max=('share','max'),unique_shares=('share','nunique'),conversion_rate=('Revenue','mean'))
    value_groups=x.groupby('share').Revenue.agg(['size','mean'])
    one=value_groups.loc[1.0]
    x['tie_preserving_bin']=pd.qcut(x['share'],10,duplicates='drop')
    grouped2=x.groupby('tie_preserving_bin',observed=True).agg(n=('Revenue','size'),share_min=('share','min'),share_max=('share','max'),conversion_rate=('Revenue','mean'))
    result={'time':p.now(),'scope':'Postfreeze diagnostic of the reported decile interpretation; no claim about adjusted nonlinearity','n':len(x),'share_exactly_one':{'n':int(one['size']),'conversion_rate':float(one['mean'])},'rank_bins':json.loads(grouped.reset_index().to_json(orient='records')),'tie_preserving_bins':json.loads(grouped2.reset_index(drop=True).to_json(orient='records'))}
    p.write(OUT/'shopping_C_r3_ties.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':{'coefficient':coefficient,'ties':ties}[sys.argv[1]]()
