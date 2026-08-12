import os,tempfile,unittest
from pathlib import Path

class AppFactoryR27StorageTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory(prefix="factory-r27-")
        self.old={k:os.environ.get(k) for k in ["BINARIO_APP_FACTORY_DATA_ROOT","BINARIO_APP_FACTORY_WORKSPACE_ROOT","BINARIO_PROJECTS_HOME"]}
        os.environ["BINARIO_APP_FACTORY_DATA_ROOT"]=str(Path(self.t.name)/"global-factory")
        os.environ["BINARIO_PROJECTS_HOME"]=str(Path(self.t.name)/"projects")
        os.environ.pop("BINARIO_APP_FACTORY_WORKSPACE_ROOT",None)
    def tearDown(self):
        for k,v in self.old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
        self.t.cleanup()
    def test_global_factory_state_is_not_inside_projects(self):
        from app_factory_ia.service import default_data_root
        root=default_data_root().resolve();projects=Path(os.environ["BINARIO_PROJECTS_HOME"]).resolve()
        self.assertNotEqual(root,projects);self.assertNotIn(projects,root.parents)
    def test_generated_app_workspace_is_visible_under_projects(self):
        from app_factory_ia.service import default_workspace_root
        projects=Path(os.environ["BINARIO_PROJECTS_HOME"]).resolve();ws=default_workspace_root().resolve()
        self.assertEqual(ws,projects/"_App Factory")
    def test_prepare_runtime_separates_global_state_and_user_workspace(self):
        from app_factory_ia.service import prepare_runtime
        factory=Path(self.t.name)/"factory";(factory/"config").mkdir(parents=True);(factory/"config/projects-registry.json").write_text('{"schemaVersion":1,"projects":[]}')
        (factory/"workspace").mkdir();(factory/".sb-state").mkdir()
        info=prepare_runtime(factory)
        self.assertTrue((factory/"workspace").is_symlink());self.assertEqual(Path(info["workspace"]).resolve(),Path(os.environ["BINARIO_PROJECTS_HOME"]).resolve()/"_App Factory")
        self.assertTrue((factory/"config/projects-registry.json").is_symlink());self.assertIn("global-factory",info["registry"])
