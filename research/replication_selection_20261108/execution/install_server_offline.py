from pathlib import Path
import tarfile
import shlex
from server_ops import connect

root=Path(__file__).resolve().parent
with tarfile.open(root/'server_wheels.tar.gz','w:gz') as tar:
    tar.add(root/'server_wheels',arcname='wheels')
client=connect()
try:
    s=client.open_sftp();remote=s.normalize('.')+'/ideas_replication_20261108'
    s.put(str(root/'server_wheels.tar.gz'),remote+'/wheels.tar.gz')
    cmd=f'''cd {shlex.quote(remote)}
tar -xzf wheels.tar.gz
.venv/bin/pip install --no-index --no-deps wheels/*.whl > install.log 2>&1
.venv/bin/python -c "import torch; from pathlib import Path; import sys; sys.path.insert(0,str(next(Path('upstream').iterdir()))); from ai_scientist.treesearch.parallel_agent import MinimalAgent; print('READY',torch.__version__,torch.cuda.is_available(),torch.cuda.get_device_name(0))"
'''
    _,o,e=client.exec_command(cmd,timeout=90)
    print(o.read().decode());print(e.read().decode());print('exit',o.channel.recv_exit_status())
finally:client.close()
