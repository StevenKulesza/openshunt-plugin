"""Offline template launch smoke test (Python 3.11+ for TOML parsing)."""
import json,pathlib,subprocess,sys,tempfile,tomllib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ConfigTests(unittest.TestCase):
 def test_templates_launch(self):
  configs=[json.loads((ROOT/'hosts'/f).read_text())['mcpServers']['open-shunt'] for f in ('claude-code.mcp.json','cursor.mcp.json')]
  configs.append(tomllib.loads((ROOT/'hosts/codex.toml').read_text())['mcp_servers']['open-shunt'])
  for config in configs:
   with self.subTest(config=config), tempfile.TemporaryDirectory() as workspace:
    args=[a.replace('/absolute/path/to/open-shunt',str(ROOT)).replace('/absolute/path/to/your/project',workspace) for a in config['args']]
    request={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'test','version':'1'}}}
    response=subprocess.run([sys.executable,*args],input=json.dumps(request)+'\n',capture_output=True,text=True,timeout=5,check=True)
    self.assertEqual(json.loads(response.stdout)['result']['serverInfo']['name'],'open-shunt')
if __name__=='__main__': unittest.main(verbosity=2)
