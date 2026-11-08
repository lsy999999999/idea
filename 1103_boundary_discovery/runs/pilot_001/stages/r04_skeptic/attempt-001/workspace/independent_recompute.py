#!/usr/bin/env python3
"""Independent reconstruction of the frozen 14092500 daily analysis."""
from pathlib import Path
import json
import numpy as np
import pandas as pd

ROOT = Path('/Applications/ideas/1103_boundary_discovery/runs/pilot_001/stages/r03_experimentalist/attempt-001/workspace')
OUT = Path(__file__).resolve().parent
SITE, NOAA = '14092500', 'USC00356532'
START, TRAIN_END, END = '2014-01-01', '2018-12-31', '2023-12-31'
SEED, B = 20261103, 2000

def read_rdb(path):
    lines = path.read_text(errors='replace').splitlines()
    i = next(i for i,x in enumerate(lines) if x.startswith('agency_cd\t'))
    return pd.read_csv(path, sep='\t', skiprows=lambda row: row < i or row == i + 1, dtype=str)

def parse_dly(path):
    rows=[]; rejected_qflags=0
    for line in path.read_text(errors='replace').splitlines():
        if line[:11] != NOAA or line[17:21] not in ('TMAX','TMIN'):
            continue
        elem=line[17:21].lower(); y=int(line[11:15]); m=int(line[15:17])
        for d in range(1,32):
            f=line[21+8*(d-1):29+8*(d-1)]
            if len(f)!=8 or int(f[:5])==-9999: continue
            if f[6].strip():
                rejected_qflags += 1
                continue
            try: date=pd.Timestamp(y,m,d)
            except ValueError: continue
            rows.append((date,elem,int(f[:5])/10.0,f[5].strip(),f[6].strip(),f[7].strip()))
    long=pd.DataFrame(rows,columns=['date','element','value','mflag','qflag','sflag'])
    # Preserve flag per element/day; duplicate keys are checked, never silently collapsed.
    if long.duplicated(['date','element']).any(): raise ValueError('duplicate NOAA date-element')
    vals=long.pivot(index='date',columns='element',values='value').rename(columns={'tmax':'tmax','tmin':'tmin'})
    for e in ('tmax','tmin'):
        flags=long[long.element.eq(e)].set_index('date')
        for flag in ('mflag','qflag','sflag'): vals[f'{e}_{flag}']=flags[flag]
    return vals.reset_index(), long, rejected_qflags

def fit(train,test,y,add_range):
    mt=pd.get_dummies(train.date.dt.month,prefix='month',dtype=float)
    mv=pd.get_dummies(test.date.dt.month,prefix='month',dtype=float).reindex(columns=mt.columns,fill_value=0.)
    cols=['air_mean','log_flow']+(['air_range'] if add_range else [])
    xtr=np.column_stack([np.ones(len(train)),mt.to_numpy(),train[cols].to_numpy(float)])
    xte=np.column_stack([np.ones(len(test)),mv.to_numpy(),test[cols].to_numpy(float)])
    beta,*_=np.linalg.lstsq(xtr,train[y].to_numpy(float),rcond=None)
    return xte@beta, int(np.linalg.matrix_rank(xtr)), xtr.shape[1]

def mae(y,p): return float(np.mean(np.abs(np.asarray(y)-np.asarray(p))))

def bootstrap(df,y,bcol,fcol):
    rng=np.random.default_rng(SEED); diffs=[]; year_rows={}
    groups={int(yr):g.reset_index(drop=True) for yr,g in df.groupby(df.date.dt.year,sort=True)}
    for yr,g in groups.items(): year_rows[str(yr)]=len(g)
    for _ in range(B):
        parts=[]
        for yr,g in groups.items():
            dates=pd.DatetimeIndex(g.date); n=len(g)
            ends=dates.searchsorted(dates+pd.Timedelta(days=28),side='left')
            ids=[]
            while len(ids)<n:
                s=int(rng.integers(0,n)); ids.extend(range(s,max(s+1,int(ends[s]))))
            parts.append(g.iloc[ids[:n]])
        z=pd.concat(parts,ignore_index=True)
        diffs.append(mae(z.observed,z[bcol])-mae(z.observed,z[fcol]))
    a=np.asarray(diffs)
    return {'mean_c':float(a.mean()),'ci95_c':[float(np.quantile(a,.025)),float(np.quantile(a,.975))],
            'replicates':B,'seed':SEED,'years_preserved_row_counts':year_rows}

