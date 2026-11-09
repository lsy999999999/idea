"""Explicit budget amendment around the unchanged frozen inquiry implementation."""
import copy
import fcntl
import shutil
from fish_inquiry import InquiryPilot, load, save
from fish_materials import CASE, prepare, digest

prepare()
with (CASE/'.run.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    pilot=InquiryPilot(run_id='inquiry_v2_live_20261106_002',timeout=240)
    amendment=load(pilot.run/'recovery/BOUNDED_CONTINUATION_AMENDMENT.json')
    amendment.update(service_budgets={'01_initial_*':3,'r1_exchange_0':2,'all_other_new_service_boundaries':1},
                     replay_policy='Retain every completed initial-learning reply and both completed r1_exchange_0 learning replies. New service boundaries use one read/response hop plus the existing final pending-request delivery.',
                     bounded_entry_sha256=digest(__file__))
    destination=pilot.run/'services/controller_only/budget_amendment.json'
    if destination.exists():
        assert load(destination)==amendment
    else:
        save(destination,amendment)
        shutil.copy2(__file__,destination.parent/'bounded_live_finish_20261106.py')
    pilot.config=copy.deepcopy(pilot.config)
    pilot.config['max_rounds']=1
    original_service=pilot.service
    def service(sid,rid,answer):
        previous=pilot.config['max_request_hops']
        pilot.config['max_request_hops']=3 if sid.startswith('01_initial_') else 2 if sid=='r1_exchange_0' else 1
        try:
            return original_service(sid,rid,answer)
        finally:
            pilot.config['max_request_hops']=previous
    pilot.service=service
    pilot.execute()
