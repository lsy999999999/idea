"""Resume this fixed-model experiment after an interrupted runner exits."""
from __future__ import annotations

import argparse
import fcntl
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parent
LOCK = ROOT / '.run.lock'
FAILURE = ROOT / 'LAST_FAILURE.json'
FINAL = ROOT / 'runs/hysteron/ours/evaluation/STATUS.json'
EVENTS = ROOT / 'SUPERVISOR_EVENTS.jsonl'
RUN = ROOT / 'runtime/run_with_resource_allowance.py'


def record(event: str, **details: object) -> None:
    row = {'at': datetime.now(timezone.utc).isoformat(), 'event': event, **details}
    with EVENTS.open('a') as file:
        file.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(json.dumps(row, ensure_ascii=False), flush=True)


def complete() -> bool:
    return FINAL.exists() and json.loads(FINAL.read_text()).get('status') == 'complete'


def wait_for_runner() -> None:
    while True:
        with LOCK.open('a') as file:
            try:
                fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(file, fcntl.LOCK_UN)
                return
            except BlockingIOError:
                time.sleep(15)


def expand_reply_allowance() -> bool:
    path = ROOT / 'model_config.json'
    cfg = json.loads(path.read_text())
    old = cfg.get('max_completion_tokens', 12000)
    new = min(393216, max(65536, old * 2))
    if new <= old:
        record('needs_review', error='Reply truncated at provider maximum output allowance')
        return False
    cfg['max_completion_tokens'] = new
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(json.dumps(cfg, ensure_ascii=False, indent=2))
    temporary.replace(path)
    record('reply_allowance_extended', before=old, after=new,
           reason='Preserve truncated response; new request avoids replaying that incomplete response')
    return True


def main(resume_existing_failure: bool = False, resume_now: bool = False) -> int:
    if (ROOT/'USER_STOP_REQUESTED.json').exists():
        record('stopped_by_user', resume_requires_new_user_instruction=True)
        return 0
    previous_failure = 0 if resume_existing_failure else (FAILURE.stat().st_mtime_ns if FAILURE.exists() else 0)
    record('waiting_for_current_runner')
    wait_for_runner()
    if resume_now and not complete():
        record('explicit_checkpoint_resume', entry=str(RUN))
        with (ROOT / 'experiment.log').open('a') as log:
            result = subprocess.run([sys.executable, str(RUN), '--case', 'hysteron'],
                                    stdout=log, stderr=subprocess.STDOUT, check=False)
        record('resumed_runner_exited', exit_code=result.returncode)
    consecutive_transport_failures = 0
    while not complete():
        if (ROOT/'USER_STOP_REQUESTED.json').exists():
            record('stopped_by_user', resume_requires_new_user_instruction=True)
            return 0
        if not FAILURE.exists() or FAILURE.stat().st_mtime_ns <= previous_failure:
            record('runner_stopped_without_new_failure_record')
            return 1
        previous_failure = FAILURE.stat().st_mtime_ns
        failure = json.loads(FAILURE.read_text())
        message = str(failure.get('error', '')).lower()
        if 'budget_exhausted' in message:
            consecutive_transport_failures = 0
            record('resuming_after_old_resource_limit')
        elif 'model response truncated' in message:
            if not expand_reply_allowance():
                return 1
            consecutive_transport_failures = 0
        elif any(term in message for term in ('connection error', 'timed out', '502', '503', '504')):
            consecutive_transport_failures += 1
            if consecutive_transport_failures > 8:
                record('repeated_transport_failure', error=failure.get('error'))
                return 1
            record('resuming_after_transport_failure', attempt=consecutive_transport_failures)
            time.sleep(min(30 * consecutive_transport_failures, 180))
        else:
            record('needs_review', error_type=failure.get('error_type'),
                   error=failure.get('error'))
            return 1

        with (ROOT / 'experiment.log').open('a') as log:
            result = subprocess.run([sys.executable, str(RUN), '--case', 'hysteron'],
                                    stdout=log, stderr=subprocess.STDOUT, check=False)
        record('resumed_runner_exited', exit_code=result.returncode)
        wait_for_runner()

    record('independent_evaluation_complete', path=str(FINAL))
    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resume-existing-failure', action='store_true')
    parser.add_argument('--resume-now', action='store_true')
    args = parser.parse_args()
    raise SystemExit(main(args.resume_existing_failure, args.resume_now))
