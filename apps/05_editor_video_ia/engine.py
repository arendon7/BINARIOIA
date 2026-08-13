from pathlib import Path
def run(payload=None):
 return {"status":"service","app_id":"05-editor-video-ia","module":"video_editor_v2.editor_server","root":str(Path(__file__).resolve().parent)}
