import pathlib,sys,unittest,os,tempfile
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'examples/harness'))
from routing import run_harness,route_result,DelegationFailed
try:
 from langgraph_example import build_graph
except ModuleNotFoundError:
 build_graph=None
RAW='SECRET_RAW_SENTINEL\n'*1000
class HarnessTests(unittest.TestCase):
 def test_harness_isolation(self):
  result=run_harness('question',lambda:RAW,delegate=lambda q,r:'compact')
  self.assertNotIn('SECRET_RAW_SENTINEL',str(result));self.assertIn('compact',str(result))
 def test_policy_types(self):
  for kwargs in ({'exact':'false'},{'threshold':True},{'max_summary':0}):
   with self.assertRaises(ValueError):route_result('q',RAW,**kwargs)
 def test_real_transport_mock_adapter(self):
  with tempfile.TemporaryDirectory() as directory:
   adapter=pathlib.Path(directory)/'adapter'
   adapter.write_text('#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nassert r["task"]=="bulk-reader"\nprint(json.dumps({"text":"compact via adapter"}))\n')
   adapter.chmod(0o700)
   with patch.dict(os.environ,{'SHUNT_PROVIDER':'custom','SHUNT_ADAPTER':str(adapter),'SHUNT_READER_MODEL':'mock-reader'}):
    self.assertIn('compact via adapter',str(run_harness('q',lambda:RAW)))
 def test_exact(self):
  self.assertEqual(route_result('q',RAW,exact=True,delegate=lambda *a: self.fail()),RAW)
 def test_small(self):
  self.assertEqual(route_result('q','small',delegate=lambda *a:self.fail()),'small')
 def test_failure(self):
  for answer in ('',RAW,None):
   with self.assertRaises(DelegationFailed):run_harness('q',lambda:RAW,delegate=lambda *a:answer)
  def fail(*args):raise RuntimeError(RAW)
  with self.assertRaises(DelegationFailed) as error:run_harness('q',lambda:RAW,delegate=fail)
  self.assertNotIn('SECRET_RAW',str(error.exception))
 @unittest.skipIf(build_graph is None,'optional langgraph not installed')
 def test_graph_updates_and_state(self):
  graph=build_graph(lambda:RAW,lambda q,r:'compact')
  initial={'question':'q','exact':False,'messages':[]}
  self.assertNotIn('SECRET_RAW',str(list(graph.stream(initial,stream_mode='updates'))))
  self.assertIn('compact',str(graph.invoke(initial)))
 @unittest.skipIf(build_graph is None,'optional langgraph not installed')
 def test_graph_exact(self):
  graph=build_graph(lambda:'exact lines',lambda *a:self.fail())
  self.assertIn('exact lines',str(graph.invoke({'question':'q','exact':True,'messages':[]})))
 @unittest.skipIf(build_graph is None,'optional langgraph not installed')
 def test_graph_failure(self):
  graph=build_graph(lambda:RAW,lambda *a:'')
  with self.assertRaises(DelegationFailed):graph.invoke({'question':'q','exact':False,'messages':[]})
if __name__=='__main__':unittest.main(verbosity=2)
