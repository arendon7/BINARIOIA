from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
class SubjectMatteUnavailable(RuntimeError): pass
class SubjectMatteProvider(Protocol):
    def create_matte(self,input_video:str,output_mask:str)->str: ...
@dataclass
class ExternalMatteProvider:
    matte_path:str
    def create_matte(self,input_video:str,output_mask:str)->str:
        p=Path(self.matte_path)
        if not p.exists(): raise SubjectMatteUnavailable(f"Matte no encontrado: {p}")
        return str(p)
class MediaPipeMatteProvider:
    def __init__(self,model_asset_path:str): self.model_asset_path=model_asset_path
    def create_matte(self,input_video:str,output_mask:str)->str:
        try:
            import cv2, mediapipe as mp
        except Exception as exc:
            raise SubjectMatteUnavailable("Para matte local se requieren mediapipe y opencv-python.") from exc
        model=Path(self.model_asset_path)
        if not model.exists(): raise SubjectMatteUnavailable("Falta el modelo de segmentación configurado.")
        BaseOptions=mp.tasks.BaseOptions; ImageSegmenter=mp.tasks.vision.ImageSegmenter; ImageSegmenterOptions=mp.tasks.vision.ImageSegmenterOptions; RunningMode=mp.tasks.vision.RunningMode
        cap=cv2.VideoCapture(input_video)
        if not cap.isOpened(): raise SubjectMatteUnavailable(f"No se pudo abrir {input_video}")
        fps=cap.get(cv2.CAP_PROP_FPS) or 30.0; w=int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); h=int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        writer=cv2.VideoWriter(output_mask,cv2.VideoWriter_fourcc(*'mp4v'),fps,(w,h),isColor=False)
        options=ImageSegmenterOptions(base_options=BaseOptions(model_asset_path=str(model)),running_mode=RunningMode.VIDEO,output_category_mask=True)
        frame=0
        with ImageSegmenter.create_from_options(options) as segmenter:
            while True:
                ok,img=cap.read()
                if not ok: break
                rgb=cv2.cvtColor(img,cv2.COLOR_BGR2RGB); mpimg=mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb)
                res=segmenter.segment_for_video(mpimg,int(frame/fps*1000)); mask=(res.category_mask.numpy_view()>0).astype('uint8')*255 if res.category_mask is not None else img[:,:,0]*0
                writer.write(mask); frame+=1
        cap.release(); writer.release(); return output_mask
