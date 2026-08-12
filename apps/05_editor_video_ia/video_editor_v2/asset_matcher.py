from __future__ import annotations
import re, unicodedata
from dataclasses import replace
from .models import AssetSpec, TimelinePlan
STOP={"de","la","el","y","en","que","a","los","las","un","una","por","para","con","del","es","se","lo","al"}
def _tokens(text):
    text=unicodedata.normalize("NFKD",(text or "").lower()); text="".join(c for c in text if not unicodedata.combining(c))
    return {x for x in re.findall(r"[a-z0-9]{3,}",text) if x not in STOP}
def _asset_tokens(a): return _tokens(" ".join(a.tags)+" "+a.description+" "+a.id)
def auto_place_assets(plan:TimelinePlan, assets:list[AssetSpec], max_per_cut:int=1)->list[AssetSpec]:
    fixed=[a for a in assets if a.enabled and not a.auto_place]; automatic=[a for a in assets if a.enabled and a.auto_place]; placed=list(fixed); used=set()
    for cut in plan.cuts:
        ct=set(cut.keywords)|_tokens(cut.text); cand=[]
        for a in automatic:
            if a.id in used: continue
            at=_asset_tokens(a); score=len(at&ct)/max(1,len(at|ct)) if at and ct else 0.0
            if score>0: cand.append((score,a))
        cand.sort(key=lambda x:x[0],reverse=True)
        for score,a in cand[:max_per_cut]:
            dur=cut.duration if a.max_duration is None else min(cut.duration,max(.5,a.max_duration))
            placement="broll" if a.kind=="broll" else a.placement
            placed.append(replace(a,start=cut.timeline_start,end=min(cut.timeline_end,cut.timeline_start+dur),placement=placement,score=round(score,4))); used.add(a.id)
    return placed
