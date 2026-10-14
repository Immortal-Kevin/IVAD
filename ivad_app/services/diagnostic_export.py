"""Only allowlisted diagnostics, never archive project or arbitrary system files."""
import json, os, platform, sys, zipfile, re
from pathlib import Path
from uuid import uuid4
from importlib.metadata import version, PackageNotFoundError
from ivad_app import __version__
from ivad_app.services.logging_service import redact

def sanitize(value):
    if isinstance(value,dict):return {k:sanitize(v) for k,v in value.items()}
    if isinstance(value,list):return [sanitize(v) for v in value]
    if not isinstance(value,str):return value
    value=redact(value)
    value=re.sub(r'(?i)(password|passwd|token|api[_-]?key|secret)(["\']?\s*[:=]\s*["\']?)[^"\'\s,;]+',r'\1\2<redacted>',value)
    value=re.sub(r'(?i)bearer\s+[^\s,;]+','Bearer <redacted>',value)
    value=re.sub(r'(?i)https?://[^\s/@]+:[^\s/@]+@','<credential-url>',value)
    return value

def export_diagnostics(services, output):
    output=Path(output)
    if output.suffix.lower()!='.zip': output=output.with_suffix('.zip')
    libraries={}
    for name in ['PySide6','av','SQLAlchemy','alembic','Pillow','numpy','PyYAML']:
        try: libraries[name]=version(name)
        except PackageNotFoundError: libraries[name]='METADATA NOT AVAILABLE'
    hardware=[]
    for device in services.devices.snapshot():
        details=device.details
        hardware.append({'name':device.name,'hardware_detected':device.hardware_detected,'driver':details.get('driver'),'memory_mib':details.get('total_mib'),'compute_capability':details.get('compute_capability','NOT TESTED'),'backend_available':device.backend_available,'backend_validated':device.backend_validated,'status':device.status,'worker_installed':False if services.lite else None})
    errors=[{k:r[k] for k in ('timestamp','level','category','message','trace')} for r in services.logs.recent() if r['level'] in ('ERROR','WARNING')]
    jobs=[{'kind':r['kind'],'state':r['state'],'error':r['error']} for r in services.jobs.history()[:50] if r['state'] in ('FAILED','CANCELLED','INTERRUPTED')]
    report={'environment.json':{'ivad':__version__,'mode':'P2 Lite Beta' if services.lite else 'Development','windows':platform.platform(),'python':platform.python_version(),'frozen':bool(getattr(sys,'frozen',False)),'libraries':libraries,'ai_test_status':'NOT TESTED'},'hardware.json':hardware,'errors.json':{'errors':errors,'video_task_failures':jobs},'manifest.json':{'privacy':'No video, frames, project databases, configuration secrets or arbitrary file copies. No automatic upload.','entries':['environment.json','hardware.json','errors.json','manifest.json']}}
    temp=output.with_name('.ivad-diagnostics-'+uuid4().hex+'.tmp')
    try:
        with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as z:
            for name,data in report.items():z.writestr(name,json.dumps(sanitize(data),ensure_ascii=False,indent=2))
        os.replace(temp,output)
    finally:
        if temp.exists():temp.unlink()
    return {'status':'SUCCEEDED','files':list(report),'path':str(output)}
