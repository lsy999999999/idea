import json, math
AGES=[0.,4.,5.,8.,12.,20.,24.,36.,48.]
XC=.5
Q0=[('zero',0.),('A_proxy',.0148724491091024),('B_proxy',.0138090880510916)]
def x_at(t,a,tau,r,dur,x0=0.):
    if t<=dur: return x0*math.exp(-t/tau)+a*r*tau*(1-math.exp(-t/tau))
    xdur=x0*math.exp(-dur/tau)+a*r*tau*(1-math.exp(-dur/tau))
    return xdur*math.exp(-(t-dur)/tau)
def cross(a,tau,r,dur,x0=0.):
    if abs(x0-XC)<1e-14: return 0. if a*r-x0/tau>0. else None
    if x0>XC: return None
    xs=a*r*tau
    if xs<=XC: return None
    tc=-tau*math.log((xs-XC)/(xs-x0))
    return tc if tc<=dur+1e-12 else None
def q_at(t,q0,kd,tc):
    return q0*math.exp(-kd*min(t,tc)) if tc is not None else q0*math.exp(-kd*t)
rows=[]
for a in (.5,1.,2.):
 for tau in (1.,5.,20.):
  for kd in (0.,.1):
   for name,r,dur in (('fast',.2,5.),('slow',.05,20.)):
    tc=cross(a,tau,r,dur,0.)
    rows.append({'alpha':a,'tau_h':tau,'xc':XC,'kn_per_h':.1,'kd_per_h':kd,'schedule':name,'r_per_h':r,'stop_h':dur,'dose':r*dur,'crossing_time_h':tc,'x_at_ages':[round(x_at(t,a,tau,r,dur),12) for t in AGES],'q_by_q0_at_ages':{label:[round(q_at(t,q0,kd,tc),12) for t in AGES] for label,q0 in Q0},'q_at_shutoff_by_q0':{label:round(q_at(dur,q0,kd,tc),12) for label,q0 in Q0},'x_at_shutoff':round(x_at(dur,a,tau,r,dur),12),'q_at_crossing_by_q0':None if tc is None else {label:round(q_at(tc,q0,kd,tc),12) for label,q0 in Q0}})
near=[]
for x0 in (XC-1e-6,XC,XC+1e-6):
 tc=cross(1.,5.,.2,5.,x0)
 near.append({'x0':x0,'right_dxdt_at_zero':.2-x0/5.,'crossing_time_h':tc,'interpretation':'upward crossing from below' if x0<XC and tc is not None else ('immediate crossing at equality because dxdt>0' if x0==XC and tc==0. else ('underdetermined initial-above-threshold switch' if x0>XC else 'no upward crossing'))})
print(json.dumps({'status':'exact conditional arithmetic; not fit or empirical evidence','equations':'xdot=alpha*r-x/tau; pre-crossing qdot=kn*max(x-xc,0)-kd*q; qdot=0 permanently after first upward crossing','ages_h':AGES,'initial_x':0.,'q0_cases':Q0,'parameters':{'xc':XC,'alpha':[.5,1.,2.],'tau_h':[1.,5.,20.],'kn_per_h':.1,'kd_per_h':[0.,.1]},'schedules':[{'name':'fast','r_per_h':.2,'duration_h':5.,'integrated_r':1.},{'name':'slow','r_per_h':.05,'duration_h':20.,'integrated_r':1.}],'cases':rows,'threshold_neighborhood':near,'observed_means_0_to_24h':{'A':[.0148724491091024,.0054389893768169,.0044390495790911,.0040641907190291,.0044581874447536],'B':[.0138090880510916,.0159150610393171,.0239331148418327,.0402799733501556,.0891834703945908],'times_h':[0.,4.,8.,12.,24.]},'named_checks':{'all_doses_equal_one':all(abs(z['dose']-1.)<1e-12 for z in rows),'x_exact_solution':'constant-rate solution then exponential relaxation after production stop','q_exact_solution_from_below':'source is zero until crossing; q=q0 exp(-kd*t) until crossing then q is constant; without crossing q=q0 exp(-kd*t)','post_crossing_q_growth':'none for a trajectory from x0<=xc under literal freeze switch','no_finite_upward_cross_from_below':'alpha*r*tau<=xc; equality approaches xc asymptotically','dimensions':'alpha*r and x/tau are h^-1; kn,kd h^-1; q dimensionless and qdot h^-1','bounds':'x finite for finite piecewise-constant r,tau>0; q finite over finite intervals, with no imposed q<=1 bound','initial_x_above_xc':'original first-upward-crossing rule does not define whether already arrested; not silently resolved','trend_comparison':'model q from below cannot rise, unlike observed B mean from .013809 to .089183 over 0-24 h; A decreases .014872 to .004458. No fitting'},sort_keys=True))