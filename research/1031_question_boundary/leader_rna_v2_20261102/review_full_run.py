"""Post-freeze organizer checks. No results are sent to frozen research roles."""
import json
import math
import broker as b

def main():
    run=b.ROOT/'runs/V2_full';s=b.state(run)
    assert b.verify(run)
    checks=[]
    for e in s['actor_events']:
        label=e['label'];inp=run/'inputs'/f'{label}.json';reply=run/'sealed_replies'/f'{label}.json'
        assert b.sha(inp)==e['input_sha256']
        assert b.sha(reply)==e['reply_sha256']==b.sha(run/'replies'/reply.name)
        assert b.read(run/'actor_finished'/f'{label}.json')['sha256']==e['reply_sha256']
        data=b.read(inp)
        assert not any(row['time_h']>24 for row in data['evidence']['initial_measurements.json'])
        assert 's44286-026-00454' not in json.dumps(data)
        checks.append(dict(reply=label,input_hash=True,sealed_hash=True,working_copy_unchanged=True))
    for t in s['tools']:
        assert t['result']['status'] in {'executed','returned'}
        if t['type']=='search':
            for source in t['result'].get('sources',[]):assert source['first_publication_date']<=b.CUTOFF
            assert b.sha(run/'tools'/t['id']/'raw.json')==t['result']['raw_sha256']
        if t['type']=='compute':
            assert (run/'tools'/t['id']/'submitted.py').read_text()==t['request']['code']
            assert b.sha(run/'tools'/t['id']/'submitted.py')==t['result']['code_sha256']
    out=dict(time=b.now(),freeze_valid=True,role_replies=checks,counters=s['counters'],all_tools_returned=True,
       clean_reply_sealing=True,hidden_observations_absent_from_inputs=True,
       operating_system_isolation=False,provider_trace_or_token_billing_available=False,
       semantic_validity='Not established by provenance checks; see PRIMARY_REVIEW_FULL.json')
    b.dump(b.ROOT/'FULL_RUN_PROVENANCE_AUDIT.json',out)

    # Check the observable equation AS SUBMITTED. These are review calculations,
    # not additional actor discoveries, repairs, fits or empirical measurements.
    observations=b.read(run/'visible/initial_measurements.json')
    B=sorted([r for r in observations if r['condition']=='B'],key=lambda r:r['time_h'])
    q0=B[0]['mean_empty_area_fraction'] if 'mean_empty_area_fraction' in B[0] else B[0]['mean_area_ratio']
    examples=[]
    for kd in [0.,.1,1.]:
        for initial in [0.,q0]:
            for name,r,T in [('fast',.2,5.),('slow',.05,20.)]:
                tau=5.;alpha=1.;xc=.5;steady=alpha*r*tau
                crossing=-tau*math.log(1-xc/steady) if steady>xc else None
                if crossing is not None and crossing>T:crossing=None
                decay_duration=T if crossing is None else crossing
                q_end=initial*math.exp(-kd*decay_duration)
                assert q_end<=initial
                examples.append(dict(schedule=name,kd_per_h=kd,q_initial=initial,q_end=q_end,crossing_h=crossing,no_growth=True))
    observed_ratio=B[-1].get('mean_empty_area_fraction',B[-1].get('mean_area_ratio'))/q0
    observable_check=dict(time=b.now(),status='submitted observable dynamics fail the growth check',
       submitted_equations=["x'=alpha*r-x/tau","Before t_star: q'=kn*max(x-xc,0)-kd*q","At/after first upward crossing t_star: q'=0"],
       proof='For continuous x starting below xc, t<t_star implies x<xc; hence source=0 and q=q0*exp(-kd*t). At/after t_star the stipulated freeze keeps q=q0*exp(-kd*t_star). Therefore q(t)=q0*exp(-kd*min(t,t_star)) and q(t)<=q0 for kd>=0. If q0=0, q remains zero. The submitted equations cannot generate cavity growth.',
       observed_B_initial=q0,observed_B_latest=B[-1],observed_B_growth_ratio=observed_ratio,
       scope='Deterministic intended mean/area mapping conflicts with observed growth. No calibrated observation noise or bias model was supplied; this is not a statistical hypothesis test.',
       load_calculation='C3 correctly computes x and crossing times, but explicitly excludes q; it does not check the growth-to-arrest bridge.',
       numerical_examples=examples,scientific_repair_applied=False,feedback_to_actors=False)
    b.dump(b.ROOT/'evaluation/OBSERVABLE_DYNAMICS_CHECK.json',observable_check)
    print(json.dumps(dict(provenance_pass=True,observable_dynamics_pass=False,observed_B_growth_ratio=observed_ratio,counters=s['counters']),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
