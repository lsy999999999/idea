import json, math
AGES = [0.,4.,5.,8.,12.,20.,24.,36.,48.]
XC = 0.5
Q0 = [('zero',0.),('A_proxy',0.0148724491091024),('B_proxy',0.0138090880510916)]
def x_at(t,a,tau,r,dur):
    if t <= dur:
        return a*r*tau*(1.0-math.exp(-t/tau))
    xdur = a*r*tau*(1.0-math.exp(-dur/tau))
    return xdur*math.exp(-(t-dur)/tau)
def cross_time(a,tau,r,dur,x0=0.):
    if abs(x0-XC) < 1e-14:
        if a*r-x0/tau > 0.0: return 0.0
        return None
    if x0 > XC: return None
    xs = a*r*tau
    if xs <= XC: return None
    tc = -tau*math.log((xs-XC)/(xs-x0))
    if tc <= dur+1e-12: return tc
    return None
def q_value(t,q0,kd,tc):
    if tc is None: return q0*math.exp(-kd*t)
    if t < tc: return q0*math.exp(-kd*t)
    return q0*math.exp(-kd*tc)
cases = []
for a in (0.5,1.0,2.0):
    for tau in (1.0,5.0,20.0):
        for kd in (0.0,0.1):
            for name,r,dur in (('fast',0.2,5.0),('slow',0.05,20.0)):
                tc = cross_time(a,tau,r,dur)
                xs = [x_at(t,a,tau,r,dur) for t in AGES]
                qrows = []
                for label,q0 in Q0:
                    qs = [q_value(t,q0,kd,tc) for t in AGES]
                    qrows.append({'q0_case':label,'q_at_ages':qs,'q_at_shutoff':q_value(dur,q0,kd,tc),'q_at_crossing':None if tc is None else q_value(tc,q0,kd,tc)})
                cases.append({'alpha':a,'tau_h':tau,'kd_per_h':kd,'kn_per_h':0.1,'schedule':name,'r_per_h':r,'duration_h':dur,'dose':r*dur,'crossing_time_h':tc,'x_at_shutoff':x_at(dur,a,tau,r,dur),'x_at_ages':xs,'q_results':qrows})
near = []
for x0 in (XC-1e-6,XC,XC+1e-6):
    tc = cross_time(1.0,5.0,0.2,5.0,x0)
    if x0 > XC: status = 'initial-above-threshold switch convention undefined'
    elif x0 == XC and tc == 0.0: status = 'immediate crossing at equality; positive right derivative'
    elif tc is not None: status = 'upward crossing from below'
    else: status = 'no upward crossing'
    near.append({'x0':x0,'right_dxdt':0.2-x0/5.0,'crossing_time_h':tc,'status':status})
result = {'status':'exact conditional arithmetic, not fit or physical evidence','equations':'xdot=alpha*r-x/tau; qdot=kn*max(x-xc,0)-kd*q until first upward crossing, then qdot=0','ages_h':AGES,'xc':XC,'q0_cases':Q0,'cases':cases,'threshold_neighborhood':near,'observed':{'times_h':[0.,4.,8.,12.,24.],'A':[0.0148724491091024,0.0054389893768169,0.0044390495790911,0.0040641907190291,0.0044581874447536],'B':[0.0138090880510916,0.0159150610393171,0.0239331148418327,0.0402799733501556,0.0891834703945908]},'checks':{'equal_dose':all(abs(c['dose']-1.0)<1e-12 for c in cases),'no_cross_from_below':'alpha*r*tau<=xc; equality is asymptotic','q_from_below':'q has zero source until crossing, then freezes; absent crossing q=q0*exp(-kd*t)','post_shutoff_x':'x relaxes exponentially after production stops','dimensions':'alpha*r and x/tau h^-1; kn,kd h^-1; q dimensionless','bounds':'finite x for finite piecewise-constant r and tau>0; q finite over finite time, no imposed q<=1','initial_above':'undefined by first-upward-crossing wording','trend':'from-below q cannot rise, unlike observed B; no fitting'}}
print(json.dumps(result,sort_keys=True))