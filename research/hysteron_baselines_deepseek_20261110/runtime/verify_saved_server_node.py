"""Execute the exact saved second node after correcting a false-positive Agg gate."""
from common import *
import ast,shlex
sys.path.insert(0,str(UP/'execution'))
from server_ops import connect

if __name__=='__main__':
 source=ROOT/'runs/scientist_v2/server/node_1.py';code=source.read_text()
 tree=ast.parse((ROOT/'runtime/server_scientist.py').read_text());function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate')
 scope={'ast':ast,'Path':Path};exec(compile(ast.Module(body=[function],type_ignores=[]),'validation','exec'),scope);scope['validate'](code)
 out=ROOT/'controller_only/server_node_verification';out.mkdir(parents=True,exist_ok=True)
 ssh=connect();s=ssh.open_sftp();remote=s.normalize('.')+'/'+ROOT.name+'/controller_verification'
 try:
  try:s.mkdir(remote)
  except IOError:pass
  s.put(str(source),remote+'/node_1.py');s.put(str(ROOT/'cases/hysteron/measurements.csv'),remote+'/measurements.csv')
  cmd='cd '+shlex.quote(remote)+' && OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 MPLBACKEND=Agg timeout 120 /home/lsy/ideas_replication_20261108/.venv/bin/python node_1.py'
  started=time.monotonic();_,o,err=ssh.exec_command(cmd,timeout=140)
  output=o.read().decode();errors=err.read().decode();exit_code=o.channel.recv_exit_status()
  dump(out/'EXECUTION.json',{'status':'executed' if exit_code==0 else 'failed','exit_code':exit_code,'stdout':output,'stderr':errors,'seconds':time.monotonic()-started,'code_sha256':hashlib.sha256(code.encode()).hexdigest(),'code_source':str(source),'scope':'Controller verification of exact model-authored code; native frozen generation and terminal evaluator inputs unchanged. Original gate blocked harmless matplotlib.use(Agg). No new model call.'})
  try:s.get(remote+'/figure.png',str(out/'figure.png'))
  except IOError:pass
  print('Exact saved server node exit',exit_code,flush=True)
 finally:ssh.close()
