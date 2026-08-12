from __future__ import annotations
import os,tempfile,unittest,sys
from pathlib import Path
APP=Path(__file__).resolve().parents[1];ROOT=APP.parents[1];sys.path[:0]=[str(ROOT),str(APP)]
from commerce_studio import store,commerce
HOME="""<html lang="es"><head><title>Tienda Acme productos naturales</title><meta name="viewport" content="width=device-width"><meta name="description" content="Tienda natural con envío y garantía"></head><body><main><h1>Tienda Acme</h1><a href="/product/cafe">Comprar café</a><p>Envío, garantía, devoluciones y pago seguro.</p></main><footer>Contacto</footer></body></html>"""
PRODUCT="""<html lang="es"><head><title>Café Acme premium de origen</title><meta name="viewport" content="width=device-width"><meta name="description" content="Café premium"></head><body><main><h1>Café premium</h1><button>Añadir al carrito</button><p>Garantía y envío nacional.</p><img src="cafe.jpg" alt="Café Acme"></main></body></html>"""
class CommerceStudioR18(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.old={k:os.environ.get(k) for k in ['BINARIO_COMMERCE_STUDIO_HOME','BINARIO_PROJECTS_HOME']};os.environ['BINARIO_COMMERCE_STUDIO_HOME']=str(Path(self.t.name)/'legacy');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.t.name)/'projects');self.pr=store.create('Acme Shop','https://shop.test/','Café')
 def tearDown(self):
  for k,v in self.old.items():
   if v is None:os.environ.pop(k,None)
   else:os.environ[k]=v
  self.t.cleanup()
 def test_full_journey(self):
  commerce.add_html(self.pr,'https://shop.test/',HOME);commerce.add_html(self.pr,'https://shop.test/product/cafe',PRODUCT);f=commerce.map_funnel(self.pr);self.assertTrue(f['stages']['home']);self.assertTrue(f['stages']['product']);a=commerce.audit(self.pr);self.assertTrue(a['legacy']);rw=commerce.rewrite_product(self.pr);self.assertIn('Café',rw['content']);commerce.review(self.pr,'OK');rd=commerce.readiness(self.pr);self.assertTrue(rd['ready']);ex=commerce.export(self.pr);self.assertTrue(Path(ex['zip']).is_file())
 def test_missing_checkout_is_explicit(self):commerce.add_html(self.pr,'https://shop.test/',HOME);f=commerce.map_funnel(self.pr);self.assertTrue(any(x['id']=='no-checkout' for x in f['leaks']))
 def test_audit_requires_pages(self):
  with self.assertRaises(RuntimeError):commerce.audit(self.pr)
 def test_state_and_exports_live_inside_canonical_project(self):
  from common import project_center
  row=project_center.get(self.pr['id']);root=Path(row['metadata']['project_path']).resolve();state=store.pdir(self.pr['id']).resolve();exports=store.export_dir(self.pr['id']).resolve();self.assertTrue(root in state.parents);self.assertTrue(root in exports.parents);self.assertIn('autosave/apps/07-auditoria-ecommerce',state.as_posix());self.assertIn('exports/07-auditoria-ecommerce',exports.as_posix())
 def test_legacy_state_is_copied_not_deleted(self):
  legacy=Path(os.environ['BINARIO_COMMERCE_STUDIO_HOME'])/self.pr['id'];legacy.mkdir(parents=True,exist_ok=True);(legacy/'legacy-note.txt').write_text('preservar',encoding='utf-8');target=store.pdir(self.pr['id']);self.assertTrue((target/'legacy-note.txt').is_file());self.assertTrue((legacy/'legacy-note.txt').is_file());self.assertTrue((target/'legacy-migration.json').is_file())
if __name__=='__main__':unittest.main()
