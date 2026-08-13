from __future__ import annotations
import html, json
from pathlib import Path
from .models import ProjectSpec, TimelinePlan

def generate_preview_html(project: ProjectSpec, plan: TimelinePlan, output_path: str | Path) -> Path:
    out=Path(output_path); out.parent.mkdir(parents=True,exist_ok=True)
    duration=max(plan.actual_duration,.001)
    colors={"hook":"#2e86de","context":"#40739e","main_idea":"#44bd32","argument":"#8c7ae6","evidence":"#00a8ff","example":"#e1b12c","cta":"#e84118","closing":"#c23616","other":"#718093"}
    cuts=[]
    for c in plan.cuts:
        width=max(1,(c.duration/duration)*100)
        cuts.append(f'<div class="clip" title="{html.escape(c.text)}" style="width:{width:.3f}%;background:{colors.get(c.role,"#718093")}">{html.escape(c.role)}</div>')
    assets=[]
    for a in sorted(plan.assets,key=lambda x:(x.z_index,x.start)):
        end=a.end if a.end is not None else duration; left=max(0,a.start/duration*100); width=max(.7,(max(a.start,end)-a.start)/duration*100)
        assets.append(f'<div class="assetline"><span>{html.escape(a.id)} · {html.escape(a.kind)} · {html.escape(a.placement)}</span><div class="rail"><i style="left:{left:.3f}%;width:{width:.3f}%"></i></div></div>')
    warnings=''.join(f'<li>{html.escape(w)}</li>' for w in plan.warnings) or '<li>Sin advertencias.</li>'
    payload=html.escape(json.dumps(plan.to_dict(),ensure_ascii=False))
    doc=f'''<!doctype html><html lang="es"><meta charset="utf-8"><title>{html.escape(project.name)} · Preview</title><style>
body{{margin:0;background:#07111d;color:#eef6ff;font:14px system-ui}}main{{max-width:1200px;margin:auto;padding:28px}}.card{{background:#0d1b2b;border:1px solid #20354b;border-radius:16px;padding:16px;margin:12px 0}}.kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}}.kpi{{background:#091725;padding:12px;border-radius:12px}}.kpi b{{display:block;font-size:22px}}.timeline{{display:flex;height:46px;overflow:hidden;border-radius:10px}}.clip{{display:flex;align-items:center;justify-content:center;font-size:11px;border-right:1px solid #07111d;overflow:hidden}}.assetline{{display:grid;grid-template-columns:230px 1fr;gap:12px;margin:8px 0;align-items:center}}.rail{{height:16px;background:#091725;border-radius:9px;position:relative}}.rail i{{position:absolute;top:2px;bottom:2px;background:#9b59b6;border-radius:7px}}li{{margin:6px 0;color:#ffd77a}}.muted{{color:#91a8bb}}@media(max-width:700px){{.kpis{{grid-template-columns:1fr 1fr}}.assetline{{grid-template-columns:1fr}}}}
</style><body><main><h1>Editor Video IA · Preview de montaje</h1><div class="muted">{html.escape(project.name)}</div><div class="kpis"><div class="kpi">Modo<b>{html.escape(plan.mode)}</b></div><div class="kpi">Duración<b>{plan.actual_duration:.1f}s</b></div><div class="kpi">Cortes<b>{len(plan.cuts)}</b></div><div class="kpi">Artes/B-roll<b>{len(plan.assets)}</b></div></div><div class="card"><b>Narrativa</b><div class="timeline">{''.join(cuts)}</div></div><div class="card"><b>Capas</b>{''.join(assets) or '<p class="muted">Sin assets.</p>'}</div><div class="card"><b>Advertencias</b><ul>{warnings}</ul></div><details class="card"><summary>Plan JSON</summary><pre>{payload}</pre></details></main></body></html>'''
    out.write_text(doc,encoding='utf-8'); return out
