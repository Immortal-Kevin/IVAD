"""P3.5 offline preprocessing cache; independent from annotations and production config."""
import csv,json,shutil,subprocess,os,queue,threading,time,math
from pathlib import Path
from uuid import uuid4
from fractions import Fraction
import av
from PIL import ImageDraw,ImageFont
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.project_store import atomic_json,file_hash
from ivad_app.video.reader import FileVideoSource

class OfflineDemoService:
    def __init__(self,services):self.s=services
    def choices(self,root):
        media=self.s.media.list(root);models=[];versions={v['id']:v for v in self.s.datasets.versions(root)}
        for r in self.s.models.versions(root):
            if r.get('state')!='EXPERIMENTAL' or r.get('model') not in {'yolo11n','yolo26n'} or r.get('task')!='detect':continue
            try:
                self.s.models.verify(r['id'],root);_,snapshot=self.s.datasets.snapshot(r['dataset_version'],root)
                if r.get('class_map')!=snapshot['classes']:continue
            except (AppError,KeyError):continue
            r['dataset_display']=versions[r['dataset_version']]['name']+' v'+str(versions[r['dataset_version']]['number']);models.append(r)
        return media,models,self.s.devices.snapshot()
    def source_notice(self,mid,model,root):
        _,snap=self.s.datasets.snapshot(model['dataset_version'],root)
        rows={r['id']:r for r in self.s.media.list(root,include_inactive=True)}
        source=self.s.datasets.source_root(type('Media',(),rows[mid])(),{k:type('Media',(),v)() for k,v in rows.items()})
        trained={r.get('source_group_id',r['media_id']) for r in snap['samples']}
        return '训练来源视频回放，不是独立测试成绩' if source in trained else '未发现同UUID来源参与该版本训练；仍需人工核实重复录像，不代表独立工业验证'
    @staticmethod
    def validate_boxes(boxes,width,height,nc):
        for b in boxes:
            if len(b)!=6 or any(not math.isfinite(float(x)) for x in b):raise AppError('DEMO_OUTPUT','模型输出无效。')
            x1,y1,x2,y2,c,k=b
            if not (0<=x1<x2<=width+.01 and 0<=y1<y2<=height+.01 and 0<=c<=1 and int(k)==k and 0<=k<nc):raise AppError('DEMO_OUTPUT','检测框坐标/类别/置信度无效。')
    def run(self,context,payload):
        root=payload['root'];mid=payload['media_id'];modelid=payload['model_id'];confidence=float(payload.get('confidence',.25));iou=.45
        if not .01<=confidence<=1:raise AppError('DEMO_CONFIDENCE','置信度须为0.01–1。')
        device=self.s.devices.require_gpu(payload['device_id'])
        if not device.id.startswith('nvidia:'):raise AppError('DEMO_GPU','仅支持NVIDIA CUDA，禁止CPU回退。')
        weights,model=self.s.models.verify(modelid,root)
        if model.get('state')!='EXPERIMENTAL' or model.get('task')!='detect' or model.get('model') not in {'yolo11n','yolo26n'}:raise AppError('DEMO_MODEL','仅选择有效实验Detection模型。')
        _,snapshot=self.s.datasets.snapshot(model['dataset_version'],root)
        if model['class_map']!=snapshot['classes']:raise AppError('DEMO_CLASSES','类别映射与冻结版本不符。')
        classes=[r['name'] for r in snapshot['classes']];media=self.s.media.get(mid,root);source=FileVideoSource(Path(media['accessible_path']));start=round(float(payload.get('start',0))*1e6);end=round(float(payload.get('end',source.metadata['duration_us']/1e6))*1e6)
        if start<0 or end<=start or end>source.metadata['duration_us']:raise AppError('DEMO_RANGE','起止时间须有效且不超出视频。')
        work=Path(root)/'demos'/str(uuid4());work.mkdir(parents=True);child=None;reader=None;output=None;rows=[];started=time.perf_counter();ready=None
        if shutil.disk_usage(work).free<100*1024*1024:raise AppError('DEMO_SPACE','演示缓存空间不足100MB，请选择其他项目磁盘。')
        manifest=dict(format='ivad-offline-demo-v1',id=work.name,state='PREPROCESSING',media_id=mid,model_id=modelid,dataset_version=model['dataset_version'],model_sha256=model['sha256'],source_sha256=file_hash(Path(media['accessible_path']),context.check),parameters=dict(confidence=confidence,iou=iou,imgsz=640,start=start/1e6,end=end/1e6),source_notice=self.source_notice(mid,model,root),experimental_notice='工程实验，未完成独立工业验证；预处理回放，不是工业报警',video_metadata=source.metadata,created_at=utc_now())
        atomic_json(work/'manifest.json',manifest)
        python=Path(self.s.settings.preferences().get('worker_python') or self.s.root/'.venv-nvidia/Scripts/python.exe')
        req=dict(weights=str(weights),weights_sha256=model['sha256'],class_names=classes,confidence=confidence,iou=iou,device_uuid=device.id.removeprefix('nvidia:'));atomic_json(work/'request.json',req)
        lines=queue.Queue()
        def receive():
            try:
                for line in child.stdout:lines.put(json.loads(line))
            except Exception as exc:lines.put(exc)
            finally:lines.put(None)
        def wait_line():
            deadline=time.monotonic()+90
            while True:
                context.check()
                try:value=lines.get(timeout=.1)
                except queue.Empty:
                    if time.monotonic()>deadline:raise AppError('DEMO_TIMEOUT','GPU Worker超时，错误日志保留。')
                    continue
                if not isinstance(value,dict):raise AppError('DEMO_WORKER','GPU Worker异常退出，请查看worker-console.log。')
                return value
        try:
            with context.service.gate.acquire(device.id,context.cancel),(work/'worker-console.log').open('w',encoding='utf8') as log:
                env=dict(os.environ,CUDA_VISIBLE_DEVICES=device.id.removeprefix('nvidia:'),PYTHONUTF8='1',YOLO_OFFLINE='true',YOLO_AUTOINSTALL='false',YOLO_CONFIG_DIR=str(work/'yolo-config'))
                child=subprocess.Popen([str(python),'-I','-X','utf8',str(self.s.root/'ivad_app/compute/offline_worker.py'),str(work/'request.json')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True,encoding='utf8',env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                reader=threading.Thread(target=receive,daemon=True);reader.start();ready=wait_line()
                if not ready.get('ready'):raise AppError('DEMO_WORKER','模型未能加载。')
                output=av.open(str(work/'annotated.partial.mp4'),'w');stream=output.add_stream('libx264',rate=Fraction(source.metadata.get('nominal_fps') or '25'));stream.width=source.metadata['display_width'];stream.height=source.metadata['display_height'];stream.pix_fmt='yuv420p' if stream.width%2==stream.height%2==0 else 'yuv444p';stream.time_base=Fraction(1,1000000);stream.codec_context.time_base=Fraction(1,1000000);stream.codec_context.max_b_frames=0
                font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',max(16,round(stream.height/45)))
                first=None
                for frame in source.iter_frames(start,end):
                    context.check()
                    if frame.time_us>=end:break
                    imagepath=work/'input.png';frame.image.save(imagepath);imagehash=file_hash(imagepath)
                    child.stdin.write(json.dumps(dict(index=len(rows),image=str(imagepath)))+'\n');child.stdin.flush();prediction=wait_line();imagepath.unlink(missing_ok=True)
                    if prediction.get('index')!=len(rows) or prediction.get('cpu_fallback') is not False or not prediction.get('cuda_forward_calls'):raise AppError('DEMO_OUTPUT','GPU来源证据无效。')
                    self.validate_boxes(prediction['boxes'],frame.image.width,frame.image.height,len(classes))
                    if first is None:first=frame.time_us
                    row=dict(index=len(rows),raw_pts_us=frame.pts_us,time_us=frame.time_us,cache_time_us=frame.time_us-first,image_sha256=imagehash,width=frame.image.width,height=frame.image.height,**{k:v for k,v in prediction.items() if k!='index'});rows.append(row)
                    draw=ImageDraw.Draw(frame.image)
                    for x1,y1,x2,y2,c,k in row['boxes']:
                        draw.rectangle((x1,y1,x2,y2),outline='#ff8a00',width=max(2,frame.image.width//500));draw.text((x1,max(0,y1-28)),f'{classes[int(k)]} {c:.3f}',font=font,fill='#ff8a00',stroke_width=1,stroke_fill='black')
                    rendered=av.VideoFrame.from_image(frame.image);rendered.pts=row['cache_time_us'];rendered.time_base=Fraction(1,1000000)
                    for packet in stream.encode(rendered):output.mux(packet)
                    context.progress(min(95,round((frame.time_us-start)/(end-start)*95)))
                if not rows:raise AppError('DEMO_EMPTY','指定范围未解码出有效帧。')
                for packet in stream.encode():output.mux(packet)
                output.close();output=None
                child.stdin.write('{"close":true}\n');child.stdin.flush();child.stdin.close();child.wait(timeout=15)
                if child.returncode:raise AppError('DEMO_WORKER','GPU进程退出失败。')
                context.check();self.s.models.verify(modelid,root)
                if file_hash(Path(media['accessible_path']),context.check)!=manifest['source_sha256']:raise AppError('DEMO_SOURCE','推理期间原视频发生变化，拒绝发布缓存。')
                cache=work/'annotated.mp4';(work/'annotated.partial.mp4').rename(cache);metadata=FileVideoSource.probe(cache)
                manifest.update(state='SUCCEEDED',frames=rows,classes=classes,cache_metadata=metadata,first_source_time_us=first,seconds=time.perf_counter()-started,gpu=ready['gpu'],cache_sha256=file_hash(cache),gpu_peak_bytes=max(r['gpu_peak_bytes'] for r in rows),inference_seconds=sum(r['inference_seconds'] for r in rows))
                manifest['end_to_end_fps']=len(rows)/manifest['seconds'];manifest['inference_fps']=len(rows)/manifest['inference_seconds'];self.write_csv(work/'detections.csv',manifest);context.check();atomic_json(work/'manifest.json',manifest);(work/'manifest.sha256').write_text(file_hash(work/'manifest.json'),encoding='ascii')
                return dict(path=str(work),frames=len(rows),detections=sum(len(r['boxes']) for r in rows),seconds=manifest['seconds'])
        except Exception as exc:
            manifest.update(state='CANCELLED' if context.cancel.is_set() else 'FAILED',error=str(exc));atomic_json(work/'manifest.json',manifest);raise
        finally:
            if output:output.close()
            if child and child.poll() is None:child.terminate();child.wait(timeout=15)
            if reader:reader.join(timeout=2)
            if child:
                if child.stdout:child.stdout.close()
                if child.stdin and not child.stdin.closed:child.stdin.close()
            (work/'input.png').unlink(missing_ok=True)
    @staticmethod
    def write_csv(path,m):
        with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f);writer.writerow(['media_uuid','model_uuid','dataset_version','time_seconds','raw_pts_us','class','confidence','xyxy_original','box_count','parameters'])
            for r in m['frames']:
                for b in r['boxes'] or [None]:writer.writerow([m['media_id'],m['model_id'],m['dataset_version'],r['time_us']/1e6,r['raw_pts_us'],m['classes'][int(b[5])] if b else '',b[4] if b else '',json.dumps(b[:4]) if b else '',len(r['boxes']),json.dumps(m['parameters'])])
    def load(self,path):
        folder=Path(path);m=json.loads((folder/'manifest.json').read_text(encoding='utf8'))
        seal=folder/'manifest.sha256'
        if not seal.is_file() or file_hash(folder/'manifest.json')!=seal.read_text(encoding='ascii'):raise AppError('DEMO_CACHE','演示记录缺少完成校验或已变化。')
        if m['state']!='SUCCEEDED' or file_hash(folder/'annotated.mp4')!=m['cache_sha256']:raise AppError('DEMO_CACHE','演示缓存未完成或文件哈希变化。')
        return m
    def export(self,path,parent):
        self.load(path);target=Path(parent)/('IVAD-offline-demo-'+uuid4().hex[:8]);target.mkdir()
        for name in ['annotated.mp4','manifest.json','manifest.sha256','detections.csv']:shutil.copy2(Path(path)/name,target/name)
        return str(target)
    def screenshot(self,path,parent,time_us):
        m=self.load(path);frame=FileVideoSource(Path(path)/'annotated.mp4',m['cache_metadata']).at(time_us);row=min(m['frames'],key=lambda r:abs(r['cache_time_us']-frame.time_us));target=Path(parent)/('IVAD-demo-frame-'+uuid4().hex[:8]);frame.image.save(target.with_suffix('.png'));atomic_json(target.with_suffix('.json'),dict(media_id=m['media_id'],model_id=m['model_id'],parameters=m['parameters'],frame=row));return str(target.with_suffix('.png'))
