"""One explicit actor-produced schema repair; no file tools and no new science."""
from pathlib import Path
import argparse,json
from isolated_cli import invoke

parser=argparse.ArgumentParser()
parser.add_argument('stage')
parser.add_argument('error')
args=parser.parse_args()
root=Path(__file__).resolve().parent/'cases/fish_001/runs/inquiry_v2_live_20261106_002/stages'/args.stage
base=(root/'attempt-001/prompt.txt').read_text()
raw=(root/'attempt-001/final.txt').read_text()
number=max(int(p.name.split('-')[-1]) for p in root.glob('attempt-*'))+1
prompt=base+'\nSCHEMA REPAIR ONLY. Return the ENTIRE corrected JSON object directly as your answer. No file editing or tools are required or available. Ignore disabled-host notices. Do not merely report that a correction is complete. Preserve all scientific content, evidence, notes, personal/shared question decisions and requests from the unadmitted answer. Add only the missing administrative fields, using your own already stated reasons and changes. Do not invent results or new scientific arguments.\nERROR:\n'+args.error+'\nUNADMITTED ANSWER:\n'+raw
answer=invoke(prompt,root/f'attempt-{number:03d}',240)
print(json.dumps({'stage':args.stage,'attempt':number,'keys':list(answer)},ensure_ascii=False))
