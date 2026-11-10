"""Content-directed research turns and demand-driven expertise; no novelty score."""
from pathlib import Path
import hashlib
import re
from discover import read, write

OPERATIONS = {'derive', 'construct', 'combine', 'simplify', 'vary_assumption', 'reframe', 'differentiate', 'learn', 'hold'}
ROUND_PROTOCOL = '''
Develop an unfinished explanatory hypothesis using the supplied actual research history.
Select a useful operation: derive, construct, combine, simplify, vary_assumption, reframe,
differentiate, learn, or hold. Carry out the operation: explain the entities, relations,
reasoning and conditional consequences, rather than merely recommend doing it later.
Use development_step.work for the actual reasoning (or a concrete unresolved obstacle).
Use examples only when they advance this reasoning; memory use needs no demonstration.
A shared interpretation is normal. Continue deepening it; do not manufacture disagreement.
If changing representation or borrowing another field, explain the object/relation mapping,
where it fails, and what new relation/consequence it enables. A generic analogy is a lead.
If two prior research outputs are supplied in progress_comparison, compare THEIR substantive
claims, assumptions and consequences, not labels or wording. Return progress_review:
{before_stage,after_stage,kind:advance/clarification/repetition/uncertain,reason}.
These are peer judgments, not verified novelty/quality scores; incomplete ideas remain valid.
For repeated clarification/repetition, choose an appropriate new move or explain specifically
why further work on the same relation is useful. Keep unavailable case facts distinct from
conditional reasoning. You may develop another relation while a fact remains unknown.
Return next_research_move:{action:develop/learn/consult/park/finish,operation,focus,reason,
owner:optional active researcher id}. It determines the next turn, not hypothesis acceptance.
finish means no useful next move within this session; retain unfinished hypotheses.
Optionally return expertise_request:{domain,relation,task,mode:consult/join} when additional
expertise is needed for a SPECIFIC relation. A consultation is one turn; join participates in
later turns. Same-field experts are allowed. Do not add a role merely to increase diversity.
Use the existing hypothesis_updates and provenance machinery. Empty updates are valid.
'''


def validate_research_turn(result, packet):
    if packet is None:
        return
    step = result.get('development_step', {})
    if not isinstance(step.get('work'), str) or not step['work'].strip():
        raise ValueError('Describe actual research reasoning or the specific unresolved obstacle in development_step.work')
    move = result.get('next_research_move')
    if not isinstance(move, dict) or move.get('action') not in {'develop','learn','consult','park','finish'}:
        raise ValueError('Choose next_research_move.action')
    if move.get('operation') not in OPERATIONS:
        raise ValueError('Unknown research operation')
    if any(not isinstance(move.get(k),str) or not move[k].strip() for k in ('focus','reason')):
        raise ValueError('Next move requires a specific focus and reason')
    if move.get('owner') is not None and move['owner'] not in packet['active_researchers']:
        raise ValueError('Next owner must be an active researcher')
    expected = packet.get('progress_comparison')
    review = result.get('progress_review')
    if expected:
        if not isinstance(review,dict) or any(review.get(k)!=expected[k] for k in ('before_stage','after_stage')):
            raise ValueError('Progress review must compare the supplied actual stage pair')
        if review.get('kind') not in {'advance','clarification','repetition','uncertain'} or not isinstance(review.get('reason'),str) or not review['reason'].strip():
            raise ValueError('Explain the concrete semantic comparison; labels alone are insufficient')
    if move['action']=='learn':
        req=result.get('learning_request',{})
        if not (req.get('needed') or req.get('case_questions') or req.get('operations') or result.get('analysis_plan')):
            raise ValueError('A learning move requires an actual knowledge, case-fact or analysis request')
    expertise = result.get('expertise_request')
    if expertise is not None:
        if not isinstance(expertise,dict) or expertise.get('mode') not in {'consult','join'}:
            raise ValueError('Expertise mode must be consult or join')
        if any(not isinstance(expertise.get(k),str) or not expertise[k].strip() for k in ('domain','relation','task')):
            raise ValueError('Expertise needs a domain, concrete relation and task')
    if move['action']=='consult' and not expertise:
        raise ValueError('Consult requires a concrete expertise_request')


