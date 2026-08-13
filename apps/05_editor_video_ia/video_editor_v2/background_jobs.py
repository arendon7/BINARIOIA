from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import threading, uuid

TERMINAL={"done","failed","cancelled"}

@dataclass
class BackgroundJob:
    id:str
    kind:str
    status:str="queued"
    progress:float=0.0
    stage:str="queued"
    message:str="En cola"
    error:str|None=None
    result:dict|None=None
    started_at_utc:str|None=None
    finished_at_utc:str|None=None
    def to_dict(self): return asdict(self)

class BackgroundJobManager:
    def __init__(self):
        self.jobs={}; self._lock=threading.RLock()
    def start(self,kind,runner):
        jid=uuid.uuid4().hex[:12]; job=BackgroundJob(jid,kind)
        with self._lock:self.jobs[jid]=job
        threading.Thread(target=self._run,args=(jid,runner),daemon=True).start()
        return job
    def _run(self,jid,runner):
        with self._lock:
            job=self.jobs[jid];job.status="running";job.started_at_utc=datetime.now(timezone.utc).isoformat()
        def update(progress,stage,message=None):
            with self._lock:
                j=self.jobs[jid];j.progress=max(j.progress,min(1.0,float(progress)));j.stage=str(stage);j.message=str(message or stage)
        try:
            result=runner(update)
            with self._lock:
                j=self.jobs[jid];j.status="done";j.progress=1.0;j.stage="done";j.message="Listo";j.result=result;j.finished_at_utc=datetime.now(timezone.utc).isoformat()
        except Exception as exc:
            with self._lock:
                j=self.jobs[jid];j.status="failed";j.error=f"{type(exc).__name__}: {exc}";j.message=str(exc);j.finished_at_utc=datetime.now(timezone.utc).isoformat()
    def get(self,jid):
        with self._lock:return self.jobs.get(jid)
