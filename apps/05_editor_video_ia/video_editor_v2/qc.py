from __future__ import annotations
from .models import ProjectSpec, TimelinePlan

def quality_control(project: ProjectSpec, plan: TimelinePlan) -> dict:
    issues = []
    warnings = []
    if not plan.cuts:
        issues.append("La timeline no contiene cortes.")
    if project.edit.mode.value == "target_duration" and not plan.within_tolerance:
        warnings.append("La duración final está fuera de tolerancia.")
    if project.edit.subtitles and any(len(c.text) > 180 for c in plan.cuts):
        warnings.append("Hay subtítulos potencialmente demasiado largos; conviene segmentar frases.")
    if any(a.placement == "behind_subject" for a in plan.assets) and not any(a.kind == "subject_matte" for a in plan.assets):
        warnings.append("Hay artes 'behind_subject' sin matte; se usará el fallback de fondo decorado.")
    music = [a for a in plan.assets if a.enabled and a.kind == "music"]
    if music and not project.edit.music_ducking:
        warnings.append("Hay música sin ducking automático; validar inteligibilidad de voz.")
    selected_external = [c for c in plan.cuts if getattr(c, "audio_source_id", None)]
    if project.audio_sources and project.edit.auto_sync_external_audio and "audio_intelligence" not in plan.analysis:
        warnings.append("Hay audios externos de voz sin analizar. Ejecuta Audio Intelligence antes del render final.")
    low_sync = [c for c in selected_external if float(getattr(c, "audio_sync_confidence", 0.0)) < project.edit.audio_sync_confidence_min]
    if low_sync:
        issues.append("Hay reemplazos de audio externo por debajo del umbral de sincronización labial.")
    return {
        "status": "blocked" if issues else ("warning" if warnings else "pass"),
        "issues": issues,
        "warnings": warnings,
        "metrics": {
            "duration": round(plan.actual_duration, 3),
            "cuts": len(plan.cuts),
            "assets": len([a for a in plan.assets if a.enabled]),
            "music_tracks": len(music),
            "external_dialogue_tracks": len(project.audio_sources),
            "external_audio_selected_cuts": len(selected_external),
            "minimum_external_sync": round(min([float(c.audio_sync_confidence) for c in selected_external], default=1.0), 4),
        },
    }
