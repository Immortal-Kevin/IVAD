"""Windows workspace boundary and SID-based policy for the WPF bridge.

This protects against other Windows accounts, not code running as the owner.
Policy creation is explicit and only allowed in a new empty workspace.
"""
import base64
import json
import os
from pathlib import Path
import re
import subprocess

POLICY='.ivad-access.json'

def powershell(script):
    script="$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"+script
    encoded=base64.b64encode(script.encode('utf-16le')).decode('ascii')
    env={k:v for k,v in os.environ.items() if k.upper()!='PSMODULEPATH'}
    ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    env['PSModulePath']=str(ps.parent/'Modules')
    p=subprocess.run([str(ps),'-NoProfile','-NonInteractive','-EncodedCommand',encoded],
        capture_output=True,text=True,encoding='utf8',errors='replace',timeout=30,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    if p.returncode:raise PermissionError('WINDOWS_SECURITY_CHECK_FAILED: '+redact(p.stderr)[:500])
    return p.stdout.strip()

def literal(path):return "'"+str(path).replace("'","''")+"'"

def sid():
    return powershell('[Security.Principal.WindowsIdentity]::GetCurrent().User.Value')

def acl(path):
    raw=powershell("[Console]::OutputEncoding=[Text.Encoding]::UTF8;$a=Get-Acl -LiteralPath "+literal(path)+";@{owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|%{@{sid=$_.IdentityReference.Value;type=$_.AccessControlType.ToString();rights=[int]$_.FileSystemRights}})}|ConvertTo-Json -Compress -Depth 4")
    return json.loads(raw.lstrip('\ufeff'))

def check_acl(path,owner):
    check_acls([path],owner)


def check_acls(paths,owner):
    allowed={owner,'S-1-5-18','S-1-5-32-544'}
    raw=powershell('@('+','.join(literal(p) for p in dict.fromkeys(paths))+')|%{$a=Get-Acl -LiteralPath $_;@{owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;rules=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])|%{@{sid=$_.IdentityReference.Value;type=$_.AccessControlType.ToString();rights=[int]$_.FileSystemRights}})}}|ConvertTo-Json -Compress -Depth 4')
    records=json.loads(raw.lstrip('\ufeff'))
    for info in records if isinstance(records,list) else [records]:
        if info['owner'] not in allowed:raise PermissionError('UNTRUSTED_DATA_OWNER')
        if any(r['type']=='Allow' and r['rights'] and r['sid'] not in allowed for r in info['rules']):
            raise PermissionError('DATA_ACL_EXPOSED')

def initialize(path):
    path=Path(path).resolve()
    if path.exists() and any(path.iterdir()):raise PermissionError('INITIALIZE_REQUIRES_EMPTY_WORKSPACE')
    path.mkdir(parents=True,exist_ok=True);owner=sid()
    def icacls(*args):
        p=subprocess.run(['icacls.exe',str(path),*args],capture_output=True,timeout=30)
        if p.returncode:raise PermissionError('WORKSPACE_ACL_INITIALIZATION_FAILED')
    icacls('/grant:r',f'*{owner}:(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F')
    icacls('/inheritance:r')
    for entry in acl(path)['rules']:
        if entry['sid'] not in {owner,'S-1-5-18','S-1-5-32-544'}:
            icacls('/remove','*'+entry['sid'])
    value={'version':1,'owner_sid':owner,'roles':{owner:'administrator'},'allow_export':False,
        'exports_directory':'exports','classification':'controlled-private'}
    (path/POLICY).write_text(json.dumps(value,indent=2),encoding='utf8');check_acl(path,owner)
    return value

def authorize(root,action,destination=None):
    boundary=Path(os.environ['IVAD_IDS_CONTROLLED_ROOT']).resolve();root=Path(root).resolve()
    if root==boundary or not root.is_relative_to(boundary):raise PermissionError('DATA_SCOPE_DENIED')
    policy_path=boundary/POLICY
    if not policy_path.is_file():raise PermissionError('WORKSPACE_POLICY_REQUIRED')
    current=sid();check_acls([boundary,policy_path],current)
    policy=json.loads(policy_path.read_text(encoding='utf8'))
    if policy.get('version')!=1 or policy.get('owner_sid')!=current:raise PermissionError('WORKSPACE_OWNER_MISMATCH')
    paths=[p for p in (root,*root.parents) if p.is_relative_to(boundary) and p.exists()]
    for name in ('wpf-runtime','wpf-runtime/catalog.sqlite','wpf-runtime/catalog.sqlite-wal','wpf-runtime/catalog.sqlite-shm','wpf-runtime/logs'):
        child=boundary/name
        if child.exists():
            if not child.resolve().is_relative_to(boundary):raise PermissionError('DATA_LINK_ESCAPE')
            paths.append(child)
    for folder in ('models','training','assets','inference','datasets','project.sqlite','project.sqlite-wal','project.sqlite-shm','project.json','project.ids.json'):
        child=root/folder
        if child.exists():
            if not child.resolve().is_relative_to(root):raise PermissionError('DATA_LINK_ESCAPE')
            paths.append(child)
    if paths:check_acls(paths,current)
    role=policy.get('roles',{}).get(current,'denied')
    read={'hydrate','identity','gpu','registry','runs','job'}
    allowed=read if role=='viewer' else read|{'commit','infer','validate'} if role=='reviewer' else read|{'commit','import','infer','validate','train','cancel','export'} if role=='administrator' else set()
    if action not in allowed:raise PermissionError('ROLE_DENIED')
    if action=='export':
        if not policy.get('allow_export'):raise PermissionError('EXPORT_DISABLED_BY_POLICY')
        exports=(boundary/policy['exports_directory']).resolve();target=Path(destination).resolve()
        if not exports.is_relative_to(boundary) or not target.is_relative_to(exports):raise PermissionError('EXPORT_SCOPE_DENIED')
        check_acls([p for p in (target,*target.parents) if p.is_relative_to(boundary) and p.exists()],current)
    return {'role':role,'can_export':role=='administrator' and bool(policy.get('allow_export'))}

def redact(text):
    text=re.sub(r'(?i)(["\']?(?:password|passwd|token|api[_-]?key|secret)["\']?\s*[:=]\s*)(?:"[^"\n]*"|\'[^\'\n]*\'|[^\s,;]+)',r'\1<redacted>',str(text))
    text=re.sub(r'(?i)(?:Bearer\s+)[A-Za-z0-9._~+/-]+','Bearer <redacted>',text)
    text=re.sub(r'(?i)(?:[A-Z]:[\\/]|\\\\)[^\r\n"\']+','<private-path>',text)
    text=re.sub(r'(?i)(?:rtsp|https?)://[^\s]+','<private-url>',text)
    return text


def drain_redacted(source, target):
    """Consume a child's pipe continuously; redact before anything reaches disk."""
    try:
        for line in source:
            target.write(redact(line));target.flush()
    finally:source.close()
