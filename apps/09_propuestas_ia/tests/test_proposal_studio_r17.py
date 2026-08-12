from pathlib import Path
import os,tempfile,unittest
class ProposalStudioR17(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_PROPOSAL_STUDIO_HOME','BINARIO_PROJECTS_HOME']};os.environ['BINARIO_PROPOSAL_STUDIO_HOME']=str(Path(self.t.name)/'proposal');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.t.name)/'projects');from proposal_studio import store,proposal;self.store=store;self.proposal=proposal
 def tearDown(self):
  for k,v in self.old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.t.cleanup()
 def test_full_journey(self):
  p=self.store.create('Cliente Demo','Propuesta IA');p['brief'].update({'problem':'Demoras operativas','objective':'Reducir tiempos'});p['scope']['deliverables']=['Auditoría','Piloto'];p['scope']['assumptions']=['Acceso a responsables'];p['pricing'].update({'subtotal':1000000,'discount':100000,'tax':0,'timeline':'6 semanas'});self.proposal.recalc(p);self.proposal.add_source(p,'Auditoría','Oportunidad de automatización priorizada.');d=self.proposal.generate(p);self.assertIn('#',d['markdown']);self.proposal.review(p,'Revisada');self.proposal.approve(p,'Director');rd=self.proposal.readiness(p);self.assertGreaterEqual(rd['score'],80);ds=self.proposal.document_spec(p);self.assertTrue(ds['path']);x=self.proposal.export(p);self.assertTrue(x['zip'])
 def test_approval_requires_review(self):
  p=self.store.create('Cliente','P');
  with self.assertRaises(RuntimeError):self.proposal.approve(p,'Director')
 def test_pricing(self):
  p=self.store.create('Cliente','P');p['pricing'].update({'subtotal':100,'discount':10,'tax':19});self.assertEqual(self.proposal.recalc(p)['total'],109)
 def test_state_and_exports_live_inside_canonical_project(self):
  from common import project_center
  p=self.store.create('Cliente','Canonical');row=project_center.get(p['id']);root=Path(row['metadata']['project_path']).resolve();state=self.store.pdir(p['id']).resolve();exports=self.store.export_dir(p['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/09-propuestas-ia',state.as_posix());self.assertIn('exports/09-propuestas-ia',exports.as_posix())
 def test_legacy_state_is_copied_not_deleted(self):
  p=self.store.create('Cliente','Legacy');legacy=Path(os.environ['BINARIO_PROPOSAL_STUDIO_HOME'])/p['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'legacy-note.txt').write_text('preservar',encoding='utf-8');target=self.store.pdir(p['id']);self.assertTrue((target/'legacy-note.txt').is_file());self.assertTrue((legacy/'legacy-note.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
if __name__=='__main__':unittest.main()
