"""Broker tools for unit inference, representation tests and model completion."""
import ast
import itertools
import json
import math
from pathlib import Path
import numpy as np
import sympy as sp
from scipy.optimize import least_squares
from model_language import Model,RAW,parse,evaluate


def infer_units(parameters,quantities,features,expression=None):
    env={n:tuple(sp.Rational(x) for x in dim) for n,(_,dim) in RAW.items()};eq=[];symbols=[]
    for i,p in enumerate(parameters):
        if p['name'] in env:raise ValueError('Duplicate parameter name')
        pair=sp.symbols('unit_'+str(i)+'_T unit_'+str(i)+'_O');symbols+=list(pair);env[p['name']]=pair
    def visit(n):
        if isinstance(n,ast.Name):
            if n.id not in env:raise ValueError('Unknown symbol '+n.id)
            return env[n.id]
        if isinstance(n,ast.Constant) and type(n.value) in [int,float]:return (sp.Integer(0),)*2
        if isinstance(n,ast.UnaryOp):return visit(n.operand)
        if isinstance(n,ast.Subscript):return visit(n.value)
        if isinstance(n,ast.BinOp):
            a=visit(n.left);b=visit(n.right)
            if isinstance(n.op,(ast.Add,ast.Sub)):
                eq.extend(x-y for x,y in zip(a,b));return a
            if isinstance(n.op,ast.Mult):return tuple(x+y for x,y in zip(a,b))
            if isinstance(n.op,ast.Div):return tuple(x-y for x,y in zip(a,b))
            if isinstance(n.op,ast.Pow):
                eq.extend(b)
                try:k=sp.Rational(str(ast.literal_eval(n.right)));return tuple(x*k for x in a)
                except (ValueError,TypeError):eq.extend(a);return (sp.Integer(0),)*2
            raise ValueError('Unsupported binary operation')
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and len(n.args)==1:
            d=visit(n.args[0]);f=n.func.id
            if f in ['sum','mean','abs']:return d
            if f=='sqrt':return tuple(x/2 for x in d)
            if f in ['exp','log','sin','cos','tanh']:eq.extend(d);return (sp.Integer(0),)*2
        raise ValueError('Unsupported unit-inference syntax')
    for q in quantities:
        if q['name'] in env:raise ValueError('Duplicate quantity name')
        env[q['name']]=visit(ast.parse(q['expression'],mode='eval').body)
    feature_dims=[visit(ast.parse(f,mode='eval').body) for f in features]
    if expression is not None:
        d=visit(ast.parse(expression,mode='eval').body);eq.extend([d[0],d[1]-1])
    eq=[sp.expand(x) for x in eq if x!=0]
    if symbols:
        sol=sp.linsolve(eq,symbols) if eq else sp.FiniteSet(tuple(symbols))
        if sol is sp.EmptySet or not sol:raise ValueError('Inconsistent dimensions')
        values=list(next(iter(sol)));free=set().union(*(v.free_symbols for v in values));sub={v:0 for v in free}
        values=[sp.simplify(v.subs(sub)) for v in values]
        mapping=dict(zip(symbols,values))
    else:
        if any(x!=0 for x in eq):raise ValueError('Inconsistent dimensions')
        mapping={};free=set()
    declared=[]
    for p in parameters:
        d=[sp.simplify(x.subs(mapping)) for x in env[p['name']]]
        if any(not x.is_Integer or abs(x)>6 for x in d):raise ValueError('Unsupported nonintegral/extreme inferred parameter dimension')
        declared.append(dict(p,dimension=list(map(int,d))))
    return declared,dict(inferred_parameter_dimensions={p['name']:p['dimension'] for p in declared},
                         free_unit_symbols=len(free),convention='Unconstrained unit choices assigned zero; not unique physical identification')