def team_config(domains):
    if not isinstance(domains,(list,tuple)) or not domains:
        raise ValueError('At least one researcher is required')
    rows=[]
    for item in domains:
        if not isinstance(item,(list,tuple)) or len(item)!=2:
            raise ValueError('Researcher entry is [id, domain]')
        rid,domain=item
        if not isinstance(rid,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,63}',rid) or not isinstance(domain,str) or not domain.strip():
            raise ValueError('Researcher needs a safe ID and a domain')
        if rid in [r[0] for r in rows]:raise ValueError('Duplicate researcher ID')
        rows.append((rid,domain))
    return rows


def run_rounds(run, domains, initial_history, call, learn, enlist, rounds=4, max_researchers=6):
    """Replay deterministic decisions from accepted outputs; never rewrite an old roster input."""
    if type(rounds) is not int or rounds<1:raise ValueError('hypothesis_rounds must be positive')
    domains=team_config(domains)
    if type(max_researchers) is not int or max_researchers<len(domains):raise ValueError('Invalid max_researchers')
    team=dict(domains);active=list(team);owner=active[0]
    history=list(initial_history);outputs=[];events=[];next_move=None;pending=None;requester=None
    for index in range(rounds):
        advisory=None;return_to=None
        if pending:
            key=hashlib.sha256((pending['domain']+'\0'+pending['relation']).encode()).hexdigest()[:12]
            expert='expert_'+key
            if expert not in team and len(team)>=max_researchers:
                advisory={'status':'capacity_reached','request':pending,'reason':'Preserve the task; use learning or the current team.'}
            else:
                if expert not in team:
                    team[expert]=pending['domain'];enlist(expert,pending['domain'])
                    if pending['mode']=='join':active.append(expert)
                elif pending['mode']=='join' and expert not in active:active.append(expert)
                owner=expert
                advisory={'status':'assigned','request':pending,'researcher':expert,'requested_by':requester}
                if pending['mode']=='consult':return_to=requester
            pending=None
        comparison=None
        if len(history)>=2:
            a,b=history[-2:]
            comparison={'before_stage':a[0],'after_stage':b[0],
                        'before_path':str(a[2]),'after_path':str(b[2])}
        packet={'active_researchers':active[:], 'researchers':[list(row) for row in team.items()],
                'progress_comparison':comparison,'requested_move':next_move,'expertise':advisory,
                'scope':'Semantic peer assessment guides work; convergence and unfinished hypotheses are valid.'}
        sid=f'09_develop_{index:03d}'
        path,result=call(sid,owner,ROUND_PROTOCOL,packet,outputs)
        validate_research_turn(result,packet)
        outputs.append(path);history.append((sid,owner,path))
        # Requested knowledge/metadata/computations return before the next peer develops the work.
        learning=learn(sid,owner,path,outputs[:])
        outputs.extend(learning['outputs'])
        decision_path=path
        for learned_sid,learned_owner,learned_path in learning['history']:
            learned_result=read(learned_path)
            validate_research_turn(learned_result,{**packet,'progress_comparison':None})
            history.append((learned_sid,learned_owner,learned_path))
            result=learned_result;decision_path=learned_path
        # Service-only tail replies must reach a researcher before honoring finish.
        pending_service=[str(p) for p in learning['outputs']
                         if p not in {row[2] for row in learning['history']}]
        next_move=result['next_research_move'];pending=result.get('expertise_request');requester=owner
        events.append({'stage':sid,'owner':owner,'source_result':str(path),
                       'decision_source':str(decision_path),'pending_service':pending_service,
                       'progress_review':read(path).get('progress_review'),'next_move':next_move,'expertise':advisory})
        write(Path(run)/'research_rounds/events.json',events)
        if next_move['action']=='finish' and not pending_service:break
        if next_move.get('owner') in active:owner=next_move['owner']
        elif return_to in active:owner=return_to
        else:owner=active[(active.index(owner)+1)%len(active)] if owner in active else active[0]
    write(Path(run)/'research_rounds/status.json',{'status':'finished' if next_move['action']=='finish' and not pending_service else 'turn_limit',
          'pending_service':pending_service,
          'pending_expertise':pending,'next_move':next_move,'active_researchers':active,'researchers':[list(row) for row in team.items()],
          'scope':'A turn limit is unfinished work, not scientific failure.'})
    return outputs
