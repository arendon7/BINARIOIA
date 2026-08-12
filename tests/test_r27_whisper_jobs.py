from __future__ import annotations
import time
from unittest import mock


def wait_done(jobs, job_id, timeout=3):
    end=time.time()+timeout
    while time.time()<end:
        row=jobs.get(job_id)
        if row.get('status') in {'done','failed'}:
            return row
        time.sleep(.02)
    raise AssertionError('job timeout')


def test_prepare_job_runs_async_and_reaches_ready():
    from runtime import whisper_jobs as jobs
    with mock.patch.object(jobs,'status',return_value={'ready':False,'runtime_ok':True,'model_cached':False}), mock.patch.object(jobs,'prepare',return_value={'ok':True,'stage':'ready'}):
        row=jobs.start('prepare','small')
        assert row['status'] in {'queued','running','done'}
        done=wait_done(jobs,row['job_id'])
    assert done['status']=='done'
    assert done['progress']==100
    assert 'listo' in done['message'].lower()


def test_duplicate_job_reuses_active_job():
    from runtime import whisper_jobs as jobs
    gate=[]
    def slow(_model):
        time.sleep(.08);gate.append(1);return {'ok':True}
    with mock.patch.object(jobs,'status',return_value={'ready':False,'runtime_ok':True}), mock.patch.object(jobs,'prepare',side_effect=slow):
        a=jobs.start('prepare','small');b=jobs.start('prepare','small')
        assert a['job_id']==b['job_id']
        wait_done(jobs,a['job_id'])
    assert len(gate)==1