def main():
    u=read_rdb(ROOT/f'data/usgs_daily_2014_2023_{SITE}.rdb')
    suffix={'water_max':'00010_00001','water_min':'00010_00002','water_mean':'00010_00003','flow':'00060_00003'}
    cols={}
    for k,s in suffix.items():
        found=[c for c in u.columns if c.endswith(s)]
        if len(found)!=1: raise ValueError((k,found))
        cols[k]=found[0]
    p=pd.DataFrame({'date':pd.to_datetime(u.datetime,errors='raise')}); qc={}
    for k,c in cols.items():
        q=c+'_cd'; p[k]=pd.to_numeric(u[c],errors='coerce'); p[k+'_qualifier']=u[q].fillna('')
        ok=p[k+'_qualifier'].str.startswith('A')
        qc[k]={'all_nonmissing':int(p[k].notna().sum()),'approved_A_prefix':int((p[k].notna()&ok).sum()),
               'approved_Ae':int((p[k].notna()&p[k+'_qualifier'].eq('A:e')).sum()),
               'rejected_non_A':int((p[k].notna()&~ok).sum())}
        p.loc[~ok,k]=np.nan
    air,long,rejected_qflags=parse_dly(ROOT/f'data/{NOAA}.dly')
    p=p.merge(air,on='date',how='inner',validate='one_to_one')
    p['air_mean']=(p.tmax+p.tmin)/2; p['air_range']=p.tmax-p.tmin
    p['water_range']=p.water_max-p.water_min; p['log_flow']=np.where(p.flow>0,np.log10(p.flow),np.nan)
    p['month']=p.date.dt.month
    targets=['water_range','water_mean','water_max']
    valid=p[targets+['air_mean','air_range','log_flow']].notna().all(axis=1)&p.flow.gt(0)
    n_excluded=int((~valid).sum()); p=p.loc[valid].sort_values('date').reset_index(drop=True)
    p.to_csv(OUT/'independent_paired_panel.csv',index=False)
    tr=p[p.date.le(TRAIN_END)].copy(); te=p[p.date.gt(TRAIN_END)].copy()
    pred=pd.DataFrame({'date':te.date})
    metrics={}; rows=[]
    for y in targets:
        b,rank_b,dim_b=fit(tr,te,y,False); f,rank_f,dim_f=fit(tr,te,y,True)
        pred['observed_'+y]=te[y].to_numpy(); pred['baseline_'+y]=b; pred['with_air_range_'+y]=f
        d=mae(te[y],b)-mae(te[y],f)
        boot=bootstrap(pd.DataFrame({'date':te.date,'observed':te[y].to_numpy(),'b':b,'f':f}),y,'b','f')
        metrics[y]={'test_n':len(te),'baseline_mae_c':mae(te[y],b),'with_air_range_mae_c':mae(te[y],f),
                    'difference_mae_baseline_minus_amplitude_c':d,'bootstrap':boot,
                    'design_baseline_rank_cols':[rank_b,dim_b],'design_expanded_rank_cols':[rank_f,dim_f]}
        rows.append({'response':y,'baseline_MAE_C':mae(te[y],b),'expanded_MAE_C':mae(te[y],f),'MAE_gain_C':d,
                     'block_CI_low':boot['ci95_c'][0],'block_CI_high':boot['ci95_c'][1],
                     'baseline_rank/cols':f'{rank_b}/{dim_b}','expanded_rank/cols':f'{rank_f}/{dim_f}'})
    pred.to_csv(OUT/'independent_daily_predictions.csv',index=False)
    pd.DataFrame(rows).to_csv(OUT/'metrics_table.csv',index=False)
    counts={f'{e}_{flag}':int((long[long.element.eq(e)][flag].fillna('').astype(str).str.strip()!='').sum())
            for e in ('tmax','tmin') for flag in ('mflag','qflag','sflag')}
    result={'status':'independent_recompute_complete','source_files':{
        'usgs_rdb':str(ROOT/f'data/usgs_daily_2014_2023_{SITE}.rdb'),'ghcn_dly':str(ROOT/f'data/{NOAA}.dly')},
        'usgs_columns':cols,'units':'USGS water temperature deg C; discharge cfs; GHCN tenths deg C converted to deg C',
        'quality_counts':qc,'noaa_flag_nonblank_counts_all_parsed_elements':counts,
        'noaa_nonmissing_qflag_rows_excluded_by_parser':rejected_qflags,
        'raw_usgs_rows':len(u),'noaa_qualified_daily_rows':len(air),'post_quality_common_rows':len(p)+n_excluded,
        'common_case_excluded':n_excluded,'paired_n':len(p),'train_n':len(tr),'test_n':len(te),
        'first_date':str(p.date.min().date()),'last_date':str(p.date.max().date()),'metrics':metrics,
        'paired_gap_dates':int((p.date.diff().dt.days.fillna(1)>1).sum()),
        'notes':'NOAA mflag/sflag preserved and counted; qflag must be blank; positive cfs; all target models use identical common-case rows. Monthly dummy columns plus intercept are rank deficient but numpy lstsq yields unique fitted projections.'}
    (OUT/'independent_results.json').write_text(json.dumps(result,indent=2)+'\n')
    # Compare saved panels and predictions on exact key and numeric columns.
    orig=pd.read_csv(ROOT/'paired_daily_panel.csv',parse_dates=['date'])
    saved=pd.read_csv(ROOT/'daily_predictions.csv',parse_dates=['date'])
    panel_common=[c for c in p.columns if c in orig.columns and c!='date' and
                  pd.api.types.is_numeric_dtype(p[c]) and pd.api.types.is_numeric_dtype(orig[c])]
    comp={'panel_same_dates':bool(orig.date.equals(p.date)),
          'panel_compared_numeric_columns':panel_common,
          'panel_numeric_max_abs_diff':float(np.nanmax(np.abs(orig[panel_common].to_numpy(float)-p[panel_common].to_numpy(float)))),
          'prediction_same_dates':bool(saved.date.reset_index(drop=True).equals(pred.date.reset_index(drop=True)))}
    common=[c for c in pred.columns if c in saved.columns and c!='date']
    comp['prediction_max_abs_diff']=float(np.nanmax(np.abs(saved[common].to_numpy(float)-pred[common].to_numpy(float))))
    result['comparison_to_saved']=comp
    (OUT/'independent_results.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__': main()
