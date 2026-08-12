import os,tempfile,unittest
from pathlib import Path
from kit_studio import store,builder
class KitStudioR16Test(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_KIT_STUDIO_HOME','BINARIO_PROJECTS_HOME','BINARIO_STATE_HOME']};os.environ['BINARIO_KIT_STUDIO_HOME']=str(Path(self.t.name)/'legacy');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.t.name)/'projects');os.environ['BINARIO_STATE_HOME']=str(Path(self.t.name)/'state')
    def tearDown(self):
        for k,v in self.old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
        self.t.cleanup()
    def test_build_validate_package(self):
        p=store.create('Kit Demo','Resolver prueba');p['spec']={'inputs':['objetivo'],'outputs':['resultado.json'],'skills':['intake','analysis','quality']};store.save(p);b=builder.materialize(p);self.assertTrue(Path(b['kit_dir']).is_dir());v=builder.validate(p);self.assertTrue(v['passed'],v);z=builder.package(p);self.assertTrue(Path(z['zip']).is_file());self.assertTrue(Path(z['handoff']).is_file())
    def test_validation_blocks_missing_build(self):
        p=store.create('Vacío','x');v=builder.validate(p);self.assertFalse(v['passed'])
    def test_state_build_and_exports_live_inside_canonical_project(self):
        from common import project_center
        p=store.create('Canonical','x');row=project_center.get(p['id']);root=Path(row['metadata']['project_path']).resolve();state=store.pdir(p['id']).resolve();exports=store.export_dir(p['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/08-creador-kits',state.as_posix());self.assertIn('exports/08-creador-kits',exports.as_posix());b=builder.materialize(p);self.assertTrue(state in Path(b['kit_dir']).resolve().parents);z=builder.package(p);self.assertTrue(exports in Path(z['zip']).resolve().parents)
    def test_legacy_state_is_copied_not_deleted(self):
        p=store.create('Legacy','x');legacy=Path(os.environ['BINARIO_KIT_STUDIO_HOME'])/p['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'legacy-note.txt').write_text('preservar',encoding='utf-8');target=store.pdir(p['id']);self.assertTrue((target/'legacy-note.txt').is_file());self.assertTrue((legacy/'legacy-note.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
