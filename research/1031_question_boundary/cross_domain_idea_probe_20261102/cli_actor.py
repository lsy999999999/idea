"""Fresh Codex CLI transport for an existing frozen actor input."""
import json
import subprocess
import sys
import time
from pathlib import Path
import harness as h

def main():
    rid,label=sys.argv[1:3];run=h.ROOT/'runs'/rid
    dispatch=h.read(run/'inputs'/f'{label}_dispatch.json')
    assert h.sha(Path(dispatch['input_path']))==dispatch['input_sha256']
    assert not (run/'replies'/f'{label}.json').exists()
    command=['/opt/homebrew/bin/codex','exec','--ephemeral','--skip-git-repo-check','--model','gpt-6-luna','--sandbox','workspace-write','--color','never','--json','--output-last-message',str(run/'inputs'/f'{label}_cli_final.txt'),'-C',str(run),'-']
    h.dump(run/'inputs'/f'{label}_cli_command.json',dict(command=command,prompt=dispatch['prompt'],time=h.now(),scope='Same scientific input and requested model; fresh process; account authorization handled internally by CLI, not read or copied.'))
    start=time.monotonic()
    with (run/'inputs'/f'{label}_cli_events.jsonl').open('x') as stdout,(run/'inputs'/f'{label}_cli_stderr.txt').open('x') as stderr:
        completed=subprocess.run(command,input=dispatch['prompt'],text=True,stdout=stdout,stderr=stderr,timeout=900)
    output=run/'replies'/f'{label}.json'
    valid=False;error=None
    try:h.read(output);valid=True
    except Exception as exc:error=str(exc)
    report=dict(time=h.now(),returncode=completed.returncode,seconds=time.monotonic()-start,reply_exists=output.exists(),reply_json_valid=valid,error=error,model_requested='gpt-6-luna',transport='codex exec --ephemeral')
    h.dump(run/'inputs'/f'{label}_cli_completion.json',report)
    print(json.dumps(dict(run=rid,label=label,**report)))
    if completed.returncode or not valid:sys.exit(1)

if __name__=='__main__':main()