class FeatureProgram:
    def __init__(self,request):
        self.request=request;self.features=request['features'];self.quantities=request['quantities']
        if not self.features or len(self.features)>200:raise ValueError('Need 1..200 scalar feature expressions')
        if len(self.quantities)>4:raise ValueError('At most four agent quantity definitions')
        self.parameters,self.unit_audit=infer_units(request['parameters'],self.quantities,self.features)
        if len(self.parameters)>2:raise ValueError('Completion supports at most two shared nonlinear parameters')
        self.model=Model(dict(parameters=self.parameters,quantities=self.quantities,exposed_inputs=list(RAW)))
        self.trees=[];self.dims=[]
        for f in self.features:
            tree,(shape,dim)=parse(f,self.model.env)
            if shape:raise ValueError('Feature must reduce to a scalar: '+f)
            self.trees.append(tree);self.dims.append(tuple(int(x) for x in dim))

    def matrix(self,rows,values,symbolic=False):
        result=[]
        with np.errstate(all='raise'):
            for r in rows:
                env=self.model.row_env(r,values,symbolic)
                result.append([evaluate(t,env,symbolic) for t in self.trees])
        result=np.array(result,dtype=object if symbolic else float)
        if not symbolic and not np.all(np.isfinite(result)):raise ValueError('Nonfinite features')
        return result


def representation_check(request,rows,premises):
    fp=FeatureProgram(request);values=[sp.Symbol(p['name'],real=True) for p in fp.parameters]
    groups={};unknown=[]
    for i,r in enumerate(rows):
        try:key=tuple(sp.srepr(v) for v in fp.matrix([r],values,True)[0])
        except Exception as exc:key=('unknown',i);unknown.append(dict(row_id=r['row_id'],error=str(exc)))
        groups.setdefault(key,[]).append(r)
    sse=0.;witnesses=[]
    for group in groups.values():
        y=np.array([r['o'] for r in group]);loss=float(np.sum((y-y.mean())**2));sse+=loss
        if np.ptp(y)>.03:witnesses.append(dict(row_ids=[r['row_id'] for r in group],observed_range=float(np.ptp(y)),unavoidable_sse=loss))
    bound=float(np.sqrt(sse/len(rows)));active=all(premises.get(k) is True for k in ['measurement_stable','shared_parameters','deterministic_response_assumption'])
    return dict(valid=True,minimum_possible_dev_rmse=bound,can_meet_threshold=not(active and bound>.06),
       witnesses=witnesses,unknown=unknown,unit_audit=fp.unit_audit,
       explanation='Exact symbolic equality of the supplied feature values forces any deterministic downstream function to give identical predictions. Unknown equalities are not merged. Passing this check does not prove the features sufficient or any model valid.')


def powers(count,degree):
    out=[tuple([0]*count)]
    for d in range(1,degree+1):
        for combo in itertools.combinations_with_replacement(range(count),d):
            v=[0]*count
            for i in combo:v[i]+=1
            out.append(tuple(v))
    return out


def monomial_matrix(base,exponents):
    return np.column_stack([np.prod(np.power(base,np.array(p)),axis=1) for p in exponents])


def sparse_sequence(X,y,max_terms,counter):
    """Forward least-squares selection, fit-only; every solve is counted."""
    selected=[0];sequence=[]
    while True:
        counter['linear_solves']+=1
        if counter['linear_solves']>20000:raise RuntimeError('Linear solve budget exhausted')
        coeff=np.linalg.lstsq(X[:,selected],y,rcond=None)[0];r=y-X[:,selected]@coeff
        loss=float(r@r);bic=len(y)*np.log(max(loss/len(y),1e-18))+len(selected)*np.log(len(y))
        sequence.append((selected.copy(),coeff,loss,float(bic)))
        if len(selected)>=max_terms:break
        Q=np.linalg.qr(X[:,selected],mode='reduced')[0];Z=X-Q@(Q.T@X)
        norm=np.sum(Z*Z,axis=0);gain=np.full(X.shape[1],-np.inf)
        good=norm>1e-14*np.maximum(1.,np.sum(X*X,axis=0))
        gain[good]=(Z[:,good].T@r)**2/norm[good];gain[selected]=-np.inf
        j=int(np.argmax(gain))
        if not np.isfinite(gain[j]) or gain[j]<1e-15:break
        selected.append(j)
    return sequence


