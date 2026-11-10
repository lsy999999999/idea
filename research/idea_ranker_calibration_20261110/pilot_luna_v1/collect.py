"""Preserve only this pilot's native judge deliveries from its own child logs."""
from pathlib import Path
import datetime
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parent
PARENT = os.environ.get('CODEX_THREAD_ID', '01a1c4eb-4eb0-7182-9d34-5ae16327358e')
JOBS = json.loads((ROOT / 'controller_only/mapping.json').read_text())
BY_ID = {j['id']: j for j in JOBS}
RULES = (ROOT / 'JUDGE_RULES.txt').read_text()

def dump(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

def message_text(payload):
    return ''.join(c.get('text', '') for c in payload.get('content', [])
                   if isinstance(c, dict))

for date in ('2026/11/10', '2026/11/11'):
    directory = Path('/Users/LSY/.codex/sessions') / date
    if not directory.exists():
        continue
    for path in directory.glob('*.jsonl'):
        with path.open() as f:
            first = f.readline()
        try:
            meta = json.loads(first).get('payload', {})
            spawn = meta.get('source', {}).get('subagent', {}).get('thread_spawn', {})
        except (ValueError, AttributeError):
            continue
        if spawn.get('parent_thread_id') != PARENT:
            continue
        task = spawn.get('agent_path', '')
        if not task.startswith('/root/luna_p'):
            continue
        opaque = task.rsplit('_', 1)[-1].upper()
        if opaque not in BY_ID:
            continue
        target = ROOT / BY_ID[opaque]['relative_dir']
        if (target / 'receipt.json').exists():
            continue
        rows = []
        for line in path.read_text().splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass  # A writer may still be appending its last JSONL row.
        messages = [r['payload'] for r in rows if r.get('type') == 'response_item']
        finals = [r for r in messages if r.get('role') == 'assistant'
                  and r.get('phase') == 'final_answer']
        if not finals:
            continue
        raw = message_text(finals[-1])
        result = json.loads(raw)
        assert result['id'] == opaque
        task_messages = [r for r in messages if r.get('type') == 'agent_message']
        assert task_messages, opaque
        contexts = [r['payload'] for r in rows if r.get('type') == 'turn_context']
        assert contexts and all(c.get('model') == 'gpt-6-luna' for c in contexts)
        tool_calls = [r for r in messages if r.get('type') in
                      ('function_call', 'custom_tool_call', 'web_search_call')]
        usage = [r['payload'].get('info') for r in rows if r.get('type') == 'event_msg'
                 and r.get('payload', {}).get('type') == 'token_count'
                 and r.get('payload', {}).get('info')]
        (target / 'raw.txt').write_text(raw)
        dump(target / 'result.json', result)
        dump(target / 'receipt.json', {
            'requested_model': 'gpt-6-luna', 'recorded_model': contexts[-1].get('model'),
            'requested_effort': 'low', 'recorded_effort': contexts[-1].get('effort'),
            'transport': 'native_collaboration', 'context_fork': 'none',
            'task': task, 'session_id': meta.get('id'), 'source_rollout': str(path),
            'source_final_message_id': finals[-1].get('id'),
            'observed_tool_calls': len(tool_calls),
            'native_task_messages': len(task_messages),
            'prompt_audit': 'Controller submitted the frozen rules and packet, with compact JSON formatting. Native task payload is encrypted in logs; independent plaintext comparison is unavailable. Original prepared prompt and opaque task/session IDs are preserved.',
            'raw_sha256': hashlib.sha256(raw.encode()).hexdigest(),
            'usage': usage[-1] if usage else None,
        })

completed = [j for j in JOBS if (ROOT / j['relative_dir'] / 'receipt.json').exists()]
dump(ROOT / 'STATUS.json', {
    'status': 'deliveries_complete' if len(completed) == len(JOBS) else 'running',
    'total': len(JOBS), 'completed': len(completed), 'model': 'gpt-6-luna',
    'effort': 'low', 'transport': 'native_collaboration',
    'updated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
})
print('Saved', len(completed), '/', len(JOBS))
pending = [j for j in JOBS if j not in completed]
for j in pending[:3]:
    print('NEXT', j['id'], j['variant'],
          (ROOT / j['relative_dir'] / 'packet.json').read_text())
