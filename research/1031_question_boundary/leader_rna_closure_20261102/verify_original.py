"""Organizer's post-submission ODE check, never supplied to research roles.

Integrates the stipulated original equations with event handling independently of
the role-authored closed-form code. This is verification, not model revision or
an additional agent discovery result.
"""
import json
from pathlib import Path
import numpy as np
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parent
RUN=ROOT/'runs/closure'

def integrate(case,ages,q0,xc):
    alpha,tau,rate,stop=case['alpha'],case['tau_h'],case['r_per_h'],case['duration_h']
    kd,kn=case['kd_per_h'],case['kn_per_h']
    y=np.array([0.]+q0);current=0.;frozen=False;crossing=None;rows=[]
    targets=sorted(set(ages+[stop]))
    for target in targets:
        if target>current:
            r=rate if current<stop else 0.
            def rhs(t,z):
                dq=np.zeros(len(q0)) if frozen else kn*max(z[0]-xc,0.)-kd*z[1:]
                return np.r_[alpha*r-z[0]/tau,dq]
            def event(t,z):return z[0]-xc
            event.direction=1;event.terminal=True
            sol=solve_ivp(rhs,(current,target),y,rtol=1e-11,atol=1e-13,max_step=.25,events=None if frozen else event)
            assert sol.success
            if not frozen and sol.t_events[0].size:
                crossing=float(sol.t_events[0][0]);current=crossing;y=sol.y_events[0][0];frozen=True
                if current<target:
                    sol=solve_ivp(rhs,(current,target),y,rtol=1e-11,atol=1e-13,max_step=.25)
                    assert sol.success
                    y=sol.y[:,-1]
            else:y=sol.y[:,-1]
            current=target
        if target in ages:rows.append(y.copy())
    return np.array(rows),crossing

def main():
    result=json.loads((RUN/'tools/C6/execution.json').read_text())
    assert result['status']=='executed' and result['returncode']==0
    data=json.loads(result['stdout']);ages=data['ages_h'];q0=[pair[1] for pair in data['q0_cases']]
    checks=[];max_x=0.;max_q=0.;max_cross=0.
    for case in data['cases']:
        numeric,tc=integrate(case,ages,q0,data['xc'])
        dx=float(np.max(np.abs(numeric[:,0]-np.array(case['x_at_ages']))))
        expected_q=np.array([q['q_at_ages'] for q in case['q_results']]).T
        dq=float(np.max(np.abs(numeric[:,1:]-expected_q)))
        assert (tc is None)==(case['crossing_time_h'] is None)
        dt=0. if tc is None else abs(tc-case['crossing_time_h'])
        max_x=max(max_x,dx);max_q=max(max_q,dq);max_cross=max(max_cross,dt)
        assert dx<1e-8 and dq<1e-8 and dt<1e-7
        assert np.all(expected_q>=0) and np.all(expected_q<=np.array(q0)+1e-12)
        assert np.all(np.diff(expected_q,axis=0)<=1e-12)
        assert np.all(expected_q[:,0]==0.)
        checks.append(dict(alpha=case['alpha'],tau_h=case['tau_h'],kd_per_h=case['kd_per_h'],schedule=case['schedule'],max_abs_x_error=dx,max_abs_q_error=dq,crossing_error_h=dt))
    anchors=[c for c in data['cases'] if c['alpha']==1. and c['tau_h']==5. and c['kd_per_h']==.1]
    rows=[]
    for case in anchors:
        q=next(q for q in case['q_results'] if q['q0_case']=='B_proxy')
        i=ages.index(24.)
        rows.append(dict(schedule=case['schedule'],q0=q0[2],crossing_time_h=case['crossing_time_h'],x_at_24h=case['x_at_ages'][i],q_at_24h=q['q_at_ages'][i],q_at_48h=q['q_at_ages'][ages.index(48.)]))
    report=dict(passed=True,scope='Organizer numerical verification after C6 submission; not role input or model repair',method='Independent adaptive ODE integration of original source/loss equations with permanent freeze event and production shutoff',parameter_schedule_cases=len(checks),q_trajectories=len(checks)*len(q0),sample_ages_h=ages,max_abs_x_error=max_x,max_abs_q_error=max_q,max_crossing_error_h=max_cross,all_q_nonnegative_nonincreasing_and_leq_initial=True,all_zero_initial_q_remain_zero=True,anchor_common_age_comparison=rows,observed_B_initial=data['observed']['B'][0],observed_B_24h=data['observed']['B'][-1],case_checks=checks,limitations=['only declared x0=0 principal trajectories; above-threshold initial arrest history remains unspecified','no empirical fit, noise model, causal identification or new observation'])
    (ROOT/'NUMERICAL_VERIFICATION.json').write_text(json.dumps(report,indent=2,allow_nan=False))
    print(json.dumps({k:v for k,v in report.items() if k not in {'case_checks','limitations'}},indent=2))

if __name__=='__main__':main()