def render_candidate(fp,exponents,indices,values,coeff,train_rmse,dev_rmse,converged,origin):
    # Original semantic features become named aliases so execution, rendering,
    # dimensions and parameter indices have one source.
    quantities=list(fp.quantities);aliases=[]
    if len(fp.features)<=4:
        for i,f in enumerate(fp.features):
            name='tool_feature_'+str(i);quantities.append(dict(name=name,expression=f));aliases.append(name)
    else:aliases=['('+f+')' for f in fp.features]
    parameters=list(fp.parameters);actual=list(map(float,values));terms=[]
    for j,(ix,c) in enumerate(zip(indices,coeff)):
        exponent=exponents[ix];dim=[sum(power*fp.dims[i][k] for i,power in enumerate(exponent)) for k in range(2)]
        name='tool_coefficient_'+str(j)
        parameters.append(dict(name=name,dimension=[-dim[0],1-dim[1]],lower=-1e12,initial=float(c),upper=1e12))
        actual.append(float(c));factors=[aliases[i]+('**'+str(power) if power!=1 else '') for i,power in enumerate(exponent) if power]
        terms.append(name+('*('+'*'.join(factors)+')' if factors else ''))
    scaffold=dict(parameters=parameters,quantities=quantities,exposed_inputs=list(RAW));expression='+'.join(terms)
    # Large automatic catalogs inline expressions; final program still must obey
    # the common compiler. Failures remain trials, not silently simplified models.
    m=Model(scaffold,expression)
    return dict(scaffold=scaffold,expression=expression,values=actual,train_rmse=train_rmse,dev_rmse=dev_rmse,
                optimizer_converged=converged,origin=origin,feature_definitions=fp.features,
                selected_basis=[list(exponents[i]) for i in indices],manifest=m.manifest())


