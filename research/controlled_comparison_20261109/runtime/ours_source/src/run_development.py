"""Continue a frozen inquiry using cloned memory; original runs remain read-only."""
import argparse
import fcntl
from pathlib import Path
import shutil

from discover import inside, read, write
from learning_memory import Memory, digest
from learning_lab import CASES
from learning_support import default_policy
from research_portfolio import Portfolio, COMMON
from portfolio_runtime import immutable, PendingRoles
from idea_check import CHECKER_PROMPT, POLICY


def clone_memory(source, target):
    manifest=target.parent/'MEMORY_CLONE.json'
    if manifest.exists():
        return
    before={str(p):digest(p) for p in source.rglob('*') if p.is_file()}
    if target.exists():
        raise ValueError('Incomplete memory clone; inspect before retrying')
    shutil.copytree(source,target)
    for p in target.glob('*/index.json'):
        index=read(p)
        for entry in index['notes'].values():
            # Note contents remain byte identical, including original source provenance.
            old=Path(entry['path'])
            relative=old.relative_to(source) if old.is_relative_to(source) else Path(p.parent.name)/'notes'/old.parent.name/old.name
            new=target/relative
            if digest(new)!=entry['sha256']:
                raise ValueError('Memory clone does not match original index')
            entry['path']=str(new)
        write(p,index)
    immutable(manifest,{'original_files':before,'cloned_to':str(target)})


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-run',required=True,type=Path)
    p.add_argument('--source-memory',required=True,type=Path)
    p.add_argument('--run',required=True,type=Path)
    p.add_argument('--case',choices=list(CASES),default='wine')
    p.add_argument('--periods',type=int,default=1)
    p.add_argument('--slots',type=int,default=2)
    p.add_argument('--call-budget',type=int,default=23)
    p.add_argument('--executor',choices=['queue','cli'],default='queue')
    a=p.parse_args()
    source,memory_source,run=inside(a.source_run),inside(a.source_memory),inside(a.run)
    if run==source or run.is_relative_to(source) or memory_source.is_relative_to(run):
        p.error('Use a separate new destination')
    run.mkdir(parents=True,exist_ok=True)
    with (run/'.controller.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        prepared=run/'PREPARED.json'
        if not prepared.exists():
            old_freeze=read(source/'GENERATION_FREEZE.json')
            for name,h in old_freeze['files'].items():
                if digest(name)!=h:
                    raise ValueError('Source generation freeze changed')
            cards=read(source/'candidate_history.json')['current_hypotheses']
            seeds=[{'id':f'D{i+1:03d}','seed':c} for i,c in enumerate(cards)]
            common=[]
            for s in read(source/'source_catalog.json')['sources']:
                path=Path(s.get('archived_path',s['local_path']))
                common.append({'id':s['id'],'url':s['url'],'content_access':s['content_access'],
                    'path':str(path),'sha256':digest(path),'text':path.read_text(errors='replace')})
            immutable(prepared,{'seeds':seeds,'common':common,'source_run':str(source),
                'source_memory':str(memory_source),'knowledge_policy':default_policy()})
        data=read(prepared)
        if data['source_run']!=str(source) or data['source_memory']!=str(memory_source):
            raise ValueError('Continuation source changed')
        clone_memory(memory_source,run/'researchers')
        memory=Memory(run/'researchers')
        config={'periods':a.periods,'rounds':2,'slots':a.slots,'call_budget':a.call_budget,
                'model':'gpt-6-luna','effort':'low','timeout':300,'knowledge_policy':data['knowledge_policy']}
        portfolio=Portfolio(run/'development',memory,CASES[a.case],data['seeds'],data['common'],config,a.executor)
        try:
            path,result=portfolio.run()
            idea_path=immutable(run/'ideas.json',{'source':str(path),'ideas':result['ideas']})
            freeze=run/'GENERATION_FREEZE.json'
            if not freeze.exists():
                immutable(freeze,{'files':{str(p):digest(p) for folder in ('development','researchers')
                    for p in (run/folder).rglob('*') if p.is_file() and p.name!='.delivery.lock'},
                    'ideas_sha256':digest(idea_path)})
            def verify():
                for name,h in read(freeze)['files'].items():
                    if digest(name)!=h:
                        raise ValueError('Frozen generation or memory changed')
                if digest(idea_path)!=read(freeze)['ideas_sha256']:
                    raise ValueError('Frozen ideas changed')
            verify()
            if result['ideas']:
                from portfolio_runtime import BatchRuntime
                runtime=BatchRuntime(run/'evaluation')
                checked=runtime.batch('final',[dict(stage='final_check',kind='checker',owner='final_checker',
                    prompt=COMMON+CHECKER_PROMPT+'\nSave source snapshots. Bounded run: at most 8 minutes. Report actual coverage and unresolved evidence honestly.',
                    packet={'ideas':result['ideas'],'checker_policy':POLICY.read_text()})])
                immutable(run/'check_report.json',next(iter(checked.values()))[1])
            else:
                immutable(run/'check_report.json',{'checks':[],'searches':[]})
            verify()
            immutable(run/'COMPLETE.json',{'generation_frozen':True,'memory_unchanged_during_check':True,
                'researcher_calls_after_check':0,'scope':'Workflow trial; not demonstrated idea-quality improvement.'})
            print('complete: '+str(run))
        except PendingRoles as error:
            print('awaiting native roles: '+str(error),flush=True)
            raise SystemExit(75)


if __name__=='__main__':
    main()
