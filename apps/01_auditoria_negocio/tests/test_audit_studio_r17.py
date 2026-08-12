import os,tempfile,unittest
from pathlib import Path
class AuditStudioR17(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_AUDIT_STUDIO_HOME','BINARIO_PROJECTS_HOME']};os.environ['BINARIO_AUDIT_STUDIO_HOME']=self.t.name+'/audit';os.environ['BINARIO_PROJECTS_HOME']=self.t.name+'/projects';from audit_studio import store,audit;self.store=store;self.audit=audit
 def tearDown(self):
  for k,v in self.old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.t.cleanup()
 def test_full_journey(self):
  p=self.store.create('Empresa Demo','Operación con ventas y soporte manual');p['intake'].update({'processes':['ventas','soporte'],'pains':['demoras manuales'],'tools':['Excel','WhatsApp'],'goals':'automatizar seguimiento'});self.store.save(p);self.audit.add_evidence(p,'Entrevista','El equipo copia datos entre Excel y WhatsApp.');d=self.audit.diagnose(p);self.assertTrue(d['scores']);self.audit.review(p,'Validado');rm=self.audit.build_roadmap(p);self.assertEqual(len(rm),3);rd=self.audit.readiness(p);self.assertGreaterEqual(rd['score'],80);h=self.audit.handoff(p,'proposal');self.assertTrue(h['path']);x=self.audit.export(p);self.assertTrue(x['zip'])
 def test_empty_evidence_rejected(self):
  p=self.store.create('X','Y');
  with self.assertRaises(ValueError):self.audit.add_evidence(p,'','')
 def test_project_center_linked(self):
  p=self.store.create('Empresa','Desc');from common import project_center;self.assertEqual(project_center.get(p['id'])['app_id'],'01-auditoria-negocio')
 def test_state_and_exports_live_inside_canonical_project(self):
  from common import project_center
  p=self.store.create('Canonical','Desc');row=project_center.get(p['id']);root=Path(row['metadata']['project_path']).resolve();state=self.store.pdir(p['id']).resolve();exports=self.store.export_dir(p['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/01-auditoria-negocio',state.as_posix());self.assertIn('exports/01-auditoria-negocio',exports.as_posix())
 def test_legacy_state_is_copied_not_deleted(self):
  from common import project_center
  p=self.store.create('Legacy','Desc');legacy=Path(os.environ['BINARIO_AUDIT_STUDIO_HOME'])/p['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'legacy-note.txt').write_text('preservar',encoding='utf-8');target=self.store.pdir(p['id']);self.assertTrue((target/'legacy-note.txt').is_file());self.assertTrue((legacy/'legacy-note.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
if __name__=='__main__':unittest.main()
