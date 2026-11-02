#!/usr/bin/env python3
"""Offline transport tests: no network or credentials required."""
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('transport', ROOT / 'scripts/lib/transport.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.message = Path(self.tmp.name) / 'message'
        self.message.write_text('hello λ\n')
        self.adapter = Path(self.tmp.name) / 'adapter with spaces'
        self.adapter.write_text('#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nprint(json.dumps({"text":r["model"]+":"+r["messages"][1]["content"]}))\n')
        self.adapter.chmod(0o700)
        self.env = patch.dict(os.environ, {'SHUNT_PROVIDER':'custom', 'SHUNT_ADAPTER':str(self.adapter), 'SHUNT_READER_MODEL':'reader', 'SHUNT_WRITER_MODEL':'writer'}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
    def invoke(self, task='bulk-reader'):
        return t.invoke(task, str(self.message))
    def test_reader_unicode(self):
        self.assertEqual(self.invoke(), 'reader:hello λ\n')
    def test_writer_model(self):
        self.assertEqual(self.invoke('code-writer'), 'writer:hello λ\n')
    def test_missing_model(self):
        del os.environ['SHUNT_READER_MODEL']
        with self.assertRaises(t.TransportError): self.invoke()
    def test_size_limit(self):
        os.environ['SHUNT_MAX_PAYLOAD_BYTES']='2'
        with self.assertRaises(t.TransportError): self.invoke()
    def test_invalid_timeout(self):
        os.environ['SHUNT_TIMEOUT_SECONDS']='-1'
        with self.assertRaises(t.TransportError): self.invoke()
    def test_relative_adapter(self):
        os.environ['SHUNT_ADAPTER']='adapter'
        with self.assertRaises(t.TransportError): self.invoke()
    def test_adapter_failure(self):
        self.adapter.write_text('#!/bin/sh\necho secret >&2\nexit 2\n')
        with self.assertRaisesRegex(t.TransportError, 'exit 2'): self.invoke()
    def test_invalid_json(self):
        self.adapter.write_text('#!/bin/sh\necho nope\n')
        with self.assertRaises(ValueError): self.invoke()
    def test_empty_response(self):
        self.adapter.write_text('#!/bin/sh\necho \'{"text":""}\'\n')
        with self.assertRaises(t.TransportError): self.invoke()
    def test_timeout(self):
        os.environ['SHUNT_TIMEOUT_SECONDS']='1'
        self.adapter.write_text('#!/bin/sh\nsleep 10 &\nwait\n')
        with self.assertRaises(subprocess.TimeoutExpired): self.invoke()
    def test_cli_errors(self):
        for name, args in [('bulk-read',['--question']),('code-write',['--spec'])]:
            result=subprocess.run(['bash',str(ROOT/'scripts'/name)]+args,capture_output=True,timeout=3)
            self.assertNotEqual(result.returncode,0)
        target=Path(self.tmp.name)/'existing'
        target.write_text('preserve me')
        self.adapter.write_text('#!/bin/sh\nexit 1\n')
        result=subprocess.run(['bash',str(ROOT/'scripts/code-write'),'--spec','test','--reference',str(self.message),'--target',str(target)],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        self.assertEqual(target.read_text(),'preserve me')
    def test_http_request(self):
        os.environ.update(SHUNT_PROVIDER='openai-compatible', SHUNT_API_URL='https://company.example/chat/completions', SHUNT_API_KEY_ENV='COMPANY_KEY', COMPANY_KEY='private')
        response=io.BytesIO(b'{"choices":[{"message":{"content":"answer"}}]}')
        with patch.object(t.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value=response
            self.assertEqual(self.invoke(), 'answer')
            req=opener.return_value.open.call_args.args[0]
            self.assertEqual(req.get_header('Authorization'), 'Bearer private')
            self.assertEqual(json.loads(req.data)['model'], 'reader')
            self.assertNotIn('private', req.data.decode())
    def test_http_refuses_plaintext(self):
        os.environ.update(SHUNT_PROVIDER='openai-compatible', SHUNT_API_URL='http://example.com')
        with self.assertRaises(t.TransportError): self.invoke()
    def test_no_redirect(self):
        with self.assertRaises(t.TransportError):
            t.NoRedirect().redirect_request(None,None,302,'',{},'https://other.example')
    def test_scripts(self):
        result=subprocess.run(['bash',str(ROOT/'scripts/bulk-read'),'--question','why','--paths',str(self.message)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('Question: why',result.stdout)
        target=Path(self.tmp.name)/'generated'
        result=subprocess.run(['bash',str(ROOT/'scripts/code-write'),'--spec','test','--reference',str(self.message),'--target',str(target)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('writer:',target.read_text())
        result=subprocess.run(['bash',str(ROOT/'scripts/code-write'),'--spec','test','--reference',str(self.message),'--target',str(Path(self.tmp.name)/'absent'/'target')],capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Wrote',result.stderr)

if __name__ == '__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(TransportTests)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    failed=len(result.failures)+len(result.errors)
    print('## %d %d' % (result.testsRun-failed,failed))
    raise SystemExit(bool(failed))
