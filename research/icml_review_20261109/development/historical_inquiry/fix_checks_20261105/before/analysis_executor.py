"""Reproducible array analysis plans, with controller handoff for missing capabilities."""
from __future__ import annotations

import ast
import hashlib
import json
import operator
from pathlib import Path

import numpy as np

from fish_materials import clean, digest
from prepare import save


PLAN_PROTOCOL = '''Analysis plan: {kind:"analysis", question, record_id, start?, stop?,
variables:[{name, expression, meaning, units}], outputs:[{name, expression}],
groups:[{name, where, values:[variable names]}],
model:{target: variable, features:[variables], train_fraction:0..1} (optional)}.
Base arrays: positions (n,2,2), scores (n,2), frame (n). Expressions use numeric/boolean
constants, arithmetic/comparisons, &, |, ~, slices and named functions: abs,sqrt,sin,cos,
arctan2,sum,mean,std,min,max,median,quantile,isfinite,where,clip,diff,norm,shift,rolling.
Functions accept axis/keepdims, etc. shift(x,k) gives x[t-k] with NaN padding (no wrap);
rolling(x,k) trailing mean, first k-1 rows NaN. diff(x,n=1,axis=0) is ordinary finite
difference; define your own quality masks and alignment. norm(x,axis=-1) is Euclidean.
Use explicit researcher-defined variables, units and conditions. Outputs may include arrays;
full arrays saved, response gives shapes/summaries/first rows. Groups return count and
summary per variable under where. Model is least squares with intercept; first train_fraction
of rows fit, remainder evaluate, preserving chronological split. This is exploratory fitting.
For an unavailable method, request {kind:"custom",question,requirements,record_id}; the
controller translates to an executable plan or returns a pending capability task, never a
scientific impossibility. You can also request segment/compare/state/model using this same
plan schema; these names have no prescribed scientific meaning.'''


def shift(x, k):
    if type(k) is not int or abs(k) > len(x):
        raise ValueError('Invalid shift')
    out = np.full(np.shape(x), np.nan)
    if k == 0:
        return np.asarray(x, dtype=float).copy()
    if k > 0:
        out[k:] = x[:-k]
    else:
        out[:k] = x[-k:]
    return out


def rolling(x, k):
    if type(k) is not int or not 1 <= k <= len(x):
        raise ValueError('Invalid rolling window')
    out = np.full(np.shape(x), np.nan)
    values = np.asarray(x, dtype=float)
    prefix = np.concatenate([np.zeros_like(values[:1]), np.cumsum(np.where(np.isfinite(values), values, 0), axis=0)])
    count = np.concatenate([np.zeros_like(values[:1]), np.cumsum(np.isfinite(values), axis=0)])
    means = (prefix[k:] - prefix[:-k]) / k
    means[(count[k:] - count[:-k]) != k] = np.nan
    out[k-1:] = means
    return out


FUNCTIONS = {'abs': np.abs, 'sqrt': np.sqrt, 'sin': np.sin, 'cos': np.cos,
             'arctan2': np.arctan2, 'sum': np.sum, 'mean': np.mean, 'std': np.std,
             'min': np.min, 'max': np.max, 'median': np.median, 'quantile': np.quantile,
             'isfinite': np.isfinite, 'where': np.where, 'clip': np.clip, 'diff': np.diff,
             'norm': np.linalg.norm, 'shift': shift, 'rolling': rolling}
BINARY = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
          ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
          ast.BitAnd: operator.and_, ast.BitOr: operator.or_}
COMPARE = {ast.Lt: operator.lt, ast.LtE: operator.le, ast.Gt: operator.gt,
           ast.GtE: operator.ge, ast.Eq: operator.eq, ast.NotEq: operator.ne}


