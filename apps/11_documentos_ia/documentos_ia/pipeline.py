from __future__ import annotations
from pathlib import Path
from .models import DocumentSpec
from .planner import scaffold
from .quality import evaluate
from .exporters import export_markdown, export_html, export_docx, export_pdf_from_docx

class DocumentsPipeline:
    def prepare(self,spec:DocumentSpec): return scaffold(spec)
    def quality(self,spec:DocumentSpec): return evaluate(spec)
    def export_all(self,spec:DocumentSpec,out_dir:str|Path,require_pass=True):
        out=Path(out_dir); out.mkdir(parents=True,exist_ok=True); stem=spec.id
        md=export_markdown(spec,out/f'{stem}.md',require_pass=require_pass)
        html=export_html(spec,out/f'{stem}.html',require_pass=require_pass)
        docx=export_docx(spec,out/f'{stem}.docx',require_pass=require_pass)
        pdf=export_pdf_from_docx(docx,out)
        return {'markdown':str(md),'html':str(html),'docx':str(docx),'pdf':str(pdf)}
