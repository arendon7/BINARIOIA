from pathlib import Path
def run(payload=None):
 return {"status":"service","app_id":"11-documentos-ia","module":"documentos_ia.service","root":str(Path(__file__).resolve().parent)}