def expression(text, env):
    tree = ast.parse(text, mode='eval')
    if len(list(ast.walk(tree))) > 300:
        raise ValueError('Expression too complex; split into variables')
    def run(node):
        if isinstance(node, ast.Expression):
            return run(node.body)
        if isinstance(node, ast.Constant) and (node.value is None or type(node.value) in (int, float, bool)):
            return node.value
        if isinstance(node, ast.Name) and node.id in env:
            return env[node.id]
        if isinstance(node, (ast.Tuple, ast.List)):
            return tuple(run(v) for v in node.elts)
        if isinstance(node, ast.Slice):
            return slice(*(run(v) if v is not None else None for v in (node.lower, node.upper, node.step)))
        if isinstance(node, ast.Subscript):
            value, index = run(node.value), run(node.slice)
            if isinstance(index, tuple) and len(index) > 4:
                raise ValueError('Use lower dimensional indexed variables')
            return value[index]
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
            a, b = run(node.left), run(node.right)
            if isinstance(node.op, ast.Pow) and (np.size(b) != 1 or abs(float(b)) > 12):
                raise ValueError('Power budget exceeded')
            shape = np.broadcast_shapes(np.shape(a), np.shape(b))
            if np.prod(shape) > 2_000_000:
                raise ValueError('Broadcast array budget exceeded')
            return BINARY[type(node.op)](a, b)
        if isinstance(node, ast.UnaryOp) and type(node.op) in (ast.USub, ast.UAdd, ast.Invert, ast.Not):
            return {ast.USub: operator.neg, ast.UAdd: operator.pos,
                    ast.Invert: np.logical_not, ast.Not: np.logical_not}[type(node.op)](run(node.operand))
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and type(node.ops[0]) in COMPARE:
            return COMPARE[type(node.ops[0])](run(node.left), run(node.comparators[0]))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS:
            if any(k.arg is None for k in node.keywords):
                raise ValueError('No expanded keyword arguments')
            return FUNCTIONS[node.func.id](*[run(a) for a in node.args], **{k.arg: run(k.value) for k in node.keywords})
        raise ValueError('Unsupported expression syntax: ' + type(node).__name__)
    with np.errstate(all='ignore'):
        value = run(tree)
    if np.size(value) > 2_000_000:
        raise ValueError('Array budget exceeded; segment the request')
    return value


def summary(value):
    array = np.asarray(value)
    if array.dtype.kind not in 'biuf':
        raise ValueError('Only numeric arrays may leave executor')
    finite = array[np.isfinite(array)]
    return clean({'shape': list(array.shape), 'finite_values': len(finite),
                  'mean': float(np.mean(finite)) if len(finite) else None,
                  'quantiles_10_50_90': np.quantile(finite, [.1,.5,.9]).tolist() if len(finite) else [],
                  'preview': array[:8].tolist() if array.ndim else array.item()})


