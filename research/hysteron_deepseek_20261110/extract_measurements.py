"""Read-only empirical-cell extraction. Run with bundled Python/openpyxl."""
from pathlib import Path
import csv,json,hashlib
import openpyxl
R=Path(__file__).resolve().parent
src=R.parent/'scenario_selection_20261110/controller_only/hysteron_originals/Source Data.xlsx'
w=openpyxl.load_workbook(src,data_only=True,read_only=True)
rows=[];provenance=[]
def add(record,cells):
 record={'record_id':len(rows)+1,**record};rows.append(record)
 provenance.append({'record_id':record['record_id'],'sheet':cells[0],'cells':cells[1:]})
for j,spring in [(1,'S046'),(3,'S019'),(5,'S007')]:
 s=w['Fig. 1B']
 for i in range(3,s.max_row+1):
  x,f=s.cell(i,j).value,s.cell(i,j+1).value
  if isinstance(x,(int,float)) and isinstance(f,(int,float)):add(dict(record_type='calibration',configuration_id='calibration',spring_id=spring,x_m=x,force_N=f),['Fig.1B',s.cell(i,j).coordinate,s.cell(i,j+1).coordinate])
s=w['Fig. 2A']
for q,(rotor,direction,other) in enumerate([(1,'up',-1),(1,'up',1),(1,'down',-1),(1,'down',1),(2,'up',-1),(2,'up',1),(2,'down',-1),(2,'down',1)]):
 for i in range(4,8):
  j=2*q+1
  add(dict(record_type='threshold',configuration_id='pair_A',rotor_i=rotor,direction=direction,other_state=other,mount_l_cm=s.cell(i,j).value,drive_gamma_cm=s.cell(i,j+1).value),['Fig.2A',s.cell(i,j).coordinate,s.cell(i,j+1).coordinate])
s=w['Fig. 3B']
for i,rotor,direction,other in [(3,1,'down',-1),(4,1,'up',-1),(5,1,'down',1),(6,1,'up',1),(8,2,'down',-1),(9,2,'down',1),(10,2,'up',-1),(11,2,'up',1)]:
 add(dict(record_type='threshold',configuration_id='pair_B',rotor_i=rotor,direction=direction,other_state=other,mount_l_cm=4.7,drive_gamma_cm=s.cell(i,2).value),['Fig.3B',f'A{i}',f'B{i}'])
s=w['Fig. 5D']
for i in range(2,18):
 state=s.cell(i,1).value
 state=state.replace('−','-')
 assert len(state)==4 and set(state)<={'-','+'}
 add(dict(record_type='state_event',configuration_id='network_C',event_index=i-1,state_string=state,drive_gamma_cm=s.cell(i,2).value,**{f's{j+1}':1 if x=='+' else -1 for j,x in enumerate(state)}),['Fig.5D',f'A{i}',f'B{i}'])
folder=R/'cases/hysteron';folder.mkdir(parents=True,exist_ok=True)
cols=list(dict.fromkeys(k for row in rows for k in row))
with (folder/'measurements.csv').open('w',newline='') as f:
 out=csv.DictWriter(f,fieldnames=cols);out.writeheader();out.writerows(rows)
