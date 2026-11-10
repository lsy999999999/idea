"""Immutable multi-role barriers with validated, retryable native deliveries."""
from concurrent.futures import ThreadPoolExecutor
import argparse
import json
import sys
from pathlib import Path
import fcntl

from discover import read, write, now, stage_run
from learning_memory import digest
from portfolio_contracts import validate


class PendingRoles(RuntimeError):
    pass


def immutable(path, value):
    path = Path(path)
    value = json.loads(json.dumps(value, ensure_ascii=False, allow_nan=False))
    if path.exists():
        if read(path) != value:
            raise ValueError('Frozen input/configuration changed: ' + str(path))
    else:
        write(path, value)
    return path


class BatchRuntime:
    def __init__(self, root, model='gpt-6-luna', effort='low', executor='queue', timeout=300):
        self.root = Path(root)
        self.model, self.effort, self.executor, self.timeout = model, effort, executor, timeout

    def prepare(self, stage, kind, owner, prompt, packet):
        if not stage.replace('_', '').isalnum():
            raise ValueError('Unsafe stage')
        directory = self.root/'roles'/stage
        inp = immutable(directory/'input.json', packet)
        ws = directory/'workspace'
        ws.mkdir(parents=True, exist_ok=True)
        validation_command = [sys.executable, '-B', str(Path(__file__).resolve()),
            '--root', str(self.root.resolve()), '--stage', stage, '--validate-only']
        prompt += ('\nBefore delivery, run validation_command as the provided read-only schema tool; '
                   'this tool execution is allowed without inspecting controller source. '
                   'Repair only your output, never the supplied inputs. Use at most three validation/repair cycles; '
                   'if still unresolved, return the concrete error. Do not invent science to satisfy the schema.')
        req = {'stage': stage, 'kind': kind, 'owner': owner, 'model': self.model,
               'validation_command': validation_command,
               'effort': self.effort, 'input': str(inp.resolve()), 'input_sha256': digest(inp),
               'workspace': str(ws.resolve()), 'prompt': prompt}
        immutable(directory/'request.json', req)
        return directory/'request.json'

    def preflight(self, stage):
        """Read-only role-facing check: no delivery marker, no memory or hypothesis writes."""
        if not stage.replace('_', '').isalnum():
            raise ValueError('Unsafe stage')
        req = read(self.root/'roles'/stage/'request.json')
        if digest(req['input']) != req['input_sha256']:
            raise ValueError('Input mutated during role execution')
        ws = Path(req['workspace'])
        value = read(ws/'result.json')
        validate(req['kind'], value, read(req['input']), ws)
        return {'status':'valid','stage':stage,'scientific_state_committed':False}

    def delivery(self, request):
        req = read(request)
        marker = request.parent/'DELIVERY.json'
        if not marker.exists():
            return None
        record = read(marker)
        if record['request_sha256'] != digest(request) or digest(req['input']) != req['input_sha256']:
            raise ValueError('Delivered role inputs changed')
        path = Path(record['result'])
        if digest(path) != record['result_sha256']:
            raise ValueError('Delivered output changed')
        for p, h in record['artifacts'].items():
            if digest(p) != h:
                raise ValueError('Delivered artifact changed')
        validate(req['kind'], read(path), read(req['input']), Path(req['workspace']))
        return path, read(path)

    def deliver(self, stage, agent):
        request = self.root/'roles'/stage/'request.json'
        req = read(request)
        ws = Path(req['workspace'])
        path = ws/'result.json'
        with (request.parent/'.delivery.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if self.delivery(request):
                return self.delivery(request)
            if len(list((request.parent/'rejected').glob('*.json'))) >= 3:
                raise ValueError('Three rejected deliveries; bounded repair limit reached')
            try:
                if digest(req['input']) != req['input_sha256']:
                    raise ValueError('Input mutated during role execution')
                value = read(path)
                validate(req['kind'], value, read(req['input']), ws)
            except (ValueError, KeyError, TypeError, AttributeError) as error:
                failed = request.parent/'rejected'
                n = len(list(failed.glob('*.json'))) + 1
                write(failed/f'{n:03d}.json', {'error': str(error), 'agent': agent,
                      'raw_result': path.read_text() if path.exists() else None, 'at': now()})
                raise ValueError(str(error)) from error
            artifacts = {}
            for item in value['artifacts']:
                p = Path(item['path'] if isinstance(item, dict) else item)
                p = p if p.is_absolute() else ws/p
                artifacts[str(p.resolve())] = digest(p)
            immutable(request.parent/'DELIVERY.json', {
                'result': str(path), 'result_sha256': digest(path), 'request_sha256': digest(request),
                'artifacts': artifacts, 'agent': agent, 'adapter': 'cli' if agent == 'cli' else 'collaboration',
                'requested_model': req['model'], 'requested_effort': req['effort'], 'at': now()})
            return path, value

    def batch(self, batch_id, jobs):
        # Freeze every request before executing or accepting any scientific state changes.
        manifest = self.root/'batches'/(batch_id+'.json')
        if manifest.exists():
            requests = [Path(p) for p in read(manifest)['requests']]
            if [read(p)['stage'] for p in requests] != [j['stage'] for j in jobs]:
                raise ValueError('Batch membership changed')
        else:
            requests = [self.prepare(**job) for job in jobs]
            immutable(manifest, {'requests': [str(p) for p in requests]})
        missing = [p for p in requests if self.delivery(p) is None]
        if missing and self.executor == 'cli':
            def execute(request):
                req = read(request)
                # One manifest per role; shared runtime manifests are not thread safe.
                try:
                    path, value = stage_run(request.parent/'cli', req['stage'], req['owner'],
                        req['prompt'], [Path(req['input'])], self.model, self.effort, self.timeout)
                    # Retain real CLI workspace; never rewrite agent-authored science.
                    ws = Path(req['workspace'])
                    import shutil
                    for p in path.parent.iterdir():
                        dest = ws/p.name
                        if p.is_file():
                            shutil.copy2(p, dest)
                        elif not dest.exists():
                            shutil.copytree(p, dest)
                    # Absolute artifact paths must point into assigned workspace. If not, queue repair.
                    self.deliver(req['stage'], 'cli')
                except Exception as error:
                    write(request.parent/'CLI_FAILURE.json', {'error': str(error), 'at': now()})
            with ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(execute, missing))
        missing = [p for p in requests if self.delivery(p) is None]
        if missing:
            write(self.root/'PENDING_ROLES.json', {'batch': batch_id, 'requests': [str(p) for p in missing]})
            raise PendingRoles(str(self.root/'PENDING_ROLES.json'))
        (self.root/'PENDING_ROLES.json').unlink(missing_ok=True)
        return {read(p)['stage']: self.delivery(p) for p in requests}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, required=True)
    p.add_argument('--stage', required=True)
    p.add_argument('--agent')
    p.add_argument('--validate-only', action='store_true')
    a = p.parse_args()
    runtime = BatchRuntime(a.root.resolve())
    if a.validate_only:
        try:
            print(json.dumps(runtime.preflight(a.stage)))
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as error:
            print(json.dumps({'status':'invalid','stage':a.stage,'error':str(error)}))
            raise SystemExit(1)
        return
    if not a.agent:
        p.error('--agent is required for an actual delivery')
    runtime.deliver(a.stage, a.agent)
    print(a.stage + ' validated; scientific state awaits the whole batch')


if __name__ == '__main__':
    main()
