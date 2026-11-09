"""Stage-scoped, lossless document references. Scientific text is never summarized away."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path


def dumps(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


class ContextStore:
    def __init__(self, directory, admission_guard=None):
        self.admission_guard=admission_guard
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.documents = {}
        self.paths = {}
        self.projections = {}
        manifest = self.directory / 'manifest.json'
        if manifest.exists():
            for ref, record in json.loads(manifest.read_text()).items():
                text = (self.directory / (ref+'.txt')).read_text()
                if hashlib.sha256(text.encode()).hexdigest() != record['sha256']:
                    raise ValueError('Stored document changed')
                if self.admission_guard:
                    for path in record['paths']:self.admission_guard(path,text)
                self.documents[ref] = {**record, 'text': text}
                for path in record['paths']:
                    self.paths[path] = ref

    def add(self, path, text):
        path = str(path)
        if self.admission_guard:self.admission_guard(path,text)
        if path in self.paths:
            old = self.documents[self.paths[path]]['text']
            if old != text:
                try:
                    if json.loads(old) != json.loads(text):
                        raise ValueError('Different versions supplied under one path: ' + path)
                except json.JSONDecodeError:
                    raise ValueError('Different versions supplied under one path: ' + path)
            return self.paths[path]
        digest = hashlib.sha256(text.encode()).hexdigest()
        ref = 'D' + digest[:20]
        record = self.documents.setdefault(ref, {'ref': ref, 'sha256': digest, 'text': text, 'paths': []})
        if record['text'] != text:
            raise ValueError('Document ID collision')
        record['paths'].append(path)
        self.paths[path] = ref
        (self.directory / (ref + '.txt')).write_text(text)
        return ref

    def add_file(self, path):
        path = Path(path).resolve()
        return self.add(str(path), path.read_text())

    def _project(self, value):
        if isinstance(value, list):
            return [self._project(v) for v in value]
        if not isinstance(value, dict):
            return value
        # Exact before-input/file snapshots, including the review's nested history.
        if isinstance(value.get('path'), str) and isinstance(value.get('text'), str):
            if value.get('sha256') and hashlib.sha256(value['text'].encode()).hexdigest() != value['sha256']:
                raise ValueError('Embedded snapshot hash mismatch: ' + value['path'])
            ref = self.add(value['path'], value['text'])
            return {**{k: self._project(v) for k, v in value.items() if k != 'text'}, 'text': {'$document': ref}}
        out = {}
        for key, item in value.items():
            if key == 'sources' and value.get('version') == 'hypothesis-cycle-v1' and isinstance(item, dict):
                out[key] = {p: {'$document': self.add(p, t)} for p, t in item.items()}
            elif key == 'result' and isinstance(value.get('path'), str) and isinstance(item, dict):
                snapshot=next((f['text'] for f in value.get('files',[]) if f.get('path')==value['path'] and isinstance(f.get('text'),str)),None)
                out[key] = {'$document': self.add(value['path'], snapshot if snapshot is not None else dumps(item))}
            else:
                out[key] = self._project(item)
        return out

    def prepare(self, paths):
        top = [self.add_file(p) for p in paths]
        # All top-level originals are installed before embedded copies are visited.
        while True:
            pending = [r for r in self.documents if r not in self.projections]
            if not pending:
                break
            for ref in pending:
                text = self.documents[ref]['text']
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = text
                self.projections[ref] = self._project(parsed)
        self.save()
        return list(dict.fromkeys(top))

    def save(self):
        (self.directory / 'manifest.json').write_text(json.dumps({r: {k: v for k, v in d.items() if k != 'text'} for r, d in self.documents.items()}, ensure_ascii=False, indent=2))

    def resolve(self, ref):
        ref = self.paths.get(ref, ref)
        if ref not in self.documents:
            raise ValueError('Not a supplied document ID/path; no arbitrary filesystem access')
        return ref

    def read(self, ref, pointer='', offset=0, limit=10000, raw=False):
        ref = self.resolve(ref)
        if self.admission_guard:
            for path in self.documents[ref]['paths']:self.admission_guard(path,self.documents[ref]['text'])
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 12000:
            raise ValueError('Use nonnegative offset and limit 1..12000')
        source = self.documents[ref]['text']
        if pointer:
            if not pointer.startswith('/'):
                raise ValueError('Use a JSON pointer starting with /')
            obj = json.loads(source)
            for token in pointer[1:].split('/'):
                token = token.replace('~1', '/').replace('~0', '~')
                obj = obj[int(token)] if isinstance(obj, list) else obj[token]
            text = dumps(self._project(obj)) if not raw else dumps(obj)
        elif raw:
            text = source
        else:
            text = self.projections.get(ref, source)
            if not isinstance(text, str):
                text = dumps(text)
        self.save()
        return {'ref': ref, 'sha256': self.documents[ref]['sha256'], 'pointer': pointer,
                'offset': offset, 'text': text[offset:offset+limit],
                'next_offset': offset+limit if offset+limit < len(text) else None,
                'total_characters': len(text), 'raw_original': raw}

    def packet(self, top, max_inline_chars=36000):
        if self.admission_guard:
            for doc in self.documents.values():
                for path in doc['paths']:self.admission_guard(path,doc['text'])
        catalog = [{k: v for k, v in self.documents[r].items() if k != 'text'} for r in self.documents]
        inline = []
        # State/role contracts first; large review histories remain addressable by ID.
        order = sorted(top, key=lambda r: 0 if any('/researcher_context/' in p for p in self.documents[r]['paths']) else 1)
        remaining = max_inline_chars
        # Review targets are needed immediately; avoid one model round-trip per small result.
        for ref in list(order):
            body=self.projections[ref]
            if isinstance(body,dict) and isinstance(body.get('sources'),dict):
                for source in body['sources'].values():
                    if isinstance(source,dict) and isinstance(source.get('result'),dict):
                        target=source['result'].get('$document')
                        if target in self.projections and target not in order:order.append(target)
        for ref in order:
            value = self.projections[ref]
            size = len(dumps(value))
            if size <= remaining:
                inline.append({'ref': ref, 'content': value})
                remaining -= size
        return {'format': 'lossless-document-references-v1', 'instructions':
                'Each document body occurs once. $document refers to the catalog. Use read_document for omitted bodies or exact original quotes; it is not a summary. Only these stage-scoped documents are readable.',
                'input_refs': top, 'documents': catalog, 'inline': inline}

    def source_bindings(self, context):
        cycle = context.get('development_cycle', {})
        bindings = {}
        for path in cycle.get('sources', {}):
            if path in self.paths:
                bindings.setdefault(self.paths[path], path)
        return bindings
