"""Offline packaging measurement on frozen real inputs; no model calls."""
import hashlib, importlib.util, json, sys, shutil
from pathlib import Path
import tiktoken
ROOT=Path(__file__).resolve().parent
shutil.rmtree(ROOT/'measurement_v2', ignore_errors=True)
RUNTIME=ROOT.parent/'controlled_comparison_20261109/runtime'
sys.path.insert(0,str(RUNTIME))
from research_context import ContextStore,dumps
from submission_repair import save_draft,repair_context
from run_ours import lab
from learning_support import review_packet
encoding=tiktoken.get_encoding('o200k_base')
def tokens(x):return len(encoding.encode(dumps(x)))
old_path=ROOT/'before/1/research_context.py'
spec=importlib.util.spec_from_file_location('old_context',old_path);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
source=ROOT.parent/'controlled_comparison_20261109/runs/optical/ours/generation/inquiry/internal_review/inputs.json'
frozen=json.loads(source.read_text())
# Use the frozen snapshots directly for the before comparison.
old_store=old.ContextStore(ROOT/'measurement_v2/old_documents');top=old_store.prepare([source]);old_view=old_store.packet(top,max_inline_chars=42000)
# Recreate an isolated set of identical files so no historical artifacts are written.
remap={}
for stage,row in frozen['sources'].items():
 for record in [*row['files'],*row.get('before_inputs',[])]:
  original=record['path'];text=record['text']
  if original in remap:
   assert remap[original].read_text()==text
   continue
  folder=ROOT/'measurement_v2/exact_inputs'/hashlib.sha256(str(Path(original).parent).encode()).hexdigest()[:16]
  folder.mkdir(parents=True,exist_ok=True)
  target=folder/Path(original).name;target.write_text(text);remap[original]=target
stages={stage:(row['owner'],remap[row['path']]) for stage,row in frozen['sources'].items()}
before={stage:[remap[x['path']] for x in row.get('before_inputs',[])] for stage,row in frozen['sources'].items()}
index=review_packet(stages,before);index_path=ROOT/'measurement_v2/review_index.json';index_path.write_text(dumps(index))
store=ContextStore(ROOT/'measurement_v2/new_documents',review_indexes=[index_path]);top=store.prepare([index_path]);view=store.packet(top,max_inline_chars=42000)
# Verify every input and reviewed result remains exact and addressable.
for target in remap.values():
 assert store.documents[store.resolve(str(target.resolve()))]['text']==target.read_text()
# Packaging-only repair example with a real frozen author result and one deliberate schema error.
row=next(iter(frozen['sources'].values()));draft=json.loads(json.dumps(row['result']));draft['summary']=[]
pending=save_draft(ROOT/'measurement_v2',store,draft)
error={'message':'summary must be a nonempty string'}
initial=[{'role':'system','content':'Research stage; repair only the reported field.'}, {'role':'user','content':dumps(view)}]
full=[*initial,{'role':'assistant','tool_calls':[{'function':{'name':'submit_result','arguments':dumps({'result':draft})}}]}, {'role':'user','content':dumps(error)}]
compact=repair_context(initial,store,pending,error)
result={'scope':'Offline o200k_base serialization counts; not model usage, billing or scientific-effect evidence.',
 'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
 'review':{'previous_v6_initial_tokens':tokens(old_view),'new_index_initial_tokens':tokens(view),
           'original_nested_packet_tokens':tokens(frozen),'registered_documents':len(store.documents),
           'all_original_texts_verified':len(remap),'index_bytes':len(index_path.read_bytes())},
 'repair_example':{'full_draft_history_tokens':tokens(full),'compact_repair_tokens':tokens(compact), 'initial_context_tokens':tokens(initial), 'full_history_increment':tokens(full)-tokens(initial), 'repair_increment':tokens(compact)-tokens(initial),
                   'note':'Repair sends only new document IDs; actual savings depend on draft size and subsequent reads.'}}
result['review']['initial_reduction_fraction']=1-result['review']['new_index_initial_tokens']/result['review']['previous_v6_initial_tokens']
(ROOT/'CONTEXT_MEASUREMENT.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
