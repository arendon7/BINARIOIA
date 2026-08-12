from __future__ import annotations
import os,tempfile,unittest,sys,json
from pathlib import Path
APP=Path(__file__).resolve().parents[1];ROOT=APP.parents[1];sys.path[:0]=[str(ROOT),str(APP)]
from web_studio import store,web
from common import web_intelligence as wi
HTML="""<html lang="es"><head><title>Acme soluciones para empresas</title><meta name="description" content="Soluciones confiables para empresas que quieren crecer"><meta name="viewport" content="width=device-width"></head><body><nav><a href="/servicios">Servicios</a></nav><main><h1>Crece con Acme</h1><p>Ayudamos empresas con estrategia digital y soporte. Garantía y contacto.</p><a href="/contacto">Contactar</a><img src="a.jpg" alt="Equipo Acme"></main><footer>Privacidad</footer></body></html>"""
class WebStudioR18(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_WEB_STUDIO_HOME','BINARIO_PROJECTS_HOME']};os.environ['BINARIO_WEB_STUDIO_HOME']=str(Path(self.t.name)/'legacy');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.t.name)/'projects');self.pr=store.create('Acme','https://acme.test/')
 def tearDown(self):
  for k,v in self.old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.t.cleanup()
 def test_manual_journey(self):
  row=web.add_html(self.pr,'https://acme.test/',HTML);self.assertEqual(row['page_type'],'home');a=web.analyze(self.pr);self.assertGreater(a['score'],40);web.review(self.pr,'Validado');rd=web.readiness(self.pr);self.assertTrue(rd['ready']);self.assertGreaterEqual(len(self.pr['backlog']),3);ex=web.export(self.pr);self.assertTrue(Path(ex['zip']).is_file())
 def test_parser_evidence(self):
  p=wi.parse_html(HTML,'https://acme.test/');self.assertEqual(p['h1_count'],1);self.assertEqual(p['images_alt_coverage'],1);self.assertTrue(p['ctas'])
 def test_crawl_with_injected_fetcher(self):
  pages={'https://acme.test/':HTML,'https://acme.test/servicios':'<html><title>Servicios Acme</title><meta name="viewport" content="x"><h1>Servicios</h1><a href="/">Inicio</a></html>'}
  def f(url):
   h=pages[url];return {'requested_url':url,'url':url,'status':200,'content_type':'text/html','bytes':len(h),'elapsed_ms':5,'html':h,'sha256':'a'*64}
  rows=wi.crawl('https://acme.test/',2,fetcher=f);self.assertEqual(len(rows),2)
 def test_empty_html_rejected_by_audit(self):
  with self.assertRaises(RuntimeError):web.analyze(self.pr)
 def test_state_and_exports_live_inside_canonical_project(self):
  from common import project_center
  row=project_center.get(self.pr['id']);root=Path(row['metadata']['project_path']).resolve();state=store.pdir(self.pr['id']).resolve();exports=store.export_dir(self.pr['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/02-cazador-webs',state.as_posix());self.assertIn('exports/02-cazador-webs',exports.as_posix())
 def test_legacy_state_is_copied_not_deleted(self):
  legacy=Path(os.environ['BINARIO_WEB_STUDIO_HOME'])/self.pr['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'legacy-note.txt').write_text('preservar',encoding='utf-8');target=store.pdir(self.pr['id']);self.assertTrue((target/'legacy-note.txt').is_file());self.assertTrue((legacy/'legacy-note.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
if __name__=='__main__':unittest.main()
