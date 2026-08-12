import os,tempfile,unittest
from pathlib import Path
from research_studio import store,research
class ResearchStudioR16Test(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_RESEARCH_STUDIO_HOME','BINARIO_PROJECTS_HOME','BINARIO_STATE_HOME']};os.environ['BINARIO_RESEARCH_STUDIO_HOME']=str(Path(self.t.name)/'legacy-research');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.t.name)/'projects');os.environ['BINARIO_STATE_HOME']=str(Path(self.t.name)/'state')
    def tearDown(self):
        for k,v in self.old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
        self.t.cleanup()
    def test_project_ingest_analyze_export(self):
        p=store.create('Prueba','¿Qué afirma la evidencia sobre energía solar?');research.ingest_text(p,'La energía solar reduce el consumo de electricidad de red en instalaciones con generación propia.','Fuente A');research.ingest_text(p,'La energía solar no elimina completamente la dependencia de la red eléctrica.','Fuente B');r=research.analyze(p);self.assertEqual(r['result']['status'],'pass');self.assertTrue(r['project']['claims']);x=research.export(r['project']);self.assertTrue(Path(x['zip']).is_file())
    def test_discovery_parser(self):
        rows=research.parse_discovery_html('<a class="result__a" href="https://example.com/a">Resultado A</a><a class="result__a" href="https://example.org/b">Resultado B</a>');self.assertEqual(len(rows),2)
    def test_readiness_blocks_empty(self):
        p=store.create('P','');r=research.readiness(p);self.assertFalse(r['ready']);self.assertIn('question_missing',r['blockers'])
    def test_private_url_blocked(self): self.assertFalse(research._public_url('http://127.0.0.1/test'))
    def test_state_and_exports_live_inside_canonical_project(self):
        from common import project_center
        p=store.create('Canonical','Pregunta');row=project_center.get(p['id']);root=Path(row['metadata']['project_path']).resolve();state=store.project_dir(p['id']).resolve();exports=store.export_dir(p['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/10-investigador-ia',state.as_posix());self.assertIn('exports/10-investigador-ia',exports.as_posix())
    def test_legacy_state_is_copied_not_deleted(self):
        p=store.create('Legacy','Pregunta');legacy=Path(os.environ['BINARIO_RESEARCH_STUDIO_HOME'])/p['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'source-old.txt').write_text('preservar',encoding='utf-8');target=store.project_dir(p['id']);self.assertTrue((target/'source-old.txt').is_file());self.assertTrue((legacy/'source-old.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
if __name__=='__main__':unittest.main()
