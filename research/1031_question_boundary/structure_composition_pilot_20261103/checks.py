import copy
import numpy as np
from model_language import Model
from structure_tools import additive_certificate,allowed_operations,membership,assemble


def run():
    checks=[]
    def check(name,test):assert test,name;checks.append(dict(name=name,passed=True))
    prop=dict(id='P',left=['u','h'],right=['history','times','dt'])
    premise=dict(shared_parameters=True,deterministic_response_assumption=True,measurement_stable=True)
    rows=[dict(u=0.,h=float(h),history=[float(v)]*4,times=[-4.,-3.,-2.,-1.],dt=1.,o=float(h*v)) for h in [0,1] for v in [0,1]]
    c=additive_certificate(rows,prop,premise)
    check('exact unrestricted class bound',abs(c['minimum_rmse']-.25)<1e-12 and c['exact_normal_equations_verified'])
    check('certified class changes G operation set',allowed_operations([prop],[c],'G')['allowed']==['joint'])
    check('same evidence leaves F routes available','separate:P' in allowed_operations([prop],[c],'F')['allowed'])
    withdrawn=additive_certificate(rows,prop,dict(premise,measurement_stable=False))
    check('premise withdrawal restores route','separate:P' in allowed_operations([prop],[withdrawn],'G')['allowed'])
    additive=[dict(r,o=r['h']+r['history'][0]) for r in rows]
    check('feasible additive class not pruned',not additive_certificate(additive,prop,premise)['hard_excluded'])
    shuffled=copy.deepcopy(rows);shuffled[1]['h']+=.000001
    check('nearby controls are not treated as exact matches',additive_certificate(shuffled,prop,premise)['minimum_rmse']<1e-10)
    p=lambda n,d:dict(name=n,dimension=d,initial=1.,lower=-3.,upper=3.)
    sc=dict(parameters=[p('gain',[0,1]),p('clock',[1,0])],quantities=[dict(name='feature',expression='mean(history)')],exposed_inputs=['u','h'])
    ma=Model(sc,'gain*u+gain*feature')
    check('quantity dependencies expand to raw inputs',membership(ma,prop['left'],prop['right'])['certified_additive'])
    mj=Model(sc,'gain*h*feature/clock')
    check('actual coupling not falsely certified additive',not membership(mj,prop['left'],prop['right'])['certified_additive'])
    renamed=copy.deepcopy(sc);renamed['quantities'][0].update(name='state')
    check('quantity names do not change classification',membership(Model(renamed,'gain*u+gain*state'),prop['left'],prop['right'])['certified_additive'])
    full=dict(sc,expression='gain*u',left_expression='gain*u',right_expression='gain*feature')
    _,expr,model=assemble(full,'separate:P',[prop])
    check('separate route has executable branch semantics',model.predict([rows[0]],[1.,1.])[0]==0.)
    bad=dict(full,left_expression='gain*h*feature/clock')
    try:assemble(bad,'separate:P',[prop]);ok=False
    except ValueError:ok=True
    check('branch cannot silently access other input group',ok)
    # Parameters may be jointly declared at completion; the plan freezes no list.
    check('response coefficients declared at completion',Model(sc,'gain*u').manifest()['parameter_bindings']['gain']==0)
    return checks
