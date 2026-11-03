"""Combine preserved masked review with explicitly documented organizer findings."""
import copy
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
import pilot as p
BASE=p.ROOT;REC=BASE/'format_recovery'

summary=p.read(REC/'MODEL_REVIEW_SUMMARY.json')
corrected=copy.deepcopy(summary)
changes=[]
for row in corrected['rows']:
    for record in row['final']:
        if row['case']=='wine' and row['arm']=='C' and record['round']==2:
            changes.append({'case':'wine','arm':'C','round':2,'review_id':record['id'],'original_usable_final':record['usable_final'],'corrected_usable_final':False,'original_material_acceptance_error':record['material_acceptance_error'],'corrected_material_acceptance_error':True,'reason':'Design matrix interaction is column 2, but fit_ord returns beta[3], the fixed_acidity coefficient. All bootstrap intervals inherit the same wrong index. Index-only organizer reexecution gives white interaction 0.02747, interval [-0.02310,0.06652], contradicting the claimed supported interaction based on 0.19409, [0.05467,0.30788].','evidence':'organizer_diagnostics/wine_C_r2_coefficient/RESULT.json','proposal_quality_preserved':True})
            record['usable_final']=False;record['material_acceptance_error']=True;record['error_type']='wrong_coefficient_semantic_binding'
            record['organizer_reason']=changes[-1]['reason']
    families=set();curve=[]
    for r in row['final']:
        if r['usable_final']:families.add(r['family_id'])
        curve.append(len(families))
    row['final_usable']=sum(r['usable_final'] for r in row['final'])
    row['final_unique_families']=len(families);row['cumulative_unique']=curve
    row['material_errors']=sum(r['material_acceptance_error'] for r in row['final'])

notes=[
 {'case':'wine','arm':'C','round':1,'severity':'evidence_label_inconsistency','decision':'Retain proposal-quality pass; do not count a second material false-effect assertion because prose explicitly states both intervals include zero and direction is not established. Record sensitivity: excluding this label mismatch would reduce C wine from 2 to 1 usable families.','reason':'evidence_level=observational_support conflicts with explicit inconclusive prose.'},
 {'case':'shopping','arm':'C','round':3,'severity':'tied_predictor_binning','decision':'Keep proposal-quality and computed-feasibility judgement; flag misleading fine-bin shape. Four highest rank bins have exactly identical share=1; their rate differences are not a response curve across share. Tie-preserving bins still show a nonmonotonic marginal pattern, so this diagnostic does not invalidate the proposed nonlinear test.','evidence':'organizer_diagnostics/shopping_C_r3_ties.json'},
 {'case':'wine','arm':'A','round':2,'severity':'evaluation_boundary','decision':'Keep masked reviewer strict exclusion in main table, report sensitivity accepting this as a useful conditional-fit proposal raises A wine from 0 to 1, without changing C vs B conclusion.','reason':'Final primary forecast is in-sample improvement of nested models; likelihood-ratio evidence is nontrivial under assumptions, but the literal improvement forecast is automatic at an optimum. The report must retain both facts.'},
 {'case':'wine','arm':'B','round':2,'severity':'sampling_limit','decision':'Retain scoped descriptive finding; do not claim rating reliability or independent pair replication.','reason':'Nearest-neighbor pairs share observations and may include duplicate chemistry rows; reference is a descriptive within-stratum permutation, not external validation.'}
]
p.write(BASE/'ORGANIZER_AUDIT.json',{'time':p.now(),'masked_review_original':str(REC/'MODEL_REVIEW_SUMMARY.json'),'overrides':changes,'additional_notes':notes,'original_model_reviews_unchanged':True,'organizer_not_blind':True})
corrected['source']='Masked same-model review plus nonblind organizer semantic and numerical audit; development pilot only'
p.write(BASE/'FINAL_SUMMARY.json',corrected)
go=all(next(r for r in corrected['rows'] if r['case']==case and r['arm']=='C')['final_unique_families']>=next(r for r in corrected['rows'] if r['case']==case and r['arm']=='B')['final_unique_families']+1 for case in p.CASES)
go=go and sum(r['material_errors'] for r in corrected['rows'] if r['arm']=='C')<=sum(r['material_errors'] for r in corrected['rows'] if r['arm']=='B')
p.write(BASE/'GO_NO_GO.json',{'time':p.now(),'advance_C':go,'predeclared_rule':'C >= B+1 usable final family in each task and no more material acceptance errors','result':{'wine':{'B':3,'C':2},'shopping':{'B':3,'C':3},'material_errors':{'B':0,'C':1}},'meaning':'Do not expand C based on this pilot. This is not a statistically powered superiority/noninferiority result or an originality judgement.'})
print(json.dumps([{k:r[k] for k in ['case','arm','final_usable','final_unique_families','cumulative_unique','material_errors']} for r in corrected['rows']],ensure_ascii=False,indent=2))
