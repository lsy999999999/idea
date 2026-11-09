"""Persist author drafts and apply explicit, atomic field edits without model rewriting."""
from copy import deepcopy
import hashlib
import json
import re


def apply_edits(draft, edits):
    if not isinstance(draft, dict):
        raise ValueError('Draft must be an object')
    if not isinstance(edits, list) or not 1 <= len(edits) <= 24:
        raise ValueError('Supply 1..24 field edits')
    result = deepcopy(draft)
    for edit in edits:
        if not isinstance(edit, dict) or edit.get('op') not in {'set', 'remove'}:
            raise ValueError('Edit op must be set or remove')
        pointer = edit.get('path')
        if not isinstance(pointer, str) or not pointer.startswith('/') or re.search(r'~(?![01])', pointer):
            raise ValueError('Edit path must be a valid non-root JSON pointer')
        tokens = [t.replace('~1', '/').replace('~0', '~') for t in pointer[1:].split('/')]
        parent = result
        for token in tokens[:-1]:
            parent = parent[_index(token, len(parent))] if isinstance(parent, list) else parent[token]
        key = tokens[-1]
        if edit['op'] == 'set' and 'value' not in edit:
            raise ValueError('Set requires an explicit value')
        if isinstance(parent, list):
            if key == '-' and edit['op'] == 'set':
                parent.append(deepcopy(edit['value']))
            else:
                index = _index(key, len(parent))
                if edit['op'] == 'remove':
                    parent.pop(index)
                else:
                    parent[index] = deepcopy(edit['value'])
        elif isinstance(parent, dict):
            if edit['op'] == 'remove':
                del parent[key]
            else:
                parent[key] = deepcopy(edit['value'])
        else:
            raise ValueError('Edit parent must be an object or array')
    return result


def _index(token, size):
    if not re.fullmatch(r'0|[1-9][0-9]*', token) or int(token) >= size:
        raise ValueError('Array index must identify an existing item; use - to append')
    return int(token)


def save_draft(workspace, store, draft):
    if not isinstance(draft, dict):
        raise ValueError('Draft must be an object')
    text = json.dumps(draft, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    digest = hashlib.sha256(text.encode()).hexdigest()
    path = workspace / 'drafts' / (digest + '.json')
    path.parent.mkdir(exist_ok=True)
    if path.exists() and path.read_text() != text:
        raise ValueError('Saved draft changed')
    path.write_text(text)
    ref = store.add_file(path)
    store.prepare([])
    return {'ref': ref, 'sha256': digest, 'fields': list(draft)}


def load_draft(store, current, expected_ref):
    if current is None or expected_ref != current['ref']:
        raise ValueError('Stale or unknown draft_ref; use the latest pending draft')
    text = store.documents[store.resolve(expected_ref)]['text']
    if hashlib.sha256(text.encode()).hexdigest() != current['sha256']:
        raise ValueError('Pending draft hash mismatch')
    return json.loads(text)


def repair_context(initial, store, pending, feedback):
    """Keep originals on disk; a fresh repair request carries pointers, not failed JSON."""
    known = {pending['ref']}
    for message in initial:
        try:
            packet = json.loads(message.get('content', ''))
            if isinstance(packet, dict):
                known.update(row['ref'] for row in packet.get('documents', []))
        except (ValueError, TypeError, KeyError):
            pass
    catalog = [row for row in store.catalog() if row['ref'] not in known
               and not any('/drafts/' in p for p in store.documents[row['ref']]['paths'])]
    request = {'task': 'Repair only the reported fields of the saved draft using patch_result. '
               'Do not resubmit the whole result. Read a draft section by ref and JSON pointer if needed. '
               'The initial catalog plus new_documents locate prior scientific documents and tool results. '
               'No scientific claim has been corrected by the controller.',
               'draft': {'ref': pending['ref'], 'fields': pending['fields']},
               'feedback': {key: value for key, value in feedback.items() if key != 'draft'},
               'new_documents': catalog}
    return [*deepcopy(initial), {'role': 'user', 'content': json.dumps(request, ensure_ascii=False)}]
