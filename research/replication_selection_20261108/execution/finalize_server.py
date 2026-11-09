from pathlib import Path
import shlex
from server_ops import connect

root=Path(__file__).resolve().parent
client=connect()
try:
    s=client.open_sftp();remote=s.normalize('.')+'/ideas_replication_20261108'
    script='''import json,subprocess,pathlib
p=pathlib.Path(__file__).resolve().parent
d={'gpu':subprocess.getoutput('nvidia-smi --query-gpu=index,name,memory.total,memory.used,utilization.gpu --format=csv,noheader'),'experiment_processes':subprocess.run(['pgrep','-af','^.venv/bin/python -u server_experiment.py'],capture_output=True,text=True).stdout}
(p/'FINAL_RESOURCE_STATUS.json').write_text(json.dumps(d,indent=2))
print(json.dumps(d))
'''
    with s.open(remote+'/final_resource.py','w') as f:f.write(script)
    _,o,e=client.exec_command('python3 '+shlex.quote(remote+'/final_resource.py'),timeout=20)
    print(o.read().decode());print(e.read().decode())
    s.get(remote+'/FINAL_RESOURCE_STATUS.json',str(root/'runs/scientist_v2/server/FINAL_RESOURCE_STATUS.json'))
    _,o,e=client.exec_command(shlex.quote(remote+'/.venv/bin/pip')+' freeze',timeout=20)
    (root/'server_runtime_freeze.txt').write_text(o.read().decode())
finally:client.close()
