"""Non-sensitive Intel Exporter -> SQLite -> existing CUDA service regression."""
import json,os,sys,subprocess,random,time,hashlib
from pathlib import Path
from uuid import uuid4
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.services.ids_import_service import IdsImportService
from ivad_app.services.wpf_rf_service import WpfRFService
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
os.environ['IVAD_IDS_CONTROLLED_ROOT']=str(out.parent)
source=out/'source';(source/'assets').mkdir(parents=True)
entities=[];assets=[]
def add(kind,data):
 e=dict(id=str(uuid4()),kind=kind,revision=1,data=data);entities.append(e);return e['id']
def asset(p):
 assets.append(dict(path=p.relative_to(source).as_posix(),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()));return assets[-1]['path']
site=add('Site',{'name':'synthetic'});project=add('Project',{'name':'CUDA IDS fixture','site_id':site});eq=add('Equipment',{'name':'synthetic','project_id':project});fault=add('Fault',{'name':'fixture rectangle','taxonomy_version':1})
for group in range(2):
 cam=add('Camera',{'name':'fixture camera '+str(group),'equipment_id':eq})
 p=source/'assets'/('video-'+str(group)+'.bin');p.write_bytes(b'synthetic video identity '+bytes([group]));video=add('Video',{'camera_id':cam,'asset_path':asset(p),'original_name':p.name})
 rng=random.Random(582+group)
 for i in range(4):
  image=Image.frombytes('RGB',(384,384),rng.randbytes(384*384*3));ImageDraw.Draw(image).rectangle((32,40,120,140),fill=(220,40,20))
  p=source/'assets'/f'{group}-{i}.png';image.save(p)
  f=add('Frame',dict(video_id=video,asset_path=asset(p),width=384,height=384,pts_us=i*1000000,source_timestamp_100ns=i*10000000,time_source='media_foundation_sample',state='normal' if i==3 else 'abnormal'))
  if i!=3:add('Annotation',dict(frame_id=f,fault_id=fault,shape='box',points=[32,40,120,140],coordinate_space='source_pixels'))
  add('Review',dict(frame_id=f,status='confirmed',reviewer='synthetic'))
doc=dict(schema='ids/1.0',project_id=project,sequence=1,entities=entities,assets=assets)
(source/'project.ids.json').write_text(json.dumps(doc),encoding='utf8')
exe=ROOT/'wpf_intel/build/rf-gate/Ivad.Annotator.Dev.exe';env=dict(os.environ);env.pop('IVAD_NVIDIA_BRIDGE',None)
subprocess.run([str(exe),'--ids-export',str(source),str(out/'fixture.ids')],env=env,check=True)
IdsImportService(exe).import_package(out/'fixture.ids',out/'project')
service=WpfRFService(ROOT,out)
try:
 r=service.execute(dict(action='train',root=str(out/'project'),epochs=1));(out/'job.json').write_text(json.dumps(r));print('CUDA job submitted',flush=True)
 deadline=time.monotonic()+600
 while time.monotonic()<deadline:
  status=service.execute(dict(action='job',root=str(out/'project'),job_id=r['job_id']))
  if status['state'] in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:break
  time.sleep(1)
 else:service.execute(dict(action='cancel',root=str(out/'project'),job_id=r['job_id']));raise TimeoutError('CUDA fixture timeout')
 (out/'result.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'state':status['state'],'error':status.get('error')}),flush=True)
 assert status['state']=='SUCCEEDED'
finally:service.close()
