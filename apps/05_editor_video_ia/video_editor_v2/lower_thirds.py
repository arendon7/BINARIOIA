from __future__ import annotations
from pathlib import Path
from .models import TimelinePlan
from .brand_presets import BrandPreset
from .subtitles import _ass_time


def _ass_color(hex_color: str, alpha: str = "00") -> str:
    s = hex_color.strip().lstrip("#")
    if len(s) != 6: s = "FFFFFF"
    r, g, b = s[0:2], s[2:4], s[4:6]
    return f"&H{alpha}{b}{g}{r}"


def _title(text: str, role: str, max_words: int = 4) -> str:
    stop = {"esta","este","esto","es","la","el","de","del","una","un","te","para","que","y","nos"}
    words = [w.strip(".,:;!?¡¿") for w in (text or "").strip().split()]
    meaningful = [w for w in words if w.lower() not in stop and len(w) > 2]
    core = " ".join(meaningful[:max_words]).replace("{", "").replace("}", "")
    labels = {"main_idea":"IDEA CLAVE", "evidence":"DATO CLAVE", "cta":"SIGUIENTE PASO"}
    label = labels.get(role, role.replace("_"," ").upper())
    return f"{label} · {core}" if core else label


def write_lower_thirds_ass(plan: TimelinePlan, output_path: str | Path, width: int, height: int, preset: BrandPreset) -> Path:
    out = Path(output_path); out.parent.mkdir(parents=True, exist_ok=True)
    font_size = max(20, min(58, int(width * 0.044)))
    margin_l = int(width * preset.safe_margin); margin_v = int(height * 0.28)
    fg = _ass_color(preset.text); bg = _ass_color(preset.secondary, "55"); outline = _ass_color(preset.secondary)
    header = f"""[Script Info]\nScriptType: v4.00+\nPlayResX: {width}\nPlayResY: {height}\nScaledBorderAndShadow: yes\n\n[V4+ Styles]\nFormat: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding\nStyle: Lower,Arial,{font_size},{fg},{fg},{outline},{bg},-1,0,0,0,100,100,0,0,3,2,0,1,{margin_l},{margin_l},{margin_v},1\n\n[Events]\nFormat: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text\n"""
    lines = [header]; roles = set(preset.lower_third_roles)
    for cut in plan.cuts:
        if cut.role not in roles: continue
        start = cut.timeline_start; end = min(cut.timeline_end, start + 3.4)
        if end - start < 0.7: continue
        text = _title(cut.text, cut.role)
        if text: lines.append(f"Dialogue: 1,{_ass_time(start)},{_ass_time(end)},Lower,,0,0,0,,{text}\n")
    out.write_text("".join(lines), encoding="utf-8"); return out
