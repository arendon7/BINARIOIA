from __future__ import annotations
from dataclasses import dataclass, asdict
from statistics import median
from typing import Iterable
from .models import ProjectSpec, TimelinePlan

@dataclass
class AudioEnhancementDecision:
    enabled: bool
    requested_preset: str
    resolved_preset: str
    denoise: bool
    normalize: bool
    target_lufs: float
    true_peak: float
    quality_basis: float | None
    filters: list[str]
    explanation: str

    def to_dict(self):
        return asdict(self)

def _quality_values(plan: TimelinePlan) -> list[float]:
    vals = []
    for c in plan.cuts:
        v = getattr(c, 'audio_quality_score', None)
        if v is None or v <= 0:
            v = getattr(c, 'camera_audio_quality_score', None)
        if v is not None and v > 0:
            vals.append(float(v))
    return vals

def _resolve_preset(project: ProjectSpec, plan: TimelinePlan) -> tuple[str, float | None]:
    requested = getattr(project.edit, 'audio_enhancement_preset', 'auto') or 'auto'
    vals = _quality_values(plan)
    q = median(vals) if vals else None
    if requested != 'auto':
        return requested, q
    if q is None:
        return 'natural', q
    if q < 0.55:
        return 'studio', q
    if q < 0.74:
        return 'clean', q
    return 'natural', q

def _should_denoise(project: ProjectSpec, preset: str, q: float | None) -> bool:
    mode = getattr(project.edit, 'audio_denoise_mode', 'auto') or 'auto'
    if getattr(project.edit, 'noise_reduction', False): return True
    if mode == 'on': return True
    if mode == 'off': return False
    if q is not None and q >= 0.86: return False
    return preset in {'natural', 'clean', 'studio'}

def build_audio_enhancement(project: ProjectSpec, plan: TimelinePlan) -> AudioEnhancementDecision:
    enabled = bool(getattr(project.edit, 'auto_enhance_audio', True))
    requested = getattr(project.edit, 'audio_enhancement_preset', 'auto') or 'auto'
    resolved, q = _resolve_preset(project, plan)
    denoise = enabled and _should_denoise(project, resolved, q)
    normalize = bool(getattr(project.edit, 'normalize_loudness', True))
    filters: list[str] = []
    if enabled:
        if resolved == 'natural':
            filters += ['highpass=f=70', 'lowpass=f=16000']
            if denoise: filters += ['afftdn=nr=7:nf=-38']
            if getattr(project.edit, 'voice_enhancement', True): filters += ['equalizer=f=2800:t=q:w=1:g=1.0','acompressor=threshold=0.18:ratio=2:attack=20:release=220:makeup=1.0']
        elif resolved == 'clean':
            filters += ['highpass=f=75', 'lowpass=f=15500']
            if denoise: filters += ['afftdn=nr=11:nf=-36']
            if getattr(project.edit, 'voice_enhancement', True): filters += ['equalizer=f=250:t=q:w=1:g=-1.0','equalizer=f=3000:t=q:w=1:g=1.6','acompressor=threshold=0.15:ratio=2.5:attack=18:release=240:makeup=1.1']
        elif resolved == 'studio':
            filters += ['highpass=f=80', 'lowpass=f=15000']
            if denoise: filters += ['afftdn=nr=14:nf=-34']
            if getattr(project.edit, 'voice_enhancement', True): filters += ['equalizer=f=220:t=q:w=1:g=-1.5','equalizer=f=3200:t=q:w=1:g=2.0','acompressor=threshold=0.125:ratio=3:attack=15:release=260:makeup=1.15']
    else:
        if getattr(project.edit, 'audio_cleanup', False): filters += ['highpass=f=70', 'lowpass=f=16000']
        if getattr(project.edit, 'noise_reduction', False): filters += ['afftdn=nr=10:nf=-36']
    if normalize: filters += [f'loudnorm=I={project.edit.target_lufs:.1f}:LRA=11:TP={project.edit.true_peak:.1f}']
    if not filters: filters = ['anull']
    if not enabled:
        explanation = 'Mejora automática desactivada; se respetan únicamente ajustes manuales/legados.'
    else:
        qtxt = 'sin métrica previa' if q is None else f'calidad mediana {q:.3f}'
        explanation = f'Perfil {resolved} resuelto desde {requested} ({qtxt}); denoise={"sí" if denoise else "no"}; normalización={"sí" if normalize else "no"}.'
    return AudioEnhancementDecision(enabled=enabled,requested_preset=requested,resolved_preset=resolved,denoise=denoise,normalize=normalize,target_lufs=float(project.edit.target_lufs),true_peak=float(project.edit.true_peak),quality_basis=q,filters=filters,explanation=explanation)
