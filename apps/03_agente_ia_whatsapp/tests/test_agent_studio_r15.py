from __future__ import annotations
import json, os, tempfile, unittest
from pathlib import Path
class AgentStudioR15Tests(unittest.TestCase):
    def setUp(self):
        self.td=tempfile.TemporaryDirectory(prefix='agent-r15-');self.old={k:os.environ.get(k) for k in ['BINARIO_AGENT_STUDIO_HOME','BINARIO_PROJECTS_HOME','BINARIO_STATE_HOME']}
        os.environ['BINARIO_AGENT_STUDIO_HOME']=str(Path(self.td.name)/'agents');os.environ['BINARIO_PROJECTS_HOME']=str(Path(self.td.name)/'projects');os.environ['BINARIO_STATE_HOME']=str(Path(self.td.name)/'state')
    def tearDown(self):
        for k,v in self.old.items():
            if v is None:os.environ.pop(k,None)
            else:os.environ[k]=v
        self.td.cleanup()
    def project(self):
        from agent_studio.store import default_project
        p=default_project('Demo','Demo');p['knowledge']=[{'id':'kb1','title':'Horario','question':'Cuál es el horario','answer':'Lunes a viernes 8 a 5','enabled':True}];return p
    def test_project_persists_and_registers_global(self):
        from agent_studio.store import default_project,get
        from common.project_center import get as global_get
        p=default_project('Agente','Negocio');self.assertEqual(get(p['id'])['name'],'Agente');self.assertEqual(global_get(p['id'])['app_id'],'03-agente-ia-whatsapp')
    def test_default_flow_has_router_and_handoff(self):
        p=self.project();ids={x['id'] for x in p['flow']['nodes']};self.assertIn('router',ids);self.assertIn('handoff',ids)
    def test_faq_knowledge_answer(self):
        from agent_studio.simulator import simulate
        r=simulate(self.project(),'cuál es el horario');self.assertEqual(r['source'],'knowledge');self.assertIn('8 a 5',r['assistant'])
    def test_human_intent_handoffs(self):
        from agent_studio.simulator import simulate
        r=simulate(self.project(),'quiero hablar con un asesor humano');self.assertTrue(r['handoff']);self.assertEqual(r['intent'],'human')
    def test_price_guardrail_does_not_invent(self):
        from agent_studio.simulator import simulate
        r=simulate(self.project(),'cuál es el precio');self.assertTrue(r['handoff']);self.assertIn('No voy a inventar',r['assistant'])
    def test_private_route_stays_local(self):
        from agent_studio.simulator import simulate
        p=self.project();p['model']['profile']='private';r=simulate(p,'hola');self.assertIn(r['route']['provider'],{'local','openai-compatible'})
    def test_execution_mode_is_truthful(self):
        from agent_studio.simulator import simulate
        r=simulate(self.project(),'hola');self.assertEqual(r['execution_mode'],'deterministic-local-sandbox')
    def test_readiness_requires_simulation_and_tests(self):
        from agent_studio.exporter import readiness
        p=self.project();r=readiness(p);self.assertFalse(r['ready']);p['tests']['last_simulation']={'ok':1};p['tests']['last_run']={'passed':True};self.assertTrue(readiness(p)['ready'])
    def test_flowbot_export_contains_intents_variables_guardrails(self):
        from agent_studio.exporter import flowbot
        f=flowbot(self.project());self.assertEqual(f['schema'],'sbia-flowbot-2.0');self.assertGreaterEqual(len(f['intents']),4);self.assertTrue(f['guardrails'])
    def test_export_creates_zip(self):
        from agent_studio.exporter import export
        p=self.project();p['tests']['last_simulation']={'ok':1};p['tests']['last_run']={'passed':True};r=export(p);self.assertTrue(Path(r['zip']).exists());self.assertTrue(Path(r['flowbot']).exists())
    def test_snapshot_and_activity(self):
        from agent_studio.store import default_project,snapshot,log_event,activity
        p=default_project('X','X');s=snapshot(p['id'],'test');self.assertTrue(Path(s['path']).exists());log_event(p['id'],'demo',{'x':1});self.assertEqual(activity(p['id'])[-1]['event'],'demo')
    def test_training_csv_import_becomes_approved_faq(self):
        from agent_studio.store import default_project,get
        from agent_studio.service import import_training_into_project
        p=default_project('Train','Train');r=import_training_into_project(p,'faq.csv',b'question,answer,tags,priority\nHorario?,Lunes a viernes,horario,normal\n');saved=get(p['id']);self.assertEqual(r['added']['qa'],1);self.assertEqual(saved['knowledge'][-1]['answer'],'Lunes a viernes');self.assertTrue(saved['knowledge'][-1]['enabled']);self.assertTrue(Path(r['training']['path']).exists())
    def test_training_document_requires_approval_then_can_answer(self):
        from agent_studio.store import default_project,get,save
        from agent_studio.service import import_training_into_project
        from agent_studio.simulator import simulate
        p=default_project('Docs','Docs');r=import_training_into_project(p,'manual.txt','La garantía dura doce meses.'.encode());saved=get(p['id']);self.assertEqual(r['added']['document_chunks'],1);self.assertFalse(saved['knowledge_documents'][0]['enabled']);saved['knowledge_documents'][0]['enabled']=True;save(saved);answer=simulate(saved,'garantía');self.assertEqual(answer['source'],'knowledge');self.assertIn('doce meses',answer['assistant'])
    def test_manifest_is_service_and_has_journey(self):
        d=json.loads((Path(__file__).resolve().parents[1]/'manifest.json').read_text());self.assertEqual(d['engine_type'],'service');self.assertEqual(d['special_service']['port'],8785);self.assertIn('observe',d['journey'])
if __name__=='__main__':unittest.main()
