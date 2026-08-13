from __future__ import annotations
from pathlib import Path
from .models import ProjectSpec, EditMode
VIDEO_EXT={'.mp4','.mov','.m4v','.mkv','.webm'}; IMAGE_EXT={'.png','.jpg','.jpeg','.webp'}; AUDIO_EXT={'.mp3','.wav','.aac','.m4a','.flac'}
def validate_project(project:ProjectSpec,check_files:bool=False)->list[str]:
    errors=[]; ids=[s.id for s in project.sources]; source_ids=set(ids)
    if len(ids)!=len(source_ids): errors.append('Hay IDs de videos duplicados.')
    if not project.sources: errors.append('El proyecto necesita al menos un video.')
    for seg in project.transcript:
        if seg.source_id not in source_ids: errors.append(f'Segmento {seg.id}: source_id inexistente {seg.source_id}.')
        if seg.end<=seg.start: errors.append(f'Segmento {seg.id}: end debe ser > start.')
    if project.edit.mode==EditMode.TARGET_DURATION and (project.edit.target_duration is None or project.edit.target_duration<=0): errors.append('Duración objetiva debe ser > 0.')
    if len([a for a in project.assets if a.enabled and a.kind=='subject_matte'])>1: errors.append('RC2 admite un solo subject_matte alineado a la timeline final.')
    if check_files:
        for s in project.sources:
            p=Path(s.path)
            if not p.exists(): errors.append(f'Video no encontrado: {p}')
            elif p.suffix.lower() not in VIDEO_EXT: errors.append(f'Formato de video no reconocido: {p}')
        for audio in project.audio_sources:
            p=Path(audio.path)
            if not p.exists(): errors.append(f'Audio externo no encontrado: {p}')
            elif p.suffix.lower() not in AUDIO_EXT | VIDEO_EXT: errors.append(f'Formato de audio externo no reconocido: {p}')
        for a in project.assets:
            p=Path(a.path)
            if not p.exists(): errors.append(f'Asset no encontrado: {p}')
            elif a.kind in {'logo','image','background','lower_third'} and p.suffix.lower() not in IMAGE_EXT: errors.append(f'Asset gráfico no reconocido: {p}')
            elif a.kind in {'broll','subject_matte'} and p.suffix.lower() not in VIDEO_EXT: errors.append(f'Asset de video no reconocido: {p}')
            elif a.kind in {'music','sfx'} and p.suffix.lower() not in AUDIO_EXT: errors.append(f'Asset de audio no reconocido: {p}')
    return errors
