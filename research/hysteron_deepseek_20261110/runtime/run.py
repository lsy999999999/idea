"""Run the revised inquiry and optional independent terminal check in this new copy."""
import argparse,fcntl,subprocess,sys,time,traceback
from contextlib import contextmanager
import run_ours as m


@contextmanager
def gateway():
    endpoint=m.ROOT/'gateway_endpoint.json'
    if endpoint.exists():raise ValueError('A gateway endpoint already exists; inspect it before starting another run')
    with (m.ROOT/'generation_gateway.log').open('a') as log:
        process=subprocess.Popen([sys.executable,str(m.ROOT/'runtime/model_gateway.py')],stdout=log,stderr=subprocess.STDOUT)
        try:
            for _ in range(200):
                if endpoint.exists():break
                if process.poll() is not None:raise RuntimeError('Gateway startup failed; inspect generation_gateway.log')
                time.sleep(.1)
            else:raise RuntimeError('Gateway startup timed out')
            yield
        finally:
            process.terminate()
            try:process.wait(timeout=10)
            except subprocess.TimeoutExpired:process.kill();process.wait()
            if endpoint.exists() and m.read(endpoint).get('pid')==process.pid:endpoint.unlink()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--case',choices=['optical','wave','hysteron'],default='optical')
    parser.add_argument('--no-evaluate',action='store_true',help='Freeze generation without running the independent terminal check')
    args=parser.parse_args()
    cfg=m.read(m.ROOT/'model_config.json')
    with (m.ROOT/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            with gateway():
                adapter=m.StageAdapter(m.ROOT,args.case,'generation',cfg,knowledge=cfg.get('knowledge','online'))
                adapter.generation()
            m.write(adapter.out/'STATUS.json',{'status':'complete','transport':m.VERSION,'generation_frozen':True})
            if not args.no_evaluate:
                from evaluate_frozen import main as evaluate
                evaluate(args.case)
        except Exception as error:
            m.write(m.ROOT/'LAST_FAILURE.json',{'error_type':type(error).__name__,'error':str(error),'traceback':traceback.format_exc()})
            raise

if __name__=='__main__':main()