def complete_model(request,train,dev,premises,log_path,budget):
    Path(log_path).parent.mkdir(parents=True,exist_ok=True)
    audit=representation_check(request,dev,premises)
    if not audit['can_meet_threshold']:return dict(status='representation_inadequate',representation=audit),[]
    fp=FeatureProgram(request);degree=request['degree'];exponents=powers(len(fp.features),degree)
    if len(exponents)>500:raise ValueError('Basis library exceeds 500 monomials')
    n=len(fp.parameters);max_terms=8-n;y=np.array([r['o'] for r in train]);dy=np.array([r['o'] for r in dev])
    used_before=budget['residual_calls'];remaining=min(1600,4800-used_before);candidates=[];shortlist={}
    if remaining<=0:return dict(status='budget_exhausted'),[]
    def matrices(values):
        if budget['residual_calls']-used_before>=remaining:raise RuntimeError('Per-call residual budget exhausted')
        budget['residual_calls']+=1
        return monomial_matrix(fp.matrix(train,values),exponents),monomial_matrix(fp.matrix(dev,values),exponents)
    def record(indices,values,coeff,X,D,converged,origin):
        tr=float(np.sqrt(np.mean((X[:,indices]@coeff-y)**2)));dr=float(np.sqrt(np.mean((D[:,indices]@coeff-dy)**2)))
        item=dict(indices=indices,nonlinear_values=list(map(float,values)),coefficients=list(map(float,coeff)),train_rmse=tr,dev_rmse=dr,converged=converged,origin=origin)
        with Path(log_path).open('a') as f:f.write(json.dumps(item,allow_nan=False)+'\n')
        if converged:
            try:candidates.append(render_candidate(fp,exponents,indices,values,coeff,tr,dr,True,origin))
            except Exception as exc:
                with Path(log_path).open('a') as f:f.write(json.dumps(dict(render_failure=str(exc),indices=indices))+'\n')
        return tr,dr
    starts=[]
    if n:
        grids=[]
        for p in fp.parameters:
            lo,hi=p['lower'],p['upper'];a=[p['initial']]
            a+=list(np.geomspace(lo,hi,7)[1:-1]) if lo>0 else [lo+.2*(hi-lo),lo+.5*(hi-lo),lo+.8*(hi-lo)]
            grids.append(list(dict.fromkeys(a)))
        starts=list(itertools.product(*grids))
    else:starts=[()]
    for values in starts:
        try:
            X,D=matrices(values)
            for indices,coeff,loss,bic in sparse_sequence(X,y,max_terms,budget):
                record(indices,values,coeff,X,D,not n,'fit_only_grid_structure_proposal')
                k=tuple(indices)
                if k not in shortlist or bic<shortlist[k][0]:shortlist[k]=(bic,values)
        except (ValueError,FloatingPointError,OverflowError,ZeroDivisionError):continue
        except RuntimeError:break
    if n:
        lo=np.array([p['lower'] for p in fp.parameters]);hi=np.array([p['upper'] for p in fp.parameters])
        # Only fit statistics choose the structures to refine. Dev never sets a
        # parameter vector; it selects among fit-converged complete models.
        for indices,(bic,start) in sorted(shortlist.items(),key=lambda v:v[1][0])[:6]:
            for initial in [start,tuple(p['initial'] for p in fp.parameters)]:
                last={}
                def residual(values):
                    X,D=matrices(values);budget['linear_solves']+=1
                    if budget['linear_solves']>20000:raise RuntimeError('Linear solve budget exhausted')
                    coeff=np.linalg.lstsq(X[:,indices],y,rcond=None)[0];last.update(values=values.copy(),coeff=coeff,X=X,D=D)
                    record(list(indices),values,coeff,X,D,False,'fit_only_nonlinear_iteration')
                    return X[:,indices]@coeff-y
                try:
                    opt=least_squares(residual,np.array(initial),bounds=(lo,hi),max_nfev=150)
                    # Re-evaluate exactly at the returned fit point; derivative
                    # probes must not be confused with the final fitted model.
                    residual(opt.x)
                    record(list(indices),opt.x,last['coeff'],last['X'],last['D'],bool(opt.success),'fit_converged_variable_projection')
                except (RuntimeError,ValueError,FloatingPointError,OverflowError,ZeroDivisionError):continue
    if not candidates:return dict(status='no_converged_complete_model',representation=audit,residual_calls=budget['residual_calls']-used_before),[]
    candidates.sort(key=lambda c:(c['dev_rmse'],len(c['values']),c['expression']))
    return dict(status='completed',representation=audit,complete_models=len(candidates),best=candidates[0],
                residual_calls=budget['residual_calls']-used_before,linear_solves=budget['linear_solves']),candidates


def automatic_library():
    """Bounded typed grammar over raw inputs, not an answer/mechanism menu."""
    scalar=['u','u**2','u**3','h','h**2','h**3']
    reduced=[]
    for a in ['history','times']:
        reduced += ['sum('+a+')','sum('+a+'**2)','sum('+a+'**3)']
        for b in ['history','times']:
            reduced.append('sum('+a+'*'+b+')')
            # Only a time-valued exponent argument can share the time parameter.
            if b=='times':
                for op in ['exp','tanh','sin','cos']:
                    for sign in ['','-']:
                        reduced.append('sum('+a+'*'+op+'('+sign+b+'/scale))')
    waiting=['h','h**2','exp(h/scale)','exp(-h/scale)','tanh(h/scale)']
    features=list(dict.fromkeys(scalar+reduced))
    for a in reduced:
        for b in waiting:features.append('('+a+')*('+b+')')
    # Constant and duplicate columns are handled by forward selection; no access
    # to simulator formula, coefficients, hidden targets or true time scale.
    return dict(parameters=[dict(name='scale',lower=.05,initial=1.,upper=20.)],quantities=[],features=list(dict.fromkeys(features)),degree=1)
