"""Local stdin/stdout bridge. No network, no GUI framework dependency."""
import json
import os
from pathlib import Path
import sys
import secrets
from uuid import uuid4
from .ids_import_service import state, controlled, commit_document
from .local_security import authorize,redact
rf=None


def execute(request):
    global rf
    root=controlled(request['root'])
    action=request['action']
    identity=authorize(root,action,request.get('destination'))
    if action=='identity':return json.dumps(identity)
    if action=='export':return 'authorized'
    if action=='hydrate':
        saved=state(root)
        if saved is None and (root/'project.sqlite').is_file():
            raise ValueError('LEGACY_PROJECT_REQUIRES_VALIDATED_IDS_COPY: 旧项目尚无已验证IDS投影；保留原数据库，请在副本上完成兼容转换。')
        if saved:
            if not (root/'project.json').exists():
                from ivad_app.storage.project_store import atomic_json
                doc=json.loads(saved['canonical'])
                project=next(e for e in doc['entities'] if e['id']==doc['project_id'])
                atomic_json(root/'project.json',{'format':'ivad-project','format_version':1,
                    'database':'project.sqlite','id':doc['project_id'],'name':project['data']['name']})
            cache=root/'project.ids.json'
            data=saved['canonical'].encode('utf8')
            if not cache.exists() or cache.read_bytes()!=data:
                tmp=cache.with_suffix('.'+uuid4().hex+'.tmp');tmp.write_bytes(data);os.replace(tmp,cache)
        return ''
    if action=='commit':
        file=Path(request['file']).resolve()
        if not file.is_relative_to(root):raise ValueError('IDS_COMMIT_PATH')
        result=commit_document(root,file.read_text(encoding='utf-8-sig'),request.get('expected'))
        # SQLite is authoritative. A cache write failure after commit must never
        # claim the transaction rolled back; next open rehydrates the cache.
        try:execute({'action':'hydrate','root':str(root)})
        except OSError:result['warning']='COMMITTED_CACHE_REBUILD_REQUIRED'
        return json.dumps(result)
    if action in {'gpu','registry','runs','job','cancel','train','validate','infer'}:
        if rf is None:
            from .wpf_rf_service import WpfRFService
            rf=WpfRFService(Path(__file__).resolve().parents[2],os.environ['IVAD_IDS_CONTROLLED_ROOT'])
        return json.dumps(rf.execute(request),ensure_ascii=False)
    raise ValueError('IDS_BRIDGE_ACTION')


if __name__=='__main__':
    for line in sys.stdin:
        try:
            request=json.loads(line)
            token=os.environ.get('IVAD_IPC_TOKEN','')
            if not token or request.get('protocol')!='ivad-local/1' or not secrets.compare_digest(request.get('token',''),token):
                raise ValueError('IPC_AUTHENTICATION_FAILED')
            answer={'ok':True,'result':execute(request)}
        except Exception as exc:answer={'ok':False,'error':redact(str(exc))}
        print(json.dumps(answer,ensure_ascii=True),flush=True)
    if rf is not None:rf.close()
