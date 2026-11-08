"""Named mathematical models; shared compiler, fit tools, partial-model audit."""
import ast
import copy
from fractions import Fraction
import json
import math
import re
import numpy as np
import sympy as sp
from scipy.optimize import least_squares

RAW = {'u': (0, (0, 0)), 'h': (0, (1, 0)),
       'history': (4, (0, 0)), 'times': (4, (1, 0)), 'dt': (0, (1, 0))}
FUNCS = {'sum', 'mean', 'exp', 'log', 'sqrt', 'abs', 'sin', 'cos', 'tanh'}
NP = {x: getattr(np, x) for x in FUNCS}
SP = {x: getattr(sp, x) for x in FUNCS - {'sum', 'mean', 'abs'}} | {'abs': sp.Abs}


def dimension(d):
    if not isinstance(d, list) or len(d) != 2 or any(type(x) != int or abs(x) > 6 for x in d):
        raise ValueError('dimension must be [time_power, response_power], integer powers -6..6')
    return tuple(Fraction(x) for x in d)


def parse(text, env):
    if not isinstance(text, str) or len(text) > 1600:
        raise ValueError('Expression must be a string of at most 1600 characters')
    tree = ast.parse(text, mode='eval').body
    if sum(1 for _ in ast.walk(tree)) > 300:
        raise ValueError('Expression exceeds 300 AST nodes')

    def infer(n):
        if isinstance(n, ast.Name):
            if n.id not in env: raise ValueError('Undeclared or unexposed symbol: ' + n.id)
            return env[n.id]
        if isinstance(n, ast.Constant) and type(n.value) in (float, int) and math.isfinite(n.value):
            return 0, (Fraction(0), Fraction(0))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub)):
            return infer(n.operand)
        if isinstance(n, ast.Subscript):
            shape, dim = infer(n.value)
            if not (shape == 4 and isinstance(n.slice, ast.Constant) and type(n.slice.value) == int and 0 <= n.slice.value < 4):
                raise ValueError('Only vector indexing [0] through [3] is allowed')
            return 0, dim
        if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow)):
            sa, da = infer(n.left); sb, db = infer(n.right)
            shape = max(sa, sb)
            if isinstance(n.op, (ast.Add, ast.Sub)):
                if da != db: raise ValueError('Addition/subtraction requires equal dimensions')
                return shape, da
            if isinstance(n.op, ast.Mult): return shape, tuple(a+b for a, b in zip(da, db))
            if isinstance(n.op, ast.Div): return shape, tuple(a-b for a, b in zip(da, db))
            if db != (0, 0): raise ValueError('Exponent must be dimensionless')
            if da == (0, 0): return shape, da
            try: power = Fraction(str(ast.literal_eval(n.right)))
            except (ValueError, TypeError): raise ValueError('Dimensional base requires constant exponent')
            return shape, tuple(a*power for a in da)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in FUNCS:
            if len(n.args) != 1 or n.keywords: raise ValueError('All functions take exactly one argument')
            shape, dim = infer(n.args[0]); f = n.func.id
            if f in ('sum', 'mean'): return 0, dim
            if f == 'abs': return shape, dim
            if f == 'sqrt': return shape, tuple(x/2 for x in dim)
            if dim != (0, 0): raise ValueError(f + ' requires dimensionless input')
            return shape, (Fraction(0), Fraction(0))
        raise ValueError('Unsupported syntax: ' + type(n).__name__)
    return tree, infer(tree)


def evaluate(tree, env, symbolic=False):
    if isinstance(tree, ast.Name): return env[tree.id]
    if isinstance(tree, ast.Constant): return sp.Rational(str(tree.value)) if symbolic else tree.value
    if isinstance(tree, ast.UnaryOp):
        v = evaluate(tree.operand, env, symbolic)
        return -v if isinstance(tree.op, ast.USub) else v
    if isinstance(tree, ast.Subscript): return evaluate(tree.value, env, symbolic)[tree.slice.value]
    if isinstance(tree, ast.BinOp):
        a = evaluate(tree.left, env, symbolic); b = evaluate(tree.right, env, symbolic)
        if isinstance(tree.op, ast.Add): return a+b
        if isinstance(tree.op, ast.Sub): return a-b
        if isinstance(tree.op, ast.Mult): return a*b
        if isinstance(tree.op, ast.Div): return a/b
        return a**b
    x = evaluate(tree.args[0], env, symbolic); f = tree.func.id
    if not symbolic: return NP[f](x)
    if f == 'sum': return sum(x) if isinstance(x, np.ndarray) else x
    if f == 'mean': return sum(x)/len(x) if isinstance(x, np.ndarray) else x
    return np.array([SP[f](v) for v in x], dtype=object) if isinstance(x, np.ndarray) else SP[f](x)


