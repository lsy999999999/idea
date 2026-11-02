import json
DATA=json.loads('{"mobility_dev.json": [{"condition": "B", "n_tracks": 279, "median_final_squared_displacement_um2": 1.596246372681656, "median_n_frames": 98.0, "top_100_by_max_displacement_median_final_squared_displacement_um2": 123.04789558444844}, {"condition": "A", "n_tracks": 838, "median_final_squared_displacement_um2": 0.6357464296597586, "median_n_frames": 159.0, "top_100_by_max_displacement_median_final_squared_displacement_um2": 19.582408620947668}], "phase_measurements.json": [{"phase": "dilute", "tie_line_id": 0, "point_index_in_series": 0, "reference_RNA_ng_per_uL": 27.48, "variant_RNA_ng_per_uL": 0.0, "wt_error_lower_ng_per_uL": 9.0684, "wt_error_upper_ng_per_uL": 9.0684, "mut_error_lower_ng_per_uL": 0.0, "mut_error_upper_ng_per_uL": 0.0}, {"phase": "dilute", "tie_line_id": 1, "point_index_in_series": 1, "reference_RNA_ng_per_uL": 53.68, "variant_RNA_ng_per_uL": 0.53, "wt_error_lower_ng_per_uL": 17.7144, "wt_error_upper_ng_per_uL": 17.7144, "mut_error_lower_ng_per_uL": 0.1749, "mut_error_upper_ng_per_uL": 0.1749}, {"phase": "dilute", "tie_line_id": 2, "point_index_in_series": 2, "reference_RNA_ng_per_uL": 92.98, "variant_RNA_ng_per_uL": 115.63, "wt_error_lower_ng_per_uL": 30.6834, "wt_error_upper_ng_per_uL": 30.6834, "mut_error_lower_ng_per_uL": 38.1579, "mut_error_upper_ng_per_uL": 38.1579}, {"phase": "dense", "tie_line_id": 0, "point_index_in_series": 0, "reference_RNA_ng_per_uL": 12893.0, "variant_RNA_ng_per_uL": 0.0, "wt_error_lower_ng_per_uL": 6446.5, "wt_error_upper_ng_per_uL": 12893.0, "mut_error_lower_ng_per_uL": 0.0, "mut_error_upper_ng_per_uL": 0.0}, {"phase": "dense", "tie_line_id": 1, "point_index_in_series": 1, "reference_RNA_ng_per_uL": 12805.0, "variant_RNA_ng_per_uL": 4787.0, "wt_error_lower_ng_per_uL": 6402.5, "wt_error_upper_ng_per_uL": 12805.0, "mut_error_lower_ng_per_uL": 2393.5, "mut_error_upper_ng_per_uL": 4787.0}, {"phase": "dense", "tie_line_id": 2, "point_index_in_series": 2, "reference_RNA_ng_per_uL": 48826.0, "variant_RNA_ng_per_uL": 20352.0, "wt_error_lower_ng_per_uL": 24413.0, "wt_error_upper_ng_per_uL": 48826.0, "mut_error_lower_ng_per_uL": 10176.0, "mut_error_upper_ng_per_uL": 20352.0}], "initial_measurements.json": [{"condition": "A", "time_h": 0.0, "mean_empty_area_fraction": 0.0148724491091024, "sem_empty_area_fraction": 0.0002437652793328, "n_fields": 7, "n_objects": 3490}, {"condition": "A", "time_h": 4.0, "mean_empty_area_fraction": 0.0054389893768169, "sem_empty_area_fraction": 0.0004851399860374, "n_fields": 7, "n_objects": 1201}, {"condition": "A", "time_h": 8.0, "mean_empty_area_fraction": 0.0044390495790911, "sem_empty_area_fraction": 0.0004738057874311, "n_fields": 7, "n_objects": 998}, {"condition": "A", "time_h": 12.0, "mean_empty_area_fraction": 0.0040641907190291, "sem_empty_area_fraction": 0.0004533639169051, "n_fields": 7, "n_objects": 937}, {"condition": "A", "time_h": 24.0, "mean_empty_area_fraction": 0.0044581874447536, "sem_empty_area_fraction": 0.0005448059632589, "n_fields": 7, "n_objects": 859}, {"condition": "B", "time_h": 0.0, "mean_empty_area_fraction": 0.0138090880510916, "sem_empty_area_fraction": 0.0002264511197326, "n_fields": 7, "n_objects": 3158}, {"condition": "B", "time_h": 4.0, "mean_empty_area_fraction": 0.0159150610393171, "sem_empty_area_fraction": 0.0011019283039892, "n_fields": 7, "n_objects": 564}, {"condition": "B", "time_h": 8.0, "mean_empty_area_fraction": 0.0239331148418327, "sem_empty_area_fraction": 0.0016049805499992, "n_fields": 7, "n_objects": 545}, {"condition": "B", "time_h": 12.0, "mean_empty_area_fraction": 0.0402799733501556, "sem_empty_area_fraction": 0.0031537325464317, "n_fields": 7, "n_objects": 496}, {"condition": "B", "time_h": 24.0, "mean_empty_area_fraction": 0.0891834703945908, "sem_empty_area_fraction": 0.0078546202289423, "n_fields": 7, "n_objects": 349}], "sequence_measurements.json": {"reference_sequence": "GGGCATTCTAATACGACTCACTATAGGACCGTCAGAGGACACGGTTAAAAAGTCCTCATTCGTGGCCGCATCGCGAAAGCGGCCACGGGATTCTGTGCTGCACATTAGAGTCGCTGTATGACCCATCGCGAAAGGGTCGTACAGCGGCTCTAGTGTGCTCGCGTGGATCCCGACTGGCACCATCGCGAAAGGTGCCAGGTAACGAATGGATCCACGCGTCACTCGTAGCATTGTGCCTGTCTCCATCGCGAAAGGAGATAGGCACAGTGCTATGAGTGTGCACGGAATCC", "reference_read_fraction": 0.9466, "other_reads": [{"sequence": "GGGCATTCTAATACGACTCACTATAGGACCGTCAGAGGACACGGTTAAAAAGTCCTCATTCGTGGCCGCATCGCGAAAGCGGCCACGGGATTCTGTGCTGCACATTAGAGTCGCTGTATGACCCATCGCGAAAGGGTCGTACAGCGGCTCTAGTGTGCTCGCGTGGATCCCGACTGGCACCATCGCGAAAGGTGCCAGGTAACGAATGGATCCACGCGTCACTCGTAGCATTGTGCCTGTCTCCATCGCGAAAGGAGATAGGCACAGTGCTATGAGTGTGCACGGAATCCCGTGGCCGCTTTCGCGATGCGGCCACGAATGAGGACTTTTTAACCGTGTCCTCTGACGGTCCTATAGTGAGTCGTATTAGAATGCCCA", "length_nt": 378, "read_fraction": 0.0265}, {"sequence": "GGGCATTCTAATACGACTCACTATAGGACCGTCAGAGGACACGGTTAAAAAGTCCTCATTCGTGGCCGCATCGCGAAAGCGGCCACGGGATTCCGTGCACACTCATAGCACTGTGCCTATCTCCTTTCGCGATGGAGACAGGCACAATGCTACGAGTGACGCGTGGATCCATTCGTTACCTGGCACCTTTCGCGATGGTGCCAGT", "length_nt": 205, "read_fraction": 0.0125}, {"sequence": "GGGCATTCTAATACGACTCACTATAGGACCGTCAGAGGACACGGTTAAAAAGTCCTCATTCGTGGCCGCATCGCGAAAGCGGCCACGGGATTCTGTGCTGCACATTAGAGTCGCTGTATGACCCATCGCGAAAGGGTCGTACAGCGGCTCTAGTGTGCTCGCGTGGATCCCGACTGGCACCATCGCGAAAGGTGCCAGGTAACGAATGGATCCACGCGTCACTCGTAGCATTGTGCCTGTCTCCATCGCGAAAGGAGATAGGCACAGTGCTATGAGTGACGCGTGGATCCATTCGTTACCTGGCACCTTTCGCGATGGTGCCAGTCGGGATCCACGCGAGCACACTAGAGCCGCTGTACGACCCTTTCGCGATGGGTCATACAGCGACTCTAATGTGCAGCACAGAATCCCGTGGCCGCTTTCGCGATGCGGCCACGAATGAGGACTTTTTAACCGTGTCCTCTGACGGTCCTATAGTGAGTCGTATTAGAATGCCCA", "length_nt": 498, "read_fraction": 0.0075}, {"sequence": "GGGCATTCTAATACGACTCACTATAGGACCGTCAGAGGACACGGTTAAAAAGTCCTCATTCGTGGCCGCATCGCGAAAGCGGCCACGGGATTCTGTGCTGCACATTAGAGTCGCTGTATGACCCATCGCGAAAGGGTCGTACAGCGGCTCTAGTGTGCTCGCGTGGATCCCGACTGGCACCATCGCGAAAGGTGCCAGGTAACGAATGGATCCACGCGTCACTCGTAGCATTGTGCCTGTCTCCATCGCGAAAGGAGATAGGCACAGTGCTATGAGTGTGCACGGAATCCCGTGGCCGCTTTCGCGATGCGGCCACGGGATTCCGTGCACACTCATCACGCTGTGCCTATCTCCTTTCGCGATGGAGACAGGCACAATGCTACGAGTGACGCGTGGATCCATTCGTTACCTGGCACCTTTCGCGATGGTGCCAGTCGGGATCCACGCGAGCACACTAGAGCCGCTGTACGACCCTTTCGCGATGGGTCATACAGCGACTCTAATGTGCAGCACAGAATCCCGTGGCCGCTTTCGCGATGCGGCCACGAATGAGGACTTTTTAACCGTGTCCTCTGACGGTCCTATAGTGAGTCGTATTAGAATGCCCA", "length_nt": 608, "read_fraction": 0.0035}], "sample_metadata": {"condition": "B", "measurement": "DNA sequencing read fractions, not RNA concentrations", "provenance": "leader_rna_dev_v1_20261102/agent_visible/researcher_01.md:244", "original_public_note": "A is the reference template; the measured read fractions describe B."}}, "fraction_dev.json": [{"template_fraction": "M", "n_fields": 3, "median_field_mean_empty_fraction": 2.7853291144878946e-05, "field_mean_empty_fractions": [2.7853291144878946e-05, 0.00016496983408747812, 0.0]}, {"template_fraction": "M+L", "n_fields": 5, "median_field_mean_empty_fraction": 0.04445828743121418, "field_mean_empty_fractions": [0.042889071607366366, 0.06561580579976005, 0.057610926734964554, 0.029657181595508317, 0.04445828743121418]}, {"template_fraction": "M+S", "n_fields": 2, "median_field_mean_empty_fraction": 0.09412483585099253, "field_mean_empty_fractions": [0.05459724838435311, 0.13365242331763194]}]}')
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