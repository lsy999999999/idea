"""Offline workflow checks, source diff and parent-integrity audit; no model calls."""
from pathlib import Path
import sys,unittest,json,hashlib,difflib,io,contextlib
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'runtime'))
import run_ours
loader=unittest.TestLoader()
suite=loader.discover(str(root/'runtime'),pattern='test_*.py')
# State and request regressions exercise the changed general-purpose modules as well.
sys.path.insert(0,str(root/'runtime/ours_source/historical_inquiry'))
for module in ['test_question_state.QuestionStateTests','test_hypothesis_development.HypothesisTests']:
 suite.addTests(loader.loadTestsFromName(module))
log=io.StringIO()
with contextlib.redirect_stdout(log),contextlib.redirect_stderr(log):
 result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
(root/'TEST_RESULTS.txt').write_text(log.getvalue())
parent=json.loads((root/'PARENT_FREEZE.json').read_text())
changed=[p for p,sha in parent.items() if not Path(p).is_file() or hashlib.sha256(Path(p).read_bytes()).hexdigest()!=sha]
report={'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'successful':result.wasSuccessful(),
 'parent_files_checked':len(parent),'parent_files_changed':changed,'real_model_calls':0,'scientific_run_started':False,
 'validation_scope':'Offline synthetic integration and regression checks; semantic model judgments and scientific benefit are untested.'}
(root/'VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
base=root.parent/'hypothesis_continuation_20261109'
diff=[];changes=[]
for p in sorted((root/'runtime').rglob('*.py')):
 rel=p.relative_to(root);old=base/rel
 before=old.read_text() if old.exists() else ''
 after=p.read_text()
 if before!=after:
  changes.append(str(rel));diff.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='parent/'+str(rel),tofile='development/'+str(rel)))
(root/'CODE_CHANGES.diff').write_text(''.join(diff))
(root/'CHANGED_FILES.json').write_text(json.dumps(changes,indent=2))
print(json.dumps(report,ensure_ascii=False));print('Changed/new Python files:',len(changes))
if not result.wasSuccessful():print(log.getvalue()[-7000:])
if not result.wasSuccessful() or changed:sys.exit(1)