class AnalysisExecutor:
    def __init__(self, broker, root, planner=None):
        self.broker, self.root, self.planner = broker, Path(root), planner

    def execute(self, request, request_id):
        path = self.root / request_id / 'result.json'
        if path.exists():
            old = json.loads(path.read_text())
            if old['request'] != request:
                raise ValueError('Compute request changed')
            return old
        root = path.parent
        save(root / 'request.json', request)
        plan = request
        legacy = request.get('kind') in {'window', 'motion', 'lag_correlation'}
        try:
            if not legacy and not request.get('outputs') and not request.get('groups') and not request.get('model'):
                raise ValueError('A concrete execution plan is needed')
            result = self.broker.operation(plan) if legacy else self.run_plan(plan, root)
        except (ValueError, TypeError, KeyError, IndexError, SyntaxError) as error:
            task = {'request': request, 'reason': str(error), 'status': 'pending_controller',
                    'scientific_disposition': 'Interface gap; the research question remains open.'}
            save(root / 'controller_task.json', task)
            if self.planner:
                try:
                    plan = self.planner(task, PLAN_PROTOCOL, root)
                    save(root / 'controller_plan.json', plan)
                    # Controller can translate a request, never silently choose a target mechanism.
                    if any(plan.get(k) != request[k] for k in ('record_id', 'start', 'stop') if k in request):
                        raise ValueError('Controller changed requested record')
                    result = self.run_plan(plan, root)
                    task.update(status='executed', resolution='controller_plan.json')
                except Exception as plan_error:
                    task['execution_error'] = type(plan_error).__name__ + ': ' + str(plan_error)
                    result = {'status': 'pending_controller', 'capability_task': task}
                save(root / 'controller_task.json', task)
            else:
                result = {'status': 'pending_controller', 'capability_task': task}
        kernel = Path(__file__).read_text()
        (root / 'executor.py').write_text(kernel)
        value = {'request': request, 'executed_plan': plan, 'result': result,
                 'executor_sha256': hashlib.sha256(kernel.encode()).hexdigest(),
                 'artifacts': [str(p.resolve()) for p in root.iterdir() if p.is_file()]}
        save(path, value)
        return value

    def run_plan(self, plan, root):
        p, q = self.broker.arrays(plan['record_id'])
        start, stop = plan.get('start', 0), plan.get('stop', len(p))
        if type(start) is not int or type(stop) is not int or not 0 <= start < stop <= len(p):
            raise ValueError('Invalid frame range')
        env = {'positions': p[start:stop], 'scores': q[start:stop], 'frame': np.arange(start, stop)}
        for var in plan.get('variables', []):
            name = var['name']
            if not name.isidentifier() or name.startswith('_') or name in env or name in FUNCTIONS:
                raise ValueError('Unsafe or duplicate variable name')
            if not var.get('meaning') or not var.get('units'):
                raise ValueError('Define variable meaning and units')
            env[name] = expression(var['expression'], env)
        arrays, outputs, groups = {}, {}, []
        for i, out in enumerate(plan.get('outputs', [])):
            value = expression(out['expression'], env)
            arrays['output_' + str(i)] = np.asarray(value)
            outputs[out['name']] = summary(value)
        for group in plan.get('groups', []):
            mask = np.asarray(expression(group['where'], env))
            if mask.dtype.kind != 'b' or mask.ndim != 1:
                raise ValueError('Condition must be a one dimensional boolean mask')
            groups.append({'name': group['name'], 'selected_rows': int(mask.sum()),
                           'values': {v: summary(env[v][mask]) for v in group['values']}})
        model = None
        if plan.get('model'):
            spec = plan['model']
            y = np.asarray(env[spec['target']], dtype=float)
            x = np.column_stack([env[v] for v in spec['features']])
            if y.ndim != 1 or len(y) != len(x) or x.ndim != 2:
                raise ValueError('Model needs aligned scalar variables')
            fraction = spec.get('train_fraction', .7)
            if not 0 < fraction < 1:
                raise ValueError('Use an explicit chronological train/evaluation split')
            split = int(len(y) * fraction)
            design = np.column_stack([np.ones(len(x)), x])
            valid = np.isfinite(design).all(axis=1) & np.isfinite(y)
            train, test = valid.copy(), valid.copy()
            train[split:], test[:split] = False, False
            if train.sum() <= design.shape[1] or not test.sum():
                raise ValueError('Not enough finite training/evaluation rows')
            coef, _, rank, _ = np.linalg.lstsq(design[train], y[train], rcond=None)
            pred = design @ coef
            arrays['predictions'] = pred
            model = clean({'method': 'ordinary least squares with intercept', 'coefficients': coef.tolist(),
                           'feature_order': ['intercept'] + spec['features'], 'rank': int(rank),
                           'split_row': split, 'training_rows': int(train.sum()), 'evaluation_rows': int(test.sum()),
                           'evaluation_rmse': float(np.sqrt(np.mean((pred[test]-y[test])**2))),
                           'scope': 'Exploratory chronological holdout; temporal dependence/leakage require researcher audit, no mechanism identified.'})
        root.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(root / 'outputs.npz', **arrays)
        return {'status': 'executed', 'question': plan.get('question'), 'outputs': outputs, 'groups': groups,
                'model': model, 'data_sha256': self.broker.records[plan['record_id']]['sha256'],
                'full_outputs': str((root / 'outputs.npz').resolve()), 'full_outputs_sha256': digest(root / 'outputs.npz')}
