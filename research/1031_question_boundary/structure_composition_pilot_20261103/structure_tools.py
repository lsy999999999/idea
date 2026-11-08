"""Generic, exact finite-data certificates for shared additive classes."""
import ast
import numpy as np
import sympy as sp
from model_language import Model, RAW


def partition(proposal):
    left=proposal['left'];right=proposal['right']
    if not left or not right or len(set(left+right))!=len(left+right) or set(left+right)!=set(RAW):
        raise ValueError('Two nonempty disjoint groups must cover the five raw input names')
    return left,right


def key(row,names):
    return tuple(tuple(row[n]) if isinstance(row[n],list) else row[n] for n in names)


def additive_certificate(rows,proposal,premises,threshold=.06):
    left,right=partition(proposal)
    ka=[key(r,left) for r in rows];kb=[key(r,right) for r in rows]
    a=list(dict.fromkeys(ka));b=list(dict.fromkeys(kb))
    X=sp.zeros(len(rows),len(a)+len(b))
    for i in range(len(rows)):X[i,a.index(ka[i])]=1;X[i,len(a)+b.index(kb[i])]=1
    # Independent columns span every finite-set additive prediction. Exact
    # rational residual orthogonal to them is a dual certificate of the minimum.
    pivots=X.rref()[1];basis=X[:,list(pivots)]
    y=sp.Matrix([sp.Rational(str(r['o'])) for r in rows])
    beta=(basis.T*basis).inv()*(basis.T*y)
    residual=y-basis*beta
    assert X.T*residual==sp.zeros(X.cols,1)
    sse=(residual.T*residual)[0];limit=sp.Rational(str(threshold))**2*len(rows)
    active=all(premises.get(k) is True for k in ['shared_parameters','deterministic_response_assumption','measurement_stable'])
    return dict(id=proposal['id'],left=left,right=right,n=len(rows),rank=len(pivots),
       class_definition='A('+','.join(left)+') + B('+','.join(right)+')',
       exact_sse=str(sse),minimum_rmse=float(sp.sqrt(sse/len(rows))),threshold=threshold,
       exact_threshold_sse=str(limit),exceeds_threshold=bool(sse>limit),premises_active=active,
       hard_excluded=bool(active and sse>limit),
       dual_residual=[str(v) for v in residual],exact_normal_equations_verified=True,
       proof='Allow unrestricted values for A and B at every unique group input. Their prediction vectors span the incidence matrix columns. The exact rational projection residual is orthogonal to all columns. Pythagoras proves its SSE is the global minimum for every shared deterministic additive function on these records.',
       scope='Empirical RMSE on these exact rows, not a universal physical theorem or a noise-only bound')


def membership(model,left,right):
    deps={n:{n} for n in RAW};deps.update({p['name']:set() for p in model.parameters})
    def raw_dependencies(tree):
        out=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Name):out|=deps.get(node.id,set())
        return out
    for name,tree in model.qtrees:deps[name]=raw_dependencies(tree)
    def terms(t):
        if isinstance(t,ast.BinOp) and isinstance(t.op,(ast.Add,ast.Sub)):
            return terms(t.left)+terms(t.right)
        return [t]
    records=[]
    for t in terms(model.tree):
        used=raw_dependencies(t)
        side='left' if used<=set(left) else 'right' if used<=set(right) else 'unknown'
        records.append(dict(expression=ast.unparse(t),dependencies=sorted(used),side=side))
    return dict(certified_additive=all(t['side']!='unknown' for t in records),terms=records,
       unknown_meaning='May be coupled or algebraically additive; no hard class rejection from unknown')


def allowed_operations(proposals,certificates,mode):
    all_ops=['joint']+['separate:'+p['id'] for p in proposals]
    disabled=['separate:'+c['id'] for c in certificates if c.get('hard_excluded')] if mode=='G' else []
    return dict(allowed=[x for x in all_ops if x not in disabled],disabled=disabled,
       semantics=dict(joint='One unrestricted whole response over any supplied information; may still emit an additive function and remains subject to common tests',
                      separate='Tool constructs a sum of two response branches, each restricted to one certified input group'))


def assemble(spec,operation,proposals):
    scaffold={k:spec[k] for k in ['parameters','quantities','exposed_inputs']}
    if operation=='joint':
        expression=spec['expression'];model=Model(scaffold,expression)
    else:
        pid=operation.split(':',1)[1];proposal=next(p for p in proposals if p['id']==pid)
        left,right=partition(proposal)
        lm=Model(scaffold,spec['left_expression']);rm=Model(scaffold,spec['right_expression'])
        def raw_deps(model):
            deps={n:{n} for n in RAW};deps.update({p['name']:set() for p in model.parameters})
            def dependencies(tree):
                out=set()
                for n in ast.walk(tree):
                    if isinstance(n,ast.Name):out|=deps.get(n.id,set())
                return out
            for name,tree in model.qtrees:deps[name]=dependencies(tree)
            return dependencies(model.tree)
        if not raw_deps(lm)<=set(left) or not raw_deps(rm)<=set(right):
            raise ValueError('Branch exceeds the raw dependencies of the chosen separate construction')
        expression='('+spec['left_expression']+')+('+spec['right_expression']+')'
        model=Model(scaffold,expression)
    return scaffold,expression,model
