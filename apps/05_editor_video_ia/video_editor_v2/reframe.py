from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from typing import Optional
from .models import ProjectSpec, TimelinePlan

FORMAT_PRESETS = {
    "vertical": (1080, 1920),
    "horizontal": (1920, 1080),
    "square": (1080, 1080),
    "portrait_4_5": (1080, 1350),
}


def apply_output_preset(project: ProjectSpec, preset: str) -> ProjectSpec:
    if preset not in FORMAT_PRESETS:
        raise ValueError(f"Formato desconocido: {preset}")
    project.output.width, project.output.height = FORMAT_PRESETS[preset]
    if preset == "horizontal":
        project.output.proxy_width, project.output.proxy_height = 640, 360
    elif preset == "square":
        project.output.proxy_width, project.output.proxy_height = 480, 480
    elif preset == "portrait_4_5":
        project.output.proxy_width, project.output.proxy_height = 432, 540
    else:
        project.output.proxy_width, project.output.proxy_height = 360, 640
    project.metadata["output_preset"] = preset
    return project


def apply_focus_to_plan(plan: TimelinePlan, focus_by_cut: dict[str, tuple[float, float, float]]) -> TimelinePlan:
    cuts = []
    for c in plan.cuts:
        fx, fy, conf = focus_by_cut.get(c.id, (getattr(c, "focus_x_norm", 0.5), getattr(c, "focus_y_norm", 0.5), getattr(c, "focus_confidence", 0.0)))
        cuts.append(replace(
            c,
            focus_x_norm=max(0.0, min(1.0, float(fx))),
            focus_y_norm=max(0.0, min(1.0, float(fy))),
            focus_confidence=max(0.0, min(1.0, float(conf))),
        ))
    plan.cuts = cuts
    return plan


class OpenCVFaceTracker:
    def __init__(self):
        try:
            import cv2
        except Exception as exc:
            raise RuntimeError("OpenCV no está disponible para Face Tracker.") from exc
        self.cv2 = cv2
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self.detector = cv2.CascadeClassifier(str(cascade_path))
        if self.detector.empty():
            raise RuntimeError("No se pudo cargar el detector de rostro de OpenCV.")

    def detect(self, project: ProjectSpec, plan: TimelinePlan) -> dict[str, tuple[float, float, float]]:
        source_map = {s.id: s for s in project.sources}
        result = {}
        for cut in plan.cuts:
            src = source_map.get(cut.source_id)
            if not src:
                continue
            cap = self.cv2.VideoCapture(src.path)
            if not cap.isOpened():
                continue
            mid = (cut.source_start + cut.source_end) / 2
            cap.set(self.cv2.CAP_PROP_POS_MSEC, mid * 1000)
            ok, frame = cap.read(); cap.release()
            if not ok:
                continue
            gray = self.cv2.cvtColor(frame, self.cv2.COLOR_BGR2GRAY)
            faces = self.detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(40, 40))
            if len(faces) == 0:
                result[cut.id] = (0.5, 0.5, 0.0)
                continue
            x, y, w, h = max(faces, key=lambda b: b[2] * b[3])
            fh, fw = frame.shape[:2]
            result[cut.id] = ((x + w / 2) / fw, (y + h / 2) / fh, min(1.0, (w*h)/(fw*fh)*8.0))
        return result
