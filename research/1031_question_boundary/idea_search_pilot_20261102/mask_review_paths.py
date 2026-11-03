"""Remove method labels leaked by execution traceback paths, not scientific content."""
import json
import re
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import pilot as p

def scrub(x):
    if isinstance(x,list):return [scrub(v) for v in x]
    if isinstance(x,dict):return {k:scrub(v) for k,v in x.items()}
    if isinstance(x,str):
        base=p.ROOT.parent if p.ROOT.name=='format_recovery' else p.ROOT
        x=re.sub(re.escape(str(base))+r'(?:/format_recovery)?/runs/(wine|shopping)_[ABC]/r[123]', '<masked_run>',x)
        x=re.sub(r'\b(wine|shopping)_[ABC]/r[123]\b','<masked_run>',x)
    return x

original=p.ROOT/'review_inputs'
backup=p.ROOT/'review_inputs_before_path_redaction'
assert original.exists() and not backup.exists()
original.rename(backup);original.mkdir()
for case in p.CASES:p.write(original/f'{case}.json',scrub(p.read(backup/f'{case}.json')))
p.write(original/'FROZEN.json',{'time':p.now(),'instruction_sha256':p.sha(p.ROOT/'REVIEW_INSTRUCTIONS.md'),'mask_code_sha256':p.sha(Path(__file__)),'inputs':{case:p.sha(original/f'{case}.json') for case in p.CASES},'prior_frozen_manifest':p.sha(backup/'FROZEN.json'),'reason':'Tracebacks expose arm identifiers in filesystem paths. Uniform redaction before any reviewer call; no rubric or scientific evidence changed. Originals preserved.'})
print('Arm-bearing traceback paths masked; original review bundles preserved')