class Model:
    def __init__(self, scaffold, expression=None):
        self.scaffold = scaffold; self.parameters = scaffold['parameters']
        if len(self.parameters) > 8: raise ValueError('At most eight named shared parameters')
        self.env = dict(RAW); self.qtrees = []
        for p in self.parameters:
            n = p['name']; self.new_name(n)
            if not all(math.isfinite(p[k]) for k in ('lower', 'initial', 'upper')) or not p['lower'] < p['initial'] < p['upper']:
                raise ValueError('Parameter bounds must be finite and lower < initial < upper')
            self.env[n] = 0, dimension(p['dimension'])
        if len(scaffold['quantities']) > 8: raise ValueError('At most eight sequential quantity definitions')
        for q in scaffold['quantities']:
            self.new_name(q['name']); tree, typed = parse(q['expression'], self.env)
            self.qtrees.append((q['name'], tree)); self.env[q['name']] = typed
        self.exposed = scaffold['exposed_inputs']
        if len(self.exposed) != len(set(self.exposed)) or any(x not in RAW for x in self.exposed):
            raise ValueError('exposed_inputs must be unique raw input names')
        available = set(self.exposed) | {q['name'] for q in scaffold['quantities']} | {p['name'] for p in self.parameters}
        self.final_env = {k: v for k, v in self.env.items() if k in available}
        self.tree = None
        if expression is not None:
            self.tree, typed = parse(expression, self.final_env)
            if typed != (0, (0, 1)): raise ValueError('Complete equation must be scalar raw response, dimension [0,1]')

    def new_name(self, n):
        if not re.fullmatch('[A-Za-z][A-Za-z0-9_]*', n) or n in self.env or n in FUNCS:
            raise ValueError('Invalid, duplicate or reserved name: ' + str(n))

    def row_env(self, row, values, symbolic=False):
        convert = (lambda v: sp.Rational(str(v))) if symbolic else float
        env = {k: np.array([convert(v) for v in row[k]], dtype=object if symbolic else float)
               if RAW[k][0] else convert(row[k]) for k in RAW}
        env.update({p['name']: v for p, v in zip(self.parameters, values)})
        for name, tree in self.qtrees: env[name] = evaluate(tree, env, symbolic)
        return env

    def predict(self, rows, values):
        with np.errstate(all='raise'):
            result = np.array([float(evaluate(self.tree, self.row_env(r, values))) for r in rows])
        if not np.all(np.isfinite(result)): raise ValueError('Nonfinite response')
        return result

    def manifest(self):
        equations = {n: ast.unparse(t) for n, t in self.qtrees}
        dims = {n: dict(shape='vector4' if s else 'scalar', dimension=list(map(str, d))) for n, (s, d) in self.env.items()}
        return dict(equations=equations, response=ast.unparse(self.tree) if self.tree else None,
                    parameter_bindings={p['name']: i for i, p in enumerate(self.parameters)}, types=dims,
                    final_allowed_symbols=sorted(self.final_env), source='Derived from the one named specification')


