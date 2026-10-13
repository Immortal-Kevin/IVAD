import threading, time
from ivad_app.jobs.manager import JobService, ResourceGate
from ivad_app.storage.models import JobRecord
from ivad_app.core.contracts import utc_now, AppError
from ivad_app.services.logging_service import redact
import pytest

def wait_state(service, job, states):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        state = service.get(job)['state']
        if state in states: return state
        time.sleep(0.005)
    raise AssertionError(service.get(job))

def test_queue_success_failure_and_continues(services):
    first = services.jobs.submit()
    failure = services.jobs.submit('diagnostic_failure')
    last = services.jobs.submit()
    assert services.jobs.get(last)['state'] == 'QUEUED'
    assert wait_state(services.jobs, first, {'SUCCEEDED'}) == 'SUCCEEDED'
    assert wait_state(services.jobs, failure, {'FAILED'}) == 'FAILED'
    assert wait_state(services.jobs, last, {'SUCCEEDED'}) == 'SUCCEEDED'
    assert services.jobs.get(last)['progress'] == 100
    logs = services.logs.recent(failure)
    assert any('RuntimeError' in log['trace'] for log in logs)

def test_cancel_queued_and_running(services):
    running = services.jobs.submit(); queued = services.jobs.submit()
    wait_state(services.jobs, running, {'RUNNING'})
    services.jobs.cancel(queued); services.jobs.cancel(running)
    assert wait_state(services.jobs, running, {'CANCELLED'}) == 'CANCELLED'
    assert services.jobs.get(queued)['state'] == 'CANCELLED'
    assert services.jobs.get(running)['progress'] < 100

def test_history_and_restart_recovery(services):
    succeeded = services.jobs.submit(); wait_state(services.jobs, succeeded, {'SUCCEEDED'})
    services.jobs.close()
    for state in ['RUNNING', 'QUEUED']:
        with services.db.transaction() as session:
            session.add(JobRecord(id=state, kind='diagnostic', state=state, progress=30, created_at=utc_now(), updated_at=utc_now(), error=''))
    services.jobs = JobService(services.db, services.logs, step_seconds=0.001)
    assert services.jobs.get(succeeded)['state'] == 'SUCCEEDED'
    assert services.jobs.get('RUNNING')['state'] == 'INTERRUPTED'
    assert services.jobs.get('QUEUED')['state'] == 'INTERRUPTED'

def test_shutdown_cancel_and_no_ai_job(services):
    job = services.jobs.submit(); services.jobs.close()
    assert services.jobs.get(job)['state'] == 'CANCELLED'
    with pytest.raises(AppError): services.jobs.submit('yolo_train')
    assert not services.jobs.thread.is_alive()

def test_resource_exclusion():
    gate = ResourceGate(); active = []; overlap = []
    def operation():
        with gate.acquire('gpu-uuid', threading.Event()):
            if active: overlap.append(True)
            active.append(True); time.sleep(0.02); active.pop()
    threads = [threading.Thread(target=operation) for _ in range(3)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not overlap

def test_log_redaction_and_file_index(services):
    value = 'token=abc password=secret rtsp://user:pass@host/video C:\\Users\\secret\\project'
    services.logs.write('test', value)
    row = services.logs.recent()[0]
    assert 'abc' not in row['message'] and 'user:pass' not in row['message'] and 'Users' not in row['message']
    assert services.logs.path.is_file()
    assert '<redacted>' in redact(value)
