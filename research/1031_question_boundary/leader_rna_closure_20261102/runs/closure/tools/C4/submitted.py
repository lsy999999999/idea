import json, math
from scipy.integrate import solve_ivp
AGES=[0.,4.,5.,8.,12.,20.,24.,36.,48.]
XC=.5

def run(alpha,tau,kn,kd,r,duration,q0,x0=0.,max_step=.002):
    t=0.; y=[float(x0),float(q0)]; arrested=False; crossing=None; rows=[]; shut=None; cross_near=None
    if abs(y[0]-XC)<1e-12 and alpha*r-y[0]/tau>0:
        arrested=True; crossing={'time_h':0.,'x':y[0],'q':y[1]}; cross_near={'before':None,'at':dict(crossing),'after_1e-4h':dict(crossing)}
    boundaries=sorted(set(AGES+[duration]))
    for target in boundaries:
        if target<t-1e-12: continue
        if abs(target-t)<1e-12:
            if target in AGES: rows.append({'time_h':target,'x':y[0],'q':y[1],'arrested':arrested})
            if abs(target-duration)<1e-12: shut={'time_h':duration,'x':y[0],'q':y[1],'arrested':arrested}
            continue
        # Split any interval at the production stop, including when it lies before target.
        cuts=[z for z in (t,duration,target) if t-1e-12<=z<=target+1e-12]
        cuts=sorted(set(cuts+[target]))
        for end in cuts[1:]:
            rate=r if (t < duration-1e-12) else 0.
            if end<=t+1e-12: continue
            def rhs(tt,yy):
                xx,qq=yy
                dq=0. if arrested else kn*max(xx-XC,0.)-kd*qq
                return [alpha*rate-xx/tau,dq]
            def event(tt,yy): return yy[0]-XC
            event.direction=1; event.terminal=True
            sol=solve_ivp(rhs,(t,end),y,rtol=1e-10,atol=1e-12,max_step=max_step,dense_output=True,events=None if arrested else event)
            if not sol.success: raise RuntimeError(sol.message)
            if not arrested and len(sol.t_events[0]):
                tc=float(sol.t_events[0][0]); yc=[float(sol.y_events[0][0][0]),float(sol.y_events[0][0][1])]
                crossing={'time_h':tc,'x':yc[0],'q':yc[1]}
                eps=1e-4
                before=None
                if tc-eps>=t-1e-12:
                    vb=sol.sol(max(t,tc-eps)); before={'time_h':max(t,tc-eps),'x':float(vb[0]),'q':float(vb[1])}
                cross_near={'before':before,'at':dict(crossing),'after_1e-4h':{'time_h':tc+eps,'x':XC*math.exp(-eps/tau)+alpha*rate*tau*(1-math.exp(-eps/tau)),'q':yc[1]}}
                arrested=True; y=yc; t=tc
                sol2=solve_ivp(rhs,(t,end),y,rtol=1e-10,atol=1e-12,max_step=max_step)
                if not sol2.success: raise RuntimeError(sol2.message)
                y=[float(sol2.y[0,-1]),float(sol2.y[1,-1])]; t=end
            else:
                y=[float(sol.y[0,-1]),float(sol.y[1,-1])]; t=end
        if abs(target-duration)<1e-10: shut={'time_h':duration,'x':y[0],'q':y[1],'arrested':arrested}
        if target in AGES: rows.append({'time_h':target,'x':y[0],'q':y[1],'arrested':arrested})
    return {'crossing':crossing,'crossing_neighborhood':cross_near,'shutoff':shut,'observations':rows,'q_after_crossing_frozen':arrested,'x_final':y[0],'q_final':y[1]}

results=[]
for tau in (1.,5.,20.):
 for alpha in (.5,1.,2.):
  for kn,kd in ((.1,0.),(.1,.1)):
   for schedule,r,dur in (('fast',.2,5.),('slow',.05,20.)):
    for qname,q0 in (('zero',0.),('A_proxy',.0148724491091024),('B_proxy',.0138090880510916)):
     results.append({'alpha':alpha,'tau_h':tau,'kn_per_h':kn,'kd_per_h':kd,'schedule':schedule,'r_per_h':r,'stop_h':dur,'dose':r*dur,'q0_case':qname,'result':run(alpha,tau,kn,kd,r,dur,q0)})
near=[]
for x0 in (XC-1e-6,XC,XC+1e-6):
 near.append({'x0':x0,'q0':0.,'case':run(1.,5.,.1,.1,.2,5.,0.,x0=x0)})
# Repeat representative fast/slow anchor cases with half maximum step for convergence audit.
conv=[]
for schedule,r,dur in (('fast',.2,5.),('slow',.05,20.)):
 a=run(1.,5.,.1,.1,r,dur,0.,max_step=.002); b=run(1.,5.,.1,.1,r,dur,0.,max_step=.001)
 da=max(abs(u[k]-v[k]) for u,v in zip(a['observations'],b['observations']) for k in ('x','q'))
 conv.append({'schedule':schedule,'coarse_max_step_h':.002,'fine_max_step_h':.001,'max_abs_difference_common_age_xq':da,'crossing_time_coarse_h':None if a['crossing'] is None else a['crossing']['time_h'],'crossing_time_fine_h':None if b['crossing'] is None else b['crossing']['time_h']})
obs={'times_h':[0.,4.,8.,12.,24.],'A':[.0148724491091024,.0054389893768169,.0044390495790911,.0040641907190291,.0044581874447536],'B':[.0138090880510916,.0159150610393171,.0239331148418327,.0402799733501556,.0891834703945908]}
print(json.dumps({'status':'conditional literal-equation computation; not fit or physical evidence','equations':'xdot=alpha*r-x/tau; before first upward crossing qdot=kn*max(x-xc,0)-kd*q; after crossing qdot=0 permanently','assumptions':{'ages_h':AGES,'xc':XC,'initial_x':0.,'q0_observed_values_are_provisional_area_proxies':True,'kn_kd_illustrations':[{'kn_per_h':.1,'kd_per_h':0.},{'kn_per_h':.1,'kd_per_h':.1}],'equal_dose':1.,'crossing_equality':'initial x==xc with positive right-hand dx/dt is immediate crossing; otherwise upward event only','solver':{'rtol':1e-10,'atol':1e-12,'max_step_h':.002,'convergence_repeat_max_step_h':.001}},'results':results,'threshold_neighborhood_initial_x':near,'convergence':conv,'observed_direction':obs,'named_checks':{'all_doses_equal_one':all(abs(z['dose']-1.)<1e-12 for z in results),'dimensions':'alpha*r and x/tau have units h^-1; kn,kd h^-1; qdot h^-1 for dimensionless q','x_bounded':'for finite piecewise-constant nonnegative r and tau>0, x is bounded and relaxes exponentially after shutoff','q_bounded':'for finite inputs q is bounded on finite time; before arrest loss is nonnegative decay and after arrest q is fixed. No imposed q<=1 bound.','no_cross_from_below':'constant rate alpha*r*tau<=xc cannot reach threshold from below; equality is asymptotic unless initialized at threshold with positive derivative','post_shutoff':'x(t)=x(T)*exp(-(t-T)/tau); q decays with kd before arrest, and is frozen after arrest','q_nonnegative':'nonnegative q0,kn,kd preserve q>=0','public_trend_check':'compare computed conditional behavior with A decreasing and B increasing from 0 to 24 h; no parameter fitting'}},sort_keys=True))