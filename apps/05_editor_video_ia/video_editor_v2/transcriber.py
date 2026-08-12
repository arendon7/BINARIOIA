from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional, Callable
from .models import VideoSource, TranscriptSegment
from .whisper_runtime import MODELS_ROOT, model_source

class TranscriptionUnavailable(RuntimeError):
    pass

class TranscriptProvider(Protocol):
    def transcribe_source(self, source: VideoSource, language: Optional[str] = None) -> list[TranscriptSegment]: ...

@dataclass
class FasterWhisperConfig:
    model_size: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 5
    vad_filter: bool = True
    download_root: str = str(MODELS_ROOT)

class FasterWhisperTranscriber:
    def __init__(self, config: FasterWhisperConfig | None = None):
        self.config = config or FasterWhisperConfig()
        self._model = None

    def _load(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
        except Exception as exc:
            raise TranscriptionUnavailable(
                "Whisper no está instalado. Usa ‘Preparar Whisper’ en el Editor o reinstala Binario IA FULL."
            ) from exc
        try:
            source = model_source(self.config.model_size)
            kwargs = {"device": self.config.device, "compute_type": self.config.compute_type}
            if source == self.config.model_size:
                kwargs["download_root"] = self.config.download_root
            self._model = WhisperModel(source, **kwargs)
        except Exception as exc:
            raise TranscriptionUnavailable(
                f"No se pudo cargar Whisper {self.config.model_size}. Revisa Internet/modelo desde ‘Preparar Whisper’: {exc}"
            ) from exc
        return self._model

    def prepare(self):
        self._load(); return self

    def transcribe_source(self, source: VideoSource, language: Optional[str] = None) -> list[TranscriptSegment]:
        model = self._load()
        try:
            segments, _ = model.transcribe(
                source.path,
                beam_size=self.config.beam_size,
                vad_filter=self.config.vad_filter,
                language=language or None,
                word_timestamps=False,
            )
        except Exception as exc:
            raise TranscriptionUnavailable(f"Whisper no pudo transcribir {source.label or source.path}: {exc}") from exc
        result = []
        for idx, seg in enumerate(segments, 1):
            text = (getattr(seg, "text", "") or "").strip()
            if text:
                result.append(TranscriptSegment(id=f"{source.id}-asr-{idx:04d}", source_id=source.id, start=float(seg.start), end=float(seg.end), text=text))
        if not result:
            raise TranscriptionUnavailable(f"Whisper no detectó voz utilizable en {source.label or source.path}.")
        return result

class StaticTranscriptProvider:
    def __init__(self, mapping: dict[str, list[TranscriptSegment]]): self.mapping = mapping
    def transcribe_source(self, source: VideoSource, language: Optional[str] = None) -> list[TranscriptSegment]:
        return list(self.mapping.get(source.id, []))

def transcribe_project(project, provider: TranscriptProvider, force: bool = False):
    if project.transcript and not force: return project
    transcript=[]
    for source in sorted((s for s in project.sources if s.enabled), key=lambda s:s.order):
        transcript.extend(provider.transcribe_source(source, language=project.edit.transcription_language))
    project.transcript=transcript
    return project
