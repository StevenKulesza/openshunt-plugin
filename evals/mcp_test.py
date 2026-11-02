#!/usr/bin/env python3
"""Offline MCP process integration tests using a mock company adapter."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SERVER = Path(__file__).resolve().parents[1] / 'scripts/shunt-mcp'

class MCPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.root = self.base / 'workspace'
        self.root.mkdir()
        (self.root / 'sample.py').write_text('print("héllo")\n')
        (self.base / 'outside').write_text('secret')
        (self.root / 'escape').symlink_to(self.base / 'outside')
        self.adapter = self.base / 'adapter'
        self.adapter.write_text('#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"text": r["task"]+":"+r["model"]}))\n')
        self.adapter.chmod(0o700)
        self.env = dict(os.environ, SHUNT_PROVIDER='custom', SHUNT_ADAPTER=str(self.adapter), SHUNT_READER_MODEL='reader-test', SHUNT_WRITER_MODEL='writer-test')

    def tearDown(self):
        self.temp.cleanup()

    def run_messages(self, messages, initialize=True):
        if initialize:
            messages = [{'jsonrpc': '2.0', 'id': 0, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}}, {'jsonrpc': '2.0', 'method': 'notifications/initialized'}] + messages
        process = subprocess.run(['python3', str(SERVER), '--workspace', str(self.root)], input=''.join(m if isinstance(m,str) else json.dumps(m)+'\n' for m in messages), text=True, capture_output=True, env=self.env, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        responses = [json.loads(line) for line in process.stdout.splitlines()]
        return responses[1:] if initialize else responses

    def call(self, name, args):
        return self.run_messages([{'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':name,'arguments':args}}])[0]

    def test_initialize_discovery(self):
        replies = self.run_messages([{'jsonrpc':'2.0','id':1,'method':'tools/list'}])
        self.assertEqual([t['name'] for t in replies[0]['result']['tools']], ['bulk_read','code_write'])

    def test_reader(self):
        reply = self.call('bulk_read', {'question':'Summarize', 'paths':['sample.py']})
        self.assertFalse(reply['result']['isError'])
        self.assertIn('bulk-reader:reader-test', reply['result']['content'][0]['text'])

    def test_writer_output_only(self):
        reply = self.call('code_write', {'spec':'Generate', 'reference':'sample.py'})
        self.assertIn('code-writer:writer-test',reply['result']['content'][0]['text'])
        self.assertEqual((self.root/'sample.py').read_text(),'print("héllo")\n')
        self.assertTrue(self.call('code_write', {'spec':'Generate','reference':'sample.py','target':'sample.py'})['result']['isError'])

    def test_escape(self):
        for path in ['../outside', str(self.base/'outside'), 'escape']:
            self.assertTrue(self.call('bulk_read',{'question':'Read', 'paths':[path]})['result']['isError'])

    def test_bad_args(self):
        for args in [{},[],{'question':'Read','paths':[]},{'question':True,'paths':['sample.py']},{'question':'Read','paths':[1]}]:
            self.assertTrue(self.call('bulk_read',args)['result']['isError'])

    def test_adapter_failure(self):
        self.adapter.write_text('#!/bin/sh\necho SECRET >&2\nexit 1\n')
        reply = self.call('bulk_read',{'question':'Read','paths':['sample.py']})
        self.assertTrue(reply['result']['isError'])
        self.assertNotIn('SECRET', json.dumps(reply))

    def test_protocol_errors(self):
        replies = self.run_messages(['invalid\n',{'jsonrpc':'2.0','id':2,'method':'unknown'},{'jsonrpc':'2.0','id':True,'method':'ping'},{'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'bad'}},{'jsonrpc':'2.0','id':4,'method':'tools/call','params':{'name':[]}}])
        self.assertEqual([r['error']['code'] for r in replies],[-32700,-32601,-32600,-32602,-32602])

    def test_symlink_loop(self):
        (self.root / 'loop').symlink_to(self.root / 'loop')
        self.assertTrue(self.call('bulk_read', {'question':'Read','paths':['loop']})['result']['isError'])

    def test_invalid_utf8(self):
        p=subprocess.run(['python3',str(SERVER),'--workspace',str(self.root)],input=b'\xff\n',capture_output=True,env=self.env,timeout=10)
        self.assertEqual(p.returncode,0)
        self.assertEqual(json.loads(p.stdout)['error']['code'],-32700)

    def test_notifications_and_ping(self):
        replies=self.run_messages([{'jsonrpc':'2.0','method':'notifications/cancelled','params':{'requestId':5}},{'jsonrpc':'2.0','id':'ping','method':'ping'}])
        self.assertEqual(len(replies),1)
        self.assertEqual(replies[0]['result'],{})

    def test_initialize_first(self):
        reply=self.run_messages([{'jsonrpc':'2.0','id':1,'method':'tools/list'}],False)[0]
        self.assertEqual(reply['error']['code'],-32000)

if __name__ == '__main__':
    unittest.main(verbosity=2)
