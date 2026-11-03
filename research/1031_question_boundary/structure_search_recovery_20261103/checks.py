"""Meaningful safety/semantics checks; no research-model inference."""
import copy
import numpy as np
from model_language import Model, capacity_audit, fit


def run():
    checks = []
    def check(name, condition):
        assert condition, name
        checks.append(dict(name=name, passed=True))
    def reject(name, fn):
        try: fn()
        except (ValueError, SyntaxError, KeyError): check(name, True); return
        raise AssertionError('Invalid model was accepted: ' + name)
    p = dict(name='gain', dimension=[0,1], lower=-5., initial=1., upper=5.)
    sc = dict(parameters=[p], quantities=[], exposed_inputs=['u'])
    row = dict(u=.5,h=.7,history=[1.,2.,3.,4.],times=[-4.,-3.,-2.,-1.],dt=1.)
    m = Model(sc,'gain*u')
    check('named coefficient predicts exact raw response', m.predict([row],[3.])[0] == 1.5)
    reject('undefined parameter', lambda: Model(sc,'missing*u'))
    reject('unexposed raw input', lambda: Model(sc,'gain*h'))
    reject('wrong output dimension', lambda: Model(sc,'u'))
    reject('function arity', lambda: Model(sc,'gain*exp(u,u)'))
    reject('attribute access', lambda: Model(sc,'gain*u.real'))
    reject('vector response', lambda: Model(dict(sc,exposed_inputs=['history']),'gain*history'))
    reject('dimensionful transcendental', lambda: Model(dict(sc,exposed_inputs=['h']),'gain*exp(h)'))
    rows = [dict(row,row_id='a',o=.4),dict(row,history=[4.,3.,2.,1.],row_id='b',o=-.4)]
    inv = dict(parameters=[dict(name='scale',dimension=[0,0],lower=.1,initial=1.,upper=3.)],
               quantities=[dict(name='summary',expression='scale*mean(history)')],exposed_inputs=['u','h'])
    premises = dict(shared_parameters=True,deterministic_response_assumption=True,measurement_stable=True)
    a = capacity_audit(inv,rows,premises)
    check('parameter-symbolic collision gives full-set floor', abs(a['guaranteed_dev_rmse_lower_bound']-.4)<1e-12 and not a['finish_enabled'])
    richer = copy.deepcopy(inv);richer['exposed_inputs'].append('history')
    check('raw information restores finish operation', capacity_audit(richer,rows,premises)['finish_enabled'])
    check('premise withdrawal restores operation', capacity_audit(inv,rows,dict(premises,measurement_stable=False))['finish_enabled'])
    varied = copy.deepcopy(inv);varied['quantities'][0]['expression']='scale*history[0]'
    varied['parameters'][0].update(lower=-1.,initial=0.,upper=1.)
    check('initial numeric coincidence not used as symbolic proof', capacity_audit(varied,rows,premises)['finish_enabled'])
    train = [dict(row,u=float(x),o=2.*x,row_id=str(i)) for i,x in enumerate([-.9,-.3,.2,.8])]
    result=fit(sc,'gain*u',train,train)
    check('fit bindings and exact computed quantity', result['dev_rmse']<1e-8 and abs(result['parameters']['gain']-2)<1e-7)
    check('actual numerical evaluation budget', result['residual_calls']<=1600 and all(x['calls']<=400 for x in result['attempts']))
    check('formula renderer comes from executable expression', result['manifest']['response']=='gain * u')
    return checks


if __name__ == '__main__':
    import json
    print(json.dumps(run(),indent=2))
