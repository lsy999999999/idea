import copy
from pathlib import Path
import tempfile
import numpy as np
from tools import FeatureProgram,infer_units,representation_check,complete_model,automatic_library
from model_language import Model


def run():
    checks=[]
    def check(name,value):assert value,name;checks.append(dict(name=name,passed=True))
    params=[dict(name='duration',lower=.1,initial=1.,upper=10.)]
    q=[dict(name='state',expression='sum(history*exp(times/duration))')]
    inferred,_=infer_units(params,q,['u','state'])
    check('time parameter dimension inferred from expression',inferred[0]['dimension']==[1,0])
    p=[dict(name='gain',lower=-5.,initial=1.,upper=5.),dict(name='offset',lower=-5.,initial=0.,upper=5.)]
    inferred,_=infer_units(p,[],[],expression='offset+gain*h')
    check('response coefficients infer different dimensions',inferred[0]['dimension']==[-1,1] and inferred[1]['dimension']==[0,1])
    try:infer_units([],[],['exp(h)']);ok=False
    except ValueError:ok=True
    check('unit inference does not bless dimensionally invalid feature',ok)
    row=dict(u=.5,h=.7,history=[1.,0.,0.,0.],times=[-4.,-3.,-2.,-1.],dt=1.)
    rows=[dict(row,row_id='a',o=.1),dict(row,history=[0.,0.,0.,1.],row_id='b',o=.9)]
    premise=dict(measurement_stable=True,shared_parameters=True,deterministic_response_assumption=True)
    request=dict(parameters=[],quantities=[],features=['u','h','sum(history)'],degree=1)
    a=representation_check(request,rows,premise)
    check('mean or sum cannot hide order witness',not a['can_meet_threshold'] and abs(a['minimum_possible_dev_rmse']-.4)<1e-12)
    request2=dict(parameters=params,quantities=q,features=['u','state'],degree=1)
    check('parameter-symbolic representation can preserve order',representation_check(request2,rows,premise)['can_meet_threshold'])
    check('premise withdrawal removes hard refusal',representation_check(request,rows,dict(premise,measurement_stable=False))['can_meet_threshold'])
    hidden_internal=dict(parameters=params,quantities=q,features=['sum(history)'],degree=1)
    check('unused informative internal quantity cannot fool representation test',not representation_check(hidden_internal,rows,premise)['can_meet_threshold'])
    train=[dict(row,u=float(u),h=.3,history=[0.,0.,0.,0.],row_id=str(i),o=2*u+.4*u**3) for i,u in enumerate(np.linspace(-1,1,13))]
    request3=dict(parameters=[],quantities=[],features=['u'],degree=3)
    with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
        budget=dict(residual_calls=0,linear_solves=0)
        result,candidates=complete_model(request3,train,train,premise,Path(tmp)/'trials.jsonl',budget)
    check('tool invents and binds linear coefficients',result['status']=='completed' and result['best']['dev_rmse']<1e-10)
    best=result['best'];m=Model(best['scaffold'],best['expression'])
    check('generated model predicts its declared target',np.max(np.abs(m.predict(train,best['values'])-[r['o'] for r in train]))<1e-9)
    check('parameter cap includes automatic coefficients',len(best['values'])<=8)
    check('all least-squares solves counted',budget['linear_solves']>0 and budget['residual_calls']<=1600)
    # Two independently varied variables prevent a missing feature from being
    # passed merely because current fit records happen to correlate it with u.
    try:FeatureProgram(dict(request3,features=['missing']));ok=False
    except ValueError:ok=True
    check('unknown feature symbols fail explicitly',ok)
    library=automatic_library();fp=FeatureProgram(library)
    check('automatic library uses a generic typed raw-input grammar',len(fp.features)>40 and len(fp.features)<=200 and fp.parameters[0]['dimension']==[1,0])
    # A simulator-free nonlinear example verifies profile fitting and final-point
    # binding rather than a derivative-probe vector from the optimizer.
    tr=[dict(row,h=float(h),u=0.,history=[0.,0.,0.,0.],row_id='t'+str(i),o=1.3*np.exp(-h/1.7)) for i,h in enumerate(np.linspace(0,2,15))]
    rq=dict(parameters=[dict(name='period',lower=.1,initial=1.,upper=8.)],quantities=[],features=['exp(-h/period)'],degree=1)
    with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
        b=dict(residual_calls=0,linear_solves=0);res,models=complete_model(rq,tr,tr,premise,Path(tmp)/'trials.jsonl',b)
    check('variable projection fits nonlinear parameter on fit',res['status']=='completed' and res['best']['train_rmse']<1e-7)
    best=res['best'];model=Model(best['scaffold'],best['expression'])
    check('returned fit point and recorded metric agree',abs(np.sqrt(np.mean((model.predict(tr,best['values'])-[r['o'] for r in tr])**2))-best['train_rmse'])<1e-12)
    check('nonlinear search respects residual and linear-solve caps',b['residual_calls']<=1600 and b['linear_solves']<=20000)
    return checks