def write(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2))
counts={k:sum(x['record_type']==k for x in rows) for k in ['calibration','threshold','state_event']}
dossier={'data_file':'measurements.csv','rows':len(rows),'statistics':{'record_counts':counts},'preview':rows,'data_dictionary':{
'record_id':'Unique row identifier; not an independent replicate.','record_type':'calibration, threshold, or state_event. Unused columns are missing, not zero.','configuration_id':'pair_A and pair_B are distinct two-rotor devices; network_C is a separate four-rotor device. No sharing of fitted pair parameters is warranted.','spring_id':'Calibration sample nominal stiffness S046=0.46, S019=0.19, S007=0.07 N/cm; samples are not exact identities of every installed spring.','x_m':'Measured spring length in metres.','force_N':'Measured tensile spring force in newtons.','rotor_i':'Switching rotor index, 1 or 2.','direction':'up: switching to + during increasing drive; down: switching to - during decreasing drive.','other_state':'State (-1 or +1) of the other rotor held fixed during the threshold measurement.','mount_l_cm':'Distance of coupling spring attachment from the rotor pivot, cm.','drive_gamma_cm':'Measured horizontal drive rod displacement, cm; threshold uncertainty ±0.1 cm for the two-rotor tables.','event_index':'Ordered observed state events under back-and-forth constant-amplitude drive. Not a time variable.','state_string':'Four rotor states in rotor order. Consecutive equal drive values preserve event order; time between events is unresolved.','s1':'State of rotor 1: -1 or +1.','s2':'State of rotor 2.','s3':'State of rotor 3.','s4':'State of rotor 4.'},
'apparatus':{'common':'Rigid bars rotate freely about central pivots between hard angular stops. Theta=0 points along y. Each driving spring attaches at distance L from the pivot and to a horizontally translating rod. Additional spring pairs couple rotors. Quasistatic drive is rod displacement gamma. Springs were calibrated by pulling a known mass resting on an electronic balance.','pair_A':{'connection':'parallel coupling springs','y_cm':9.4,'L_cm':6.3,'w_cm':15.2,'x_mount_offsets_cm':[0,-1.9],'stop_angles_degrees':[[-36.6,36.7],[-9.8,11.2]],'driving_k_N_per_cm':[0.19,0.19],'driving_rest_lengths_cm':[3.9,4.2],'coupling_k_N_per_cm':0.07,'coupling_rest_lengths_cm':[2.4,2.6]},'pair_B':{'connection':'crossed coupling springs','y_cm':9.4,'L_cm':6.3,'w_cm':15.2,'x_mount_offsets_cm':[-8.1,-16.4],'stop_angles_degrees':[[-18.3,18.3],[-38.8,38.8]],'all_spring_k_N_per_cm':0.19,'all_spring_rest_length_cm':4.1,'mount_l_cm':4.7},'network_C':'Four coupled rotors; some coupling attachments have unequal mounting distances. A spring pair between rotors 1 and 3 is extended with steel wire. Numerical stop angles, attachment coordinates, full connectivity and drive reversal values are not contained in the supplied numeric table; request supported method details if needed, otherwise keep them unknown.'},
'protocol':{'thresholds':'Hold the other rotor fixed at its - or + stop; move the common drive quasistatically until the free rotor switches. Repeat for both directions. Pair A varies coupling attachment distance with all other geometry fixed.','events':'State sequence and drive positions were measured during constant-amplitude cyclic driving. The source export has 16 ordered events and no timestamps or reversal rows. Do not infer reversal positions from event extrema.','scope':'Published figure-source experimental measurements, not complete acquisition streams. No independent repetitions or error bars for calibration/events are provided. Author model columns, calculated state graphs, equations and interpretation are excluded. The four-rotor apparatus was adjusted iteratively before recording; it is not an unselected random sample.','geometry_notation':'L is driving attachment distance; w is pivot spacing; ell is coupling attachment distance. y and x_mount_offsets are reported mounting coordinates; exact reference orientation may be requested through case definitions. They are not additional measurements.'}}
write(folder/'dossier.json',dossier)
write(R/'runtime/ours_source/learning_lab/scenarios/hysteron.md',dossier)
write(R/'controller_only/hysteron/CELL_PROVENANCE.json',{'source':str(src),'sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'records':provenance,'omitted':['Fig.2A Q:AF model','Fig.3B C model','Fig.S1B','Fig.S3A','Fig.S3B'],'counts':counts})
sha=hashlib.sha256((folder/'measurements.csv').read_bytes()).hexdigest()
p=R/'runtime/ours_source/historical_inquiry/case_access.py'
t=p.read_text().replace("CASE_RULES = MappingProxyType({", "CASE_RULES = MappingProxyType({\n    'hysteron': MappingProxyType({\n        'before': '2024-09-12',\n        'dois': ('10.1038/s41467-026-70913-2','10.6084/m9.figshare.28856705','10.6084/m9.figshare.28856705.v1','10.48550/arXiv.2409.07726'),\n        'titles': ('Mechanical hysterons with tunable interactions of general sign',),\n        'aliases': ('PMC13070039','2409.07726','figshare.com/articles/dataset/28856705','Kinematic-model.nb','t-graph-maker.ipynb'),\n        'csv_sha256': '"+sha+"',\n    }),")
t=t.replace("'preview', 'data_file')","'preview', 'data_file', 'apparatus', 'protocol')")
t=t.replace('Separate source scans are measurements, not independent repeated preparations.','Supplied figure-source rows are measurements or ordered events, not independent repeated preparations.')
p.write_text(t)
print(json.dumps({'rows':len(rows),'counts':counts,'csv_sha256':sha}))
