"""Meaningful simulator-free contract checks before research inference."""
import copy
from pathlib import Path
import tempfile
import numpy as np
from model_language import Model
from tools import complete_model
from experiment_tools import make_offers,validate_selection,equal_features,scoped_capacity,key

def run():
    checks=[]
    def check(name,value):
        assert value,name
        checks.append(dict(name=name,passed=True))
    base=dict(u=0.,h=.7,history=[0.,0.,0.,0.],times=[-4.,-3.,-2.,-1.],dt=1.)
    premise=dict(measurement_stable=True,shared_parameters=True,deterministic_response_assumption=True)
    request=dict(parameters=[],quantities=[],features=['u','h','history[0]','history[3]'],degree=1)
    a=copy.deepcopy(base);b=copy.deepcopy(base);a['history'][1]=-1.;b['history'][1]=1.
    check('endpoint features provably merge middle-history intervention',equal_features(request,a,b))
    weighted=dict(parameters=[dict(name='duration',lower=.1,initial=1.,upper=8.)],quantities=[],features=['sum(history*exp(times/duration))'],degree=1)
    check('symbolic parameter representation does not merge changed middle input',not equal_features(weighted,a,b))
    def candidate(cid,feature):
        scaffold=dict(parameters=[dict(name='gain',dimension=[0,1],lower=-2.,initial=1.,upper=2.)],quantities=[],exposed_inputs=['u','history'])
        return dict(id=cid,request=dict(parameters=[],quantities=[],features=[feature],degree=1),scaffold=scaffold,expression='gain*'+feature,values=[1.])
    cs=[candidate('A','u'),candidate('B','history[1]')]
    offers=make_offers(cs,[])
    check('model disagreement creates usable experiment offers',bool(offers) and all(o['predicted_contrast_disagreement']>.06 for o in offers))
    selected=validate_selection(dict(offer_ids=[offers[0]['id']],manual_pairs=[]),offers,cs,[])
    check('valid novel pair accepted',len(selected['selected'])==1 and not selected['rejected'])
    duplicate=validate_selection(dict(offer_ids=[offers[0]['id']],manual_pairs=[]),offers,cs,[offers[0]['designs'][0]])
    check('observed condition rejected before acquisition',not duplicate['selected'] and bool(duplicate['rejected']))
    no_gap=copy.deepcopy(offers[0]);no_gap['predicted_contrast_disagreement']=0.
    rejected=validate_selection(dict(offer_ids=[no_gap['id']],manual_pairs=[]),[no_gap],cs,[])
    check('non-discriminating offer rejected',not rejected['selected'])
    rows=[dict(a,row_id='a'+str(i),condition=0,pair_id='E1',repeat=i,o=-.5) for i in range(4)]+[dict(b,row_id='b'+str(i),condition=1,pair_id='E1',repeat=i,o=.5) for i in range(4)]
    dev=[dict(base,u=float(i),row_id='d'+str(i),o=0.) for i in range(100)]
    cap=scoped_capacity(request,dev,rows,premise)
    check('new pair bound prevents complete-response search',not cap['completion_enabled'] and cap['experiment_scopes'][0]['minimum_possible_dev_rmse']>.06)
    check('premise withdrawal retracts hard completion refusal',scoped_capacity(request,dev,rows,dict(premise,measurement_stable=False))['completion_enabled'])
    train=[dict(base,u=float(u),row_id='t'+str(i),o=.2+.8*u+.3*u**3) for i,u in enumerate(np.linspace(-1,1,15))]
    req=dict(parameters=[],quantities=[],features=['u'],degree=3)
    with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
        budget=dict(residual_calls=0,linear_solves=0)
        result,pool=complete_model(req,train,train,premise,Path(tmp)/'missing'/'nested'/'trials.jsonl',budget)
        check('nested trace directory created and model completed',result['status']=='completed' and bool(pool))
    c=result['best'];m=Model(c['scaffold'],c['expression'])
    check('completed declared model replays reported fit',np.sqrt(np.mean((m.predict(train,c['values'])-[r['o'] for r in train])**2))<1e-10)
    check('shared parameter binding includes auto coefficients',len(c['values'])==len(c['scaffold']['parameters'])<=8)
    for o in offers:
        for c in cs:
            p=Model(c['scaffold'],c['expression']).predict(o['designs'],c['values'])
            check('offered predictions bind to '+o['id']+'/'+c['id'],np.max(np.abs(p-o['predictions'][c['id']]))<1e-12)
    return checks
