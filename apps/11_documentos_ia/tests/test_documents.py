import json,tempfile,unittest,hashlib
from pathlib import Path
from documentos_ia.models import DocumentSpec,ContentBlock,SourceRef
from documentos_ia.planner import scaffold
from documentos_ia.quality import evaluate
from documentos_ia.exporters import export_markdown,export_html,export_docx
from documentos_ia.revision import revision_hash,diff_specs
from documentos_ia.workspace import Workspace
from documentos_ia.intake import extract_text
from documentos_ia.security import safe_filename,validate_upload
from documentos_ia.workflow_adapter import run_workflow
from documentos_ia.generator import apply_generated_blocks

ROOT=Path(__file__).resolve().parents[1]

def sample(): return DocumentSpec.from_json(ROOT/'examples/sample_project.json')

class DocumentTests(unittest.TestCase):
    def test_sample_quality_pass(self):
        q=evaluate(sample()); self.assertEqual(q.status,'pass'); self.assertGreaterEqual(q.score,85)
    def test_placeholder_blocks(self):
        s=sample(); s.blocks.append(ContentBlock(id='x',kind='paragraph',text='[[PENDIENTE:algo]]')); self.assertEqual(evaluate(s).status,'blocked')
    def test_broken_source_blocks(self):
        s=sample(); s.blocks[1].source_ids=['missing']; self.assertEqual(evaluate(s).status,'blocked')
    def test_low_source_coverage_blocks(self):
        s=sample();
        for b in s.blocks:
            if b.kind=='paragraph': b.source_ids=[]
        self.assertEqual(evaluate(s).status,'blocked')
    def test_scaffold(self):
        s=DocumentSpec(id='x',title='X',document_type='report',objective='Objetivo'); scaffold(s); self.assertTrue(any(b.kind=='heading' for b in s.blocks))
    def test_revision_hash_stable(self):
        s=sample(); self.assertEqual(revision_hash(s),revision_hash(s))
    def test_revision_hash_changes(self):
        s=sample(); h=revision_hash(s); s.title+=' 2'; self.assertNotEqual(h,revision_hash(s))
    def test_diff(self):
        a=sample(); b=sample(); b.title='Otro'; self.assertIn('+  "title": "Otro"',diff_specs(a,b))
    def test_workspace_history(self):
        with tempfile.TemporaryDirectory() as td:
            w=Workspace(td); w.save(sample(),'uno'); w.save(sample(),'dos'); self.assertEqual(len(w.history()),2)
    def test_markdown_export(self):
        with tempfile.TemporaryDirectory() as td:
            p=export_markdown(sample(),Path(td)/'a.md'); self.assertIn('# Documentos IA',p.read_text(encoding='utf-8'))
    def test_html_export(self):
        with tempfile.TemporaryDirectory() as td:
            p=export_html(sample(),Path(td)/'a.html'); self.assertIn('Fuentes y procedencia',p.read_text(encoding='utf-8'))
    def test_docx_export(self):
        with tempfile.TemporaryDirectory() as td:
            p=export_docx(sample(),Path(td)/'a.docx'); self.assertTrue(p.exists()); self.assertGreater(p.stat().st_size,5000)
    def test_intake_txt_hash(self):
        text,src=extract_text(ROOT/'examples/base_fuente.txt'); self.assertIn('Documentos IA',text); self.assertEqual(len(src.hash_sha256),64)
    def test_intake_docx(self):
        with tempfile.TemporaryDirectory() as td:
            p=export_docx(sample(),Path(td)/'a.docx'); text,src=extract_text(p); self.assertIn('Resumen ejecutivo',text)
    def test_safe_filename(self): self.assertEqual(safe_filename('../../mal:?x.pdf'),'mal_x.pdf')
    def test_upload_validation(self): self.assertTrue(validate_upload(ROOT/'examples/base_fuente.txt'))
    def test_workflow_contract(self):
        out=run_workflow(sample().to_dict()); self.assertEqual(out['schema'],'sbia-flow-1.2'); self.assertEqual(out['quality']['status'],'pass')
    def test_generator_preserves_locked(self):
        s=sample(); before=s.blocks[0].text
        class P:
            def generate_blocks(self,payload): return [{'id':'h1','text':'NO'},{'id':'p1','text':'Texto generado profesional suficientemente desarrollado para reemplazar el bloque original.','source_ids':[s.sources[0].id]}]
        apply_generated_blocks(s,P()); self.assertEqual(s.blocks[0].text,before); self.assertTrue(s.blocks[1].text.startswith('Texto generado'))
    def test_quality_metrics(self):
        q=evaluate(sample()); self.assertGreater(q.metrics['words'],80); self.assertGreaterEqual(q.metrics['source_coverage'],.7)
    def test_empty_objective_blocks(self):
        s=sample(); s.objective=''; self.assertEqual(evaluate(s).status,'blocked')

if __name__=='__main__': unittest.main()