def capacity_audit(scaffold, rows, premises):
    """A proof for a PARTIAL representation; no final response formula exists yet.

    Exactly identical symbolic signatures imply identical response under every
    shared parameter value. Equality may be missed; non-identical signatures do
    not prove distinguishability. No sampled parameter value establishes equality.
    """
    model = Model(scaffold); groups = {}; unknown = []
    values = [sp.Symbol(p['name'], real=True) for p in model.parameters]
    names = scaffold['exposed_inputs'] + [q['name'] for q in scaffold['quantities']]
    for i, row in enumerate(rows):
        try:
            env = model.row_env(row, values, True)
            def signature(v):
                return tuple(signature(x) for x in v) if isinstance(v, np.ndarray) else sp.srepr(v)
            key = tuple(signature(env[n]) for n in names)
        except Exception as exc:
            unknown.append(dict(row=row['row_id'], reason=str(exc))); key = ('unknown', i)
        groups.setdefault(key, []).append(row)
    witnesses = []; total_sse = 0.
    for group in groups.values():
        obs = np.array([r['o'] for r in group]); sse = float(np.sum((obs-np.mean(obs))**2)); total_sse += sse
        if len(group) > 1 and np.ptp(obs) > .03:
            witnesses.append(dict(row_ids=[r['row_id'] for r in group], n=len(group),
                                  observed_range=float(np.ptp(obs)), unavoidable_sse=sse))
    bound = float(np.sqrt(total_sse/len(rows)))
    active = all(premises.get(k) is True for k in ('shared_parameters', 'deterministic_response_assumption', 'measurement_stable'))
    blocked = active and bound > .06
    return dict(stage='partial representation, before complete response generation',
                premises_active=active, dev_rows=len(rows), guaranteed_dev_rmse_lower_bound=bound,
                equivalence_classes=len(groups), witnesses=witnesses, unknown=unknown,
                finish_enabled=not blocked,
                next_operation='revise_partial_representation' if blocked else 'compose_complete_response',
                explanation='Every deterministic shared response using only these exposed inputs and defined quantities has the stated RMSE floor on this exact development set. Unproven equality is not merged; unknown cases remain available. This provides no preferred formula.')


def rmse(pred, rows): return float(np.sqrt(np.mean((pred-np.array([r['o'] for r in rows]))**2)))


def fit(scaffold, expression, train, dev):
    try: model = Model(scaffold, expression)
    except Exception as exc: return dict(status='compile_failed', error=str(exc))
    parameters = model.parameters; y = np.array([r['o'] for r in train]); calls = 0; attempts = []
    if parameters:
        lo = np.array([p['lower'] for p in parameters]); hi = np.array([p['upper'] for p in parameters])
        initial = np.array([p['initial'] for p in parameters]); choices = []
        for start in [initial, lo+.25*(hi-lo), lo+.5*(hi-lo), lo+.75*(hi-lo)]:
            local = 0; best = [float('inf'), None]
            def residual(p):
                nonlocal local, calls
                if local >= 400: raise RuntimeError('400 actual residual calls exhausted')
                local += 1; calls += 1
                try: v = model.predict(train, p)-y
                except (ValueError, OverflowError, ZeroDivisionError, FloatingPointError): v = np.full(len(y), 1e6)
                loss = float(v@v)
                if loss < best[0]: best[:] = [loss, p.copy()]
                return v
            try:
                opt = least_squares(residual, start, bounds=(lo, hi), max_nfev=400)
                choices.append((float(opt.fun@opt.fun), opt.x.tolist(), bool(opt.success)))
                attempts.append(dict(calls=local, converged=bool(opt.success), message=opt.message))
            except Exception as exc:
                attempts.append(dict(calls=local, converged=False, message=str(exc)))
                if best[1] is not None: choices.append((best[0], best[1].tolist(), False))
        if not choices: return dict(status='fit_failed', residual_calls=calls, attempts=attempts)
        _, values, converged = min([c for c in choices if c[2]] or choices, key=lambda x: x[0])
    else: values = []; converged = True
    try:
        tp = model.predict(train, values); dp = model.predict(dev, values)
        records = [dict(row_id=r['row_id'], observed=r['o'], predicted=float(p), residual=float(p-r['o'])) for r,p in zip(dev,dp)]
        return dict(status='executed', parameters=dict(zip([p['name'] for p in parameters], values)), values=values,
                    fit_rmse=rmse(tp,train), dev_rmse=rmse(dp,dev), optimizer_converged=converged,
                    residual_calls=calls, attempts=attempts, dev_predictions=records,
                    dev_pass=bool(converged and rmse(dp,dev)<=.06), manifest=model.manifest())
    except Exception as exc: return dict(status='execution_failed', error=str(exc), residual_calls=calls, attempts=attempts)
