from pathlib import Path
import json
import tomllib
import urllib.request
import urllib.error

root = Path(__file__).resolve().parent
config = tomllib.loads(Path('/Users/LSY/.codex/config.toml').read_text())
auth = json.loads(Path('/Users/LSY/.codex/auth.json').read_text())
base = config['model_providers'][config['model_provider']]['base_url'].rstrip('/')
key = auth.get('OPENAI_API_KEY')
rows = []
for suffix in ['/models', '/v1/models']:
    try:
        req = urllib.request.Request(base + suffix, headers={'Authorization': 'Bearer ' + key})
        with urllib.request.urlopen(req, timeout=20) as response:
            data = json.load(response)
        models = [m['id'] for m in data.get('data', [])]
        row = {'route': suffix, 'models': models}
    except Exception as exc:
        row = {'route': suffix, 'error': type(exc).__name__, 'detail': str(exc)}
    rows.append(row)
    print(json.dumps(row))
(root/'provider_probe.json').write_text(json.dumps(rows, indent=2))
