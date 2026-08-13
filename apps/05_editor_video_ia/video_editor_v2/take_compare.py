from __future__ import annotations
from pathlib import Path
import subprocess, html
from .models import ProjectSpec
from .quality import take_quality_score
from .runtime_tools import resolve_ffmpeg


def _extract_frame(video: str, second: float, output: Path, cwd: str | Path | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        resolve_ffmpeg(), "-y", "-ss", f"{max(0, second):.3f}", "-i", video,
        "-frames:v", "1", "-vf", "scale=480:-2", "-q:v", "3", str(output),
    ]
    cp = subprocess.run(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stdout[-1200:])


def prepare_take_comparison(project: ProjectSpec, take_group: str, output_dir: str | Path, *, cwd: str | Path | None = None) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = {s.id: s for s in project.sources}
    candidates = [x for x in project.transcript if x.take_group == take_group]
    candidates.sort(key=take_quality_score, reverse=True)
    cards = []
    for seg in candidates:
        src = sources[seg.source_id]
        thumb = output_dir / f"{take_group}_{seg.id}.jpg"
        _extract_frame(src.path, (seg.start + seg.end) / 2, thumb, cwd=cwd)
        cards.append({
            "id": seg.id,
            "source_id": seg.source_id,
            "source_label": src.label or src.id,
            "text": seg.text,
            "score": round(take_quality_score(seg), 4),
            "visual_quality": seg.visual_quality,
            "audio_quality": seg.audio_quality,
            "stability": seg.stability,
            "face_presence": seg.face_presence,
            "thumbnail": thumb.name,
        })
    return {"take_group": take_group, "candidates": cards}


def write_take_comparison_html(data: dict, output_path: str | Path) -> Path:
    out = Path(output_path)
    cards = []
    for c in data["candidates"]:
        cards.append(f'''<article><img src="{html.escape(c['thumbnail'])}"><h3>{html.escape(c['source_label'])}</h3>
        <p>{html.escape(c['text'])}</p><b>Score {c['score']:.3f}</b><small>Visual {c['visual_quality']:.2f} · Audio {c['audio_quality']:.2f} · Estabilidad {c['stability']:.2f}</small></article>''')
    doc = f'''<!doctype html><meta charset="utf-8"><title>Comparar tomas</title><style>
    body{{background:#07111d;color:#eef6ff;font:14px system-ui;padding:24px}}main{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}
    article{{background:#0d1b2b;border:1px solid #20354b;border-radius:15px;padding:12px}}img{{width:100%;border-radius:10px}}small{{display:block;color:#91a7ba;margin-top:8px}}</style>
    <h1>Grupo {html.escape(data['take_group'])}</h1><main>{''.join(cards)}</main>'''
    out.write_text(doc, encoding="utf-8")
    return out
