"""Model-based experiment offers and scoped representation checks; no simulator."""
import copy
import itertools
import math
import numpy as np
import sympy as sp
from model_language import Model
from tools import FeatureProgram,representation_check

COORDINATES=['u','h','history[0]','history[1]','history[2]','history[3]']

def key(r):return tuple([r['u'],r['h'],*r['history'],*r['times'],r['dt']])

def validate_design(r):
    if len(r['history'])!=4:raise ValueError('History length must be four')
    if not all(math.isfinite(v) for v in [r['u'],r['h'],*r['history']]):raise ValueError('Nonfinite design')
    if not -1.1<=r['u']<=1.1 or not 0<=r['h']<=2.5 or any(not -1<=x<=1 for x in r['history']):raise ValueError('Outside controllable input range')
    return dict(u=r['u'],h=r['h'],history=r['history'],times=[-4.,-3.,-2.,-1.],dt=1.)

def equal_features(request,a,b):
    """Exact symbolic equality is a sufficient certificate, not a full solver."""
    fp=FeatureProgram(request);values=[sp.Symbol(p['name'],real=True) for p in fp.parameters]
    v=fp.matrix([a,b],values,True)
    return all(sp.srepr(x)==sp.srepr(y) for x,y in zip(v[0],v[1]))

def predict(candidate,designs):return Model(candidate['scaffold'],candidate['expression']).predict(designs,candidate['values'])

def describe_pair(a,b,candidates):
    predictions={};contrasts={};equal={}
    for c in candidates:
        p=predict(c,[a,b]).tolist();predictions[c['id']]=p;contrasts[c['id']]=float(p[1]-p[0])
        try:equal[c['id']]=equal_features(c['request'],a,b)
        except Exception:equal[c['id']]=None
    spread=max(contrasts.values())-min(contrasts.values()) if contrasts else 0.
    return dict(designs=[a,b],predictions=predictions,predicted_contrasts=contrasts,
                predicted_contrast_disagreement=spread,symbolically_equal_features=equal)

def make_offers(candidates,known,seed=41104001):
    if len(candidates)<2:return []
    rng=np.random.default_rng(seed);seen={key(r) for r in known};proposed=[]
    for coordinate in COORDINATES:
        local=[]
        for i in range(24):
            anchor=dict(u=float(rng.uniform(-1.1,1.1)),h=float(rng.uniform(0,2.5)),history=rng.uniform(-1,1,4).tolist(),times=[-4.,-3.,-2.,-1.],dt=1.)
            a=copy.deepcopy(anchor);b=copy.deepcopy(anchor)
            if coordinate=='u':a['u']=-1.1;b['u']=1.1
            elif coordinate=='h':a['h']=0.;b['h']=2.5
            else:
                j=int(coordinate[-2]);a['history'][j]=-1.;b['history'][j]=1.
            if key(a) in seen or key(b) in seen:continue
            try:item=describe_pair(a,b,candidates)
            except (ValueError,FloatingPointError,OverflowError,ZeroDivisionError):continue
            if item['predicted_contrast_disagreement']>.06:local.append(dict(item,varied_coordinate=coordinate))
        local.sort(key=lambda x:-x['predicted_contrast_disagreement'])
        proposed+=local[:2]
    proposed.sort(key=lambda x:-x['predicted_contrast_disagreement'])
    for i,p in enumerate(proposed):p['id']='E'+str(i+1)
    return proposed

def validate_selection(reply,offers,candidates,known):
    selected=[];rejected=[];seen={key(r) for r in known};lookup={o['id']:o for o in offers}
    requests=[dict(kind='offered',id=i) for i in reply['offer_ids']]+[dict(kind='manual',pair=p) for p in reply['manual_pairs']]
    if len(requests)>2:raise ValueError('At most two experiment pairs total')
    for index,r in enumerate(requests):
        try:
            if r['kind']=='offered':item=copy.deepcopy(lookup[r['id']])
            else:
                p=r['pair'];a=validate_design(p['a']);b=validate_design(p['b'])
                item=dict(describe_pair(a,b,candidates),id='manual_'+str(index),varied_coordinate='agent-specified')
            for d in item['designs']:validate_design(d)
            a,b=item['designs']
            if key(a)==key(b) or key(a) in seen or key(b) in seen:raise ValueError('Previously observed or duplicate condition; not a new intervention')
            if item['predicted_contrast_disagreement']<=.06:raise ValueError('Frozen candidate contrasts do not differ by more than 0.06')
            selected.append(item);seen.update([key(a),key(b)])
        except Exception as exc:rejected.append(dict(request=r,error=str(exc)))
    return dict(selected=selected,rejected=rejected)

def scoped_capacity(request,dev,experiment_rows,premises):
    pooled=representation_check(request,dev,premises)
    local=[]
    for pair_id in sorted({r['pair_id'] for r in experiment_rows}):
        rows=[r for r in experiment_rows if r['pair_id']==pair_id]
        result=representation_check(request,rows,premises)
        local.append(dict(pair_id=pair_id,**result))
    blocked=not pooled['can_meet_threshold'] or any(not x['can_meet_threshold'] for x in local)
    return dict(pooled=pooled,experiment_scopes=local,completion_enabled=not blocked,
                scope='A lower bound applies only to the stated dataset/pair and shared deterministic feature-response assumptions. No collision is not evidence of sufficiency.')

def experiment_feedback(selected,rows,candidates,premises):
    results=[]
    for item in selected:
        observed=[r for r in rows if r['pair_id']==item['id']]
        means=[float(np.mean([r['o'] for r in observed if r['condition']==i])) for i in [0,1]]
        delta=means[1]-means[0];models=[]
        for c in candidates:
            pred=item['predictions'][c['id']];floor=representation_check(c['request'],observed,premises)
            models.append(dict(candidate_id=c['id'],frozen_predictions=pred,frozen_contrast=pred[1]-pred[0],
              raw_rmse=float(np.sqrt(np.mean((predict(c,observed)-[r['o'] for r in observed])**2))),
              contrast_error=abs((pred[1]-pred[0])-delta),
              feature_collision=item['symbolically_equal_features'][c['id']],
              empirical_class_rmse_floor=floor['minimum_possible_dev_rmse'],class_can_meet_pair_threshold=floor['can_meet_threshold']))
        results.append(dict(pair_id=item['id'],varied_coordinate=item['varied_coordinate'],observed_means=means,observed_contrast=delta,
           noise_only_contrast_interval=[delta-.03,delta+.03],models=models))
    return results
