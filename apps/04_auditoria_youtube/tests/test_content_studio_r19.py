import os,sys,tempfile,unittest
from pathlib import Path
APP=Path(__file__).resolve().parents[1];ROOT=APP.parents[1];sys.path.insert(0,str(ROOT));sys.path.insert(0,str(APP))
from youtube_studio import store,content
class YouTubeStudioR19(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_YOUTUBE_STUDIO_HOME','BINARIO_PROJECTS_HOME']};os.environ['BINARIO_YOUTUBE_STUDIO_HOME']=str(Path(self.t.name)/'legacy');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.t.name)/'projects');self.p=store.create('Demo');self.p['profile'].update({'channel_name':'Canal Demo','positioning':'IA práctica','audience':'Pymes','offer':'Consultoría','posts_per_week':3});store.save(self.p)
 def tearDown(self):
  for k,v in self.old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.t.cleanup()
 def seed(self):
  content.add_item(self.p,{'title':'Cómo usar IA en ventas','text':'Tres pasos concretos para mejorar ventas. Comenta tu caso.','metrics':{'views':1000,'likes':80,'comments':20}});content.add_item(self.p,{'title':'Errores al automatizar','text':'Errores comunes de automatización y cómo corregirlos.'})
 def test_01_persistent(self):self.assertTrue(store.get(self.p['id']))
 def test_02_hash(self):self.assertEqual(len(content.add_item(self.p,{'title':'A','text':'B'})['sha256']),64)
 def test_03_analysis_observed_metrics(self):self.seed();a=content.analyze(self.p);self.assertTrue(a['pillars']);self.assertEqual(a['items'][0]['analysis']['engagement_pct_observed'],10.0);self.assertIsNone(a['items'][0]['analysis']['retention_pct_observed'])
 def test_04_calendar(self):self.seed();content.analyze(self.p);self.assertGreaterEqual(len(content.build_calendar(self.p,30,3)),3)
 def test_05_ready_after_review(self):self.seed();content.analyze(self.p);content.build_calendar(self.p,30,3);content.review(self.p,'OK');self.assertTrue(content.readiness(self.p)['ready'])
 def test_06_experiment(self):self.assertEqual(content.add_experiment(self.p,{'name':'Hook A/B','hypothesis':'Pregunta mejora CTR'})['status'],'planned')
 def test_07_performance(self):self.assertEqual(content.log_performance(self.p,{'metrics':{'views':200}})['metrics']['views'],200)
 def test_08_handoff(self):self.assertTrue(content.handoff(self.p,'video')['payload']['human_approval_required'])
 def test_09_export(self):self.seed();content.analyze(self.p);content.build_calendar(self.p,30,3);content.review(self.p,'OK');self.assertTrue(Path(content.export(self.p)['zip']).is_file())
 def test_10_snapshot(self):self.assertTrue(Path(store.snapshot(self.p['id'],'manual')['path']).is_file())
 def test_11_state_and_exports_live_inside_canonical_project(self):
  from common import project_center
  row=project_center.get(self.p['id']);root=Path(row['metadata']['project_path']).resolve();state=store.pdir(self.p['id']).resolve();exports=store.export_dir(self.p['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/04-auditoria-youtube',state.as_posix());self.assertIn('exports/04-auditoria-youtube',exports.as_posix())
 def test_12_legacy_state_is_copied_not_deleted(self):
  legacy=Path(os.environ['BINARIO_YOUTUBE_STUDIO_HOME'])/self.p['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'legacy-note.txt').write_text('preservar',encoding='utf-8');target=store.pdir(self.p['id']);self.assertTrue((target/'legacy-note.txt').is_file());self.assertTrue((legacy/'legacy-note.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
if __name__=='__main__':unittest.main()
