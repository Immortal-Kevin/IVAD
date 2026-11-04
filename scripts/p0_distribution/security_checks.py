import json,os,sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ivad_app.services.local_security import initialize,authorize,sid,redact,powershell,literal,POLICY
class SecurityTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.root=pathlib.Path(sys.argv[1]);cls.policy=initialize(cls.root);os.environ['IVAD_IDS_CONTROLLED_ROOT']=str(cls.root);cls.project=cls.root/'project';cls.project.mkdir()
 def test_1_private_acl(self):self.assertEqual(authorize(self.project,'identity')['role'],'administrator')
 def test_2_export_denied(self):
  with self.assertRaisesRegex(PermissionError,'EXPORT_DISABLED'):authorize(self.project,'export',self.root/'exports/a.ids')
 def test_3_role_not_display_name(self):
  p=dict(self.policy,roles={sid():'viewer'});(self.root/POLICY).write_text(json.dumps(p))
  try:
   with self.assertRaisesRegex(PermissionError,'ROLE_DENIED'):authorize(self.project,'commit')
  finally:(self.root/POLICY).write_text(json.dumps(self.policy))
 def test_4_export_scope(self):
  (self.root/POLICY).write_text(json.dumps(dict(self.policy,allow_export=True)))
  try:
   authorize(self.project,'export',self.root/'exports/a.ids')
   with self.assertRaisesRegex(PermissionError,'EXPORT_SCOPE'):authorize(self.project,'export',self.root.parent/'a.ids')
  finally:(self.root/POLICY).write_text(json.dumps(self.policy))
 def test_5_acl_exposure(self):
  powershell('$p='+literal(self.project)+';icacls $p /grant "*S-1-1-0:(R)" | Out-Null')
  try:
   with self.assertRaisesRegex(PermissionError,'ACL_EXPOSED'):authorize(self.project,'identity')
  finally:powershell('$p='+literal(self.project)+';icacls $p /remove:g "*S-1-1-0" | Out-Null')
 def test_6_redaction(self):
  value=redact('"token": "private secret" Bearer abc.def \\\\server\\private\\video.mp4')
  for secret in ['private secret','abc.def','server']:self.assertNotIn(secret,value)
 def test_7_database_acl(self):
  path=self.project/'project.sqlite';path.write_bytes(b'ACL fixture, not a database')
  powershell('$p='+literal(path)+';icacls $p /grant "*S-1-1-0:(R)" | Out-Null')
  try:
   with self.assertRaisesRegex(PermissionError,'ACL_EXPOSED'):authorize(self.project,'identity')
  finally:path.unlink()
 def test_8_ipc_rejects_unauthenticated(self):
  import subprocess
  env=dict(os.environ,IVAD_IPC_TOKEN='test-only-non-production')
  result=subprocess.run([sys.executable,'-m','ivad_app.services.ids_bridge'],input=json.dumps({'protocol':'ivad-local/1','token':'wrong'})+'\n',text=True,capture_output=True,env=env,check=True)
  self.assertIn('IPC_AUTHENTICATION_FAILED',result.stdout)
 def test_9_worker_log_redaction_before_write(self):
  import io
  from ivad_app.services.local_security import drain_redacted
  output=io.StringIO();drain_redacted(io.StringIO('token=TOPSECRET\nC:\\secret\\weight.pth\n'),output)
  self.assertNotIn('TOPSECRET',output.getvalue());self.assertNotIn('weight.pth',output.getvalue())
 def test_catalog_acl(self):
  folder=self.root/'wpf-runtime';folder.mkdir();path=folder/'catalog.sqlite';path.write_bytes(b'ACL fixture')
  powershell('$p='+literal(path)+';icacls $p /grant "*S-1-1-0:(R)" | Out-Null')
  try:
   with self.assertRaisesRegex(PermissionError,'ACL_EXPOSED'):authorize(self.project,'identity')
  finally:path.unlink();folder.rmdir()
if __name__=='__main__':
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(SecurityTests);result=unittest.TextTestRunner(verbosity=2).run(suite);sys.exit(not result.wasSuccessful())
