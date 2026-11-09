from pathlib import Path
import json
import shlex
from server_ops import connect

root = Path(__file__).resolve().parent
client = connect()
try:
    sftp = client.open_sftp()
    home = sftp.normalize('.')
    remote = home + '/ideas_replication_20261108'
    try:
        sftp.mkdir(remote)
    except IOError:
        pass
    sftp.put(str(root/'scientist_v2.zip'), remote+'/scientist_v2.zip')
    base_python = home+'/machinelearning/machinelearning_inruc/.conda-gpu/bin/python'
    setup = f'''set -e
cd {shlex.quote(remote)}
{shlex.quote(base_python)} -m venv --system-site-packages .venv
.venv/bin/python -c "import zipfile; zipfile.ZipFile('scientist_v2.zip').extractall('upstream')"
.venv/bin/pip install -q openai anthropic backoff humanize dataclasses-json funcy rich omegaconf genson coolname shutup python-igraph jsonschema tiktoken
.venv/bin/python -c "import torch; from pathlib import Path; import sys; sys.path.insert(0,str(next(Path('upstream').iterdir()))); from ai_scientist.treesearch.parallel_agent import MinimalAgent; print('READY',torch.__version__,torch.cuda.is_available(),torch.cuda.get_device_name(0))"
'''
    with sftp.open(remote+'/setup.sh', 'w') as f:
        f.write(setup)
    (root/'server_location.json').write_text(json.dumps({'priority_server':'10.42.127.214','directory':remote,'python':remote+'/.venv/bin/python'},indent=2))
    _, stdout, stderr = client.exec_command('bash '+shlex.quote(remote+'/setup.sh'), timeout=240)
    print(stdout.read().decode(errors='replace'))
    print(stderr.read().decode(errors='replace'))
    print('setup_exit', stdout.channel.recv_exit_status())
finally:
    client.close()
