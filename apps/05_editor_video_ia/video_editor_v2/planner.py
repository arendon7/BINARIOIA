from __future__ import annotations
from dataclasses import replace
from collections import defaultdict
from .models import ProjectSpec, TimelineCut, TimelinePlan, EditMode
from .scoring import segment_score
from .quality import choose_best_takes

ROLE_ORDER={"hook":10,"context":20,"main_idea":30,"argument":40,"evidence":50,"example":55,"transition":60,"other":65,"cta":80,"closing":90,"filler":98,"repetition":99}
CORE_ROLES=("hook","main_idea","argument","cta","closing")

def _eligible(project):
    source_order={s.id:s.order for s in project.sources if s.enabled}
    rows=[s for s in project.transcript if s.source_id in source_order and s.duration>.05]
    if project.edit.remove_fillers: rows=[s for s in rows if s.role!="filler"]
    if project.edit.remove_repetitions: rows=[s for s in rows if s.role!="repetition" or s.must_keep]
    if project.edit.montage_order=="source":
        rows.sort(key=lambda s:(source_order[s.source_id],s.start))
    else:
        rows.sort(key=lambda s:(s.narrative_order if s.narrative_order is not None else ROLE_ORDER.get(s.role,65),-segment_score(s),source_order[s.source_id],s.start))
    return rows

def _recommended_min(rows):
    chosen={s.id:s for s in rows if s.must_keep}
    by_role=defaultdict(list)
    for s in rows: by_role[s.role].append(s)
    for role in CORE_ROLES:
        if by_role.get(role):
            best=max(by_role[role],key=segment_score); chosen[best.id]=best
    return sum(s.duration for s in chosen.values())

def _knapsack(rows,target,quantum=.25):
    cap=max(1,int(round(target/quantum))); states={0:(0.0,[])}
    for i,s in enumerate(rows):
        units=max(1,int(round(s.duration/quantum)))
        value=segment_score(s)+(.04/max(s.duration,.25))+(2.5 if s.must_keep else 0)
        new=dict(states)
        for used,(score,chosen) in states.items():
            nxt=used+units
            if nxt>cap: continue
            proposal=(score+value,chosen+[i])
            if nxt not in new or proposal[0]>new[nxt][0]: new[nxt]=proposal
        states=new
    must={i for i,s in enumerate(rows) if s.must_keep}
    best=None
    for used,(value,chosen) in states.items():
        if not must.issubset(set(chosen)): continue
        duration=used*quantum
        objective=value-.025*abs(target-duration)
        if best is None or objective>best[0]: best=(objective,chosen)
    return [rows[i] for i in best[1]] if best else [s for s in rows if s.must_keep]

def _ensure_coverage(rows,selected,target):
    picked={s.id:s for s in selected}; total=sum(s.duration for s in picked.values())
    present={s.role for s in rows}; current={s.role for s in picked.values()}
    for role in CORE_ROLES:
        if role not in present or role in current: continue
        cand=max((s for s in rows if s.role==role and s.id not in picked),key=segment_score,default=None)
        if cand and total+cand.duration<=target*1.08:
            picked[cand.id]=cand; total+=cand.duration
    return list(picked.values())

def _order(project,selected):
    source_order={s.id:s.order for s in project.sources}
    if project.edit.montage_order=="source":
        return sorted(selected,key=lambda s:(source_order.get(s.source_id,999),s.start))
    return sorted(selected,key=lambda s:(s.narrative_order if s.narrative_order is not None else ROLE_ORDER.get(s.role,65),source_order.get(s.source_id,999),s.start))

def _fill_gap(rows,selected,target):
    total=sum(s.duration for s in selected); gap=target-total; warnings=[]
    if gap<=0.05: return selected,warnings
    selected_ids={s.id for s in selected}
    candidates=[s for s in rows if s.id not in selected_ids and s.allow_trim and s.role not in ("filler","repetition")]
    candidates.sort(key=segment_score,reverse=True)
    for s in candidates:
        if gap<=0.05: break
        if s.duration<=gap+0.05:
            selected.append(s); gap-=s.duration
        elif gap>=0.75:
            selected.append(replace(s,end=s.start+gap))
            warnings.append(f"Se usó un fragmento parcial de {s.id} para aproximar la duración objetivo; conviene validar el corte contra la transcripción.")
            gap=0
    return selected,warnings

def _trim(selected,target):
    total=sum(s.duration for s in selected); excess=total-target; out=list(selected); warnings=[]
    if excess<=0: return out,warnings
    for i in sorted(range(len(out)),key=lambda j:segment_score(out[j])):
        if excess<=.02: break
        s=out[i]
        if s.must_keep or not s.allow_trim or s.duration<=.75: continue
        removable=min(excess,max(0,s.duration-.75))
        out[i]=replace(s,end=s.end-removable); excess-=removable
    if excess>.02: warnings.append(f"No fue posible llegar exactamente a {target:.1f}s sin romper segmentos protegidos; sobran {excess:.1f}s.")
    return out,warnings

def build_timeline(project:ProjectSpec)->TimelinePlan:
    rows=_eligible(project); take_analysis={"groups":0,"decisions":[]}
    if project.edit.select_best_takes:
        rows,take_analysis=choose_best_takes(rows)
        rows=_order(project,rows)
    recommended=_recommended_min(rows); warnings=[]
    if project.edit.mode==EditMode.NATURAL:
        selected=[s for s in rows if s.must_keep or segment_score(s)>=project.edit.min_natural_score]; target=None
    else:
        target=project.edit.target_duration
        if target is None or target<=0: raise ValueError("target_duration debe ser > 0")
        selected=_knapsack(rows,target)
        selected=_ensure_coverage(rows,selected,target)
        selected=_order(project,selected)
        selected,w=_trim(selected,target); warnings+=w
        selected,w=_fill_gap(rows,selected,target); warnings+=w
        if target+project.edit.tolerance<recommended:
            warnings.append(f"Objetivo {target:.1f}s por debajo del mínimo narrativo estimado {recommended:.1f}s.")
    selected=_order(project,selected)
    cursor=0.0; cuts=[]
    for n,s in enumerate(selected,1):
        d=s.duration
        cuts.append(TimelineCut(f"cut-{n:03d}",s.source_id,s.start,s.end,cursor,cursor+d,s.text,s.role,segment_score(s),list(getattr(s,"keywords",[]) or [])))
        cursor+=d
    total_eligible=sum(s.duration for s in rows)
    return TimelinePlan(
        mode=project.edit.mode.value,target_duration=target,actual_duration=cursor,recommended_min_duration=recommended,
        within_tolerance=True if target is None else abs(cursor-target)<=project.edit.tolerance,
        cuts=cuts,assets=[a for a in project.assets if a.enabled],warnings=warnings,
        analysis={"source_count":len([s for s in project.sources if s.enabled]),"eligible_segments":len(rows),
                  "selected_segments":len(selected),"discarded_segments":max(0,len(rows)-len(selected)),
                  "original_eligible_duration":round(total_eligible,3),"selected_duration":round(cursor,3),
                  "compression_ratio":round(cursor/total_eligible,4) if total_eligible else 0,
                  "best_take_selection":take_analysis,"tolerance":project.edit.tolerance}
    )
