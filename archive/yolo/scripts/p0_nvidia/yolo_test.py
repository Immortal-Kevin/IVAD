"""顺序执行双模型 P0；合成数据仅证明流程。"""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['YOLO_CONFIG_DIR'] = str(ROOT / 'artifacts/yolo-config')
os.environ['YOLO_AUTOINSTALL'] = 'false'
os.environ['YOLO_OFFLINE'] = 'true'
os.environ['MPLCONFIGDIR'] = str(ROOT / 'artifacts/matplotlib')
(ROOT / 'artifacts/yolo-config').mkdir(parents=True, exist_ok=True)
import json, time, hashlib, traceback, urllib.request
import faulthandler
faulthandler.enable()
faulthandler.dump_traceback_later(90, repeat=True)
import numpy as np
import torch
from PIL import Image, ImageDraw
from ultralytics import YOLO, settings
from ultralytics.models.yolo.detect import DetectionTrainer
import onnxruntime as ort

OUT = ROOT / 'artifacts/p0'
settings.update({'sync': False, 'datasets_dir': str(OUT / 'dataset'), 'weights_dir': str(OUT / 'weights'), 'runs_dir': str(OUT / 'runs')})
torch.manual_seed(123)
assert torch.cuda.is_available()
torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False

# 覆盖框架中的验证/导出路径；发现CPU神经网络前向立即失败。
def require_cuda(module, args):
    for p in module.parameters(recurse=False):
        assert p.is_cuda, f'CPU parameter in {type(module).__name__}'
    def check(v):
        if isinstance(v, torch.Tensor):
            assert v.is_cuda, f'CPU forward in {type(module).__name__}'
        elif isinstance(v, (tuple, list)):
            for item in v: check(item)
        elif isinstance(v, dict):
            for item in v.values(): check(item)
    check(args)
torch.nn.modules.module.register_module_forward_pre_hook(require_cuda)

class CudaInitTrainer(DetectionTrainer):
    def get_model(self, cfg=None, weights=None, verbose=True):
        # 框架默认在CPU做stride探测前向；在模型构造范围指定CUDA，避免CPU AI。
        with torch.device('cuda:0'):
            return super().get_model(cfg=cfg, weights=weights, verbose=verbose)
    def optimizer_step(self):
        super().optimizer_step()
        self.p0_optimizer_steps = getattr(self, 'p0_optimizer_steps', 0) + 1

def summary(values):
    return {'p50_ms': float(np.percentile(values, 50)), 'p95_ms': float(np.percentile(values, 95)), 'fps_mean': 1000 / float(np.mean(values)), 'raw_ms': values}

def timed(fn):
    for _ in range(10): fn()
    values = []
    for _ in range(50):
        torch.cuda.synchronize(); start = time.perf_counter(); fn(); torch.cuda.synchronize()
        values.append((time.perf_counter() - start) * 1000)
    return summary(values)

def download(url, path):
    if path.exists(): return
    with urllib.request.urlopen(url, timeout=30) as response, path.open('wb') as f:
        while chunk := response.read(1024 * 1024): f.write(chunk)

def main():
    dataset = OUT / 'dataset'
    for split, count in [('train', 8), ('val', 4)]:
        (dataset / 'images' / split).mkdir(parents=True, exist_ok=True)
        (dataset / 'labels' / split).mkdir(parents=True, exist_ok=True)
        for i in range(count):
            im = Image.new('RGB', (640, 640), (20 + i, 30, 40))
            ImageDraw.Draw(im).rectangle((160, 160, 480, 480), fill=(220, 100 + i, 60))
            im.save(dataset / 'images' / split / f'{i}.png')
            (dataset / 'labels' / split / f'{i}.txt').write_text('0 0.5 0.5 0.5 0.5\n')
    data = dataset / 'data.yaml'
    data.write_text(f'path: {dataset.as_posix()}\ntrain: images/train\nval: images/val\nnames:\n  0: synthetic_rectangle\n')
    all_results = {}
    for name in ['yolo26n', 'yolo11n']:
        r = {'model': name, 'precision': 'FP32', 'batch': 1, 'imgsz': 640, 'warmup': 10, 'repeat': 50}
        all_results[name] = r
        try:
            weight = OUT / f'{name}.pt'
            url = f'https://github.com/ultralytics/assets/releases/download/v8.4.0/{name}.pt'
            r['source'] = url
            download(url, weight)
            r['sha256'] = hashlib.sha256(weight.read_bytes()).hexdigest()
            yolo = YOLO(str(weight)); model = yolo.model.cuda().eval()
            assert all(p.is_cuda for p in model.parameters())
            im_path = dataset / 'images/val/0.png'
            r['decode'] = timed(lambda: np.asarray(Image.open(im_path).convert('RGB')))
            im = np.asarray(Image.open(im_path).convert('RGB')).copy()
            r['preprocess_h2d'] = timed(lambda: torch.from_numpy(im).permute(2, 0, 1).unsqueeze(0).cuda().float() / 255)
            x = (torch.from_numpy(im).permute(2, 0, 1).unsqueeze(0).cuda().float() / 255).contiguous()
            torch.cuda.reset_peak_memory_stats()
            with torch.inference_mode(): r['torch_forward'] = timed(lambda: model(x))
            r['torch_peak_bytes'] = torch.cuda.max_memory_allocated()
            r['torch_predict'] = timed(lambda: yolo.predict(im, device=0, imgsz=640, verbose=False, half=False))
            r['torch_status'] = 'PASS'
            try:
                onnx_path = yolo.export(format='onnx', device=0, imgsz=640, batch=1, half=False, simplify=False, opset=17, dynamic=False)
                model = yolo.model.cuda().eval()
                ort.preload_dlls()
                opts = ort.SessionOptions(); opts.enable_profiling = True
                opts.profile_file_prefix = str(OUT / f'{name}-ort-profile')
                opts.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
                session = ort.InferenceSession(str(onnx_path), sess_options=opts, providers=[('CUDAExecutionProvider', {'cudnn_conv_algo_search': 'HEURISTIC', 'use_tf32': '0'})])
                session.disable_fallback()
                binding = session.io_binding()
                binding.bind_input(session.get_inputs()[0].name, 'cuda', 0, np.float32, tuple(x.shape), x.data_ptr())
                for output in session.get_outputs(): binding.bind_output(output.name, 'cuda')
                r['ort_forward'] = timed(lambda: session.run_with_iobinding(binding))
                actual = binding.copy_outputs_to_cpu()[0]
                with torch.inference_mode():
                    expected = model(x)
                    if isinstance(expected, tuple): expected = expected[0]
                    expected = expected.detach().cpu().numpy()
                r['output_shape'] = list(actual.shape)
                r['max_abs_error'] = float(np.max(np.abs(expected - actual)))
                r['alignment_pass'] = bool(np.allclose(expected, actual, rtol=1e-3, atol=1e-3))
                profile = session.end_profiling()
                events = json.loads(Path(profile).read_text())
                providers = [e['args']['provider'] for e in events if 'provider' in e.get('args', {})]
                assert providers and set(providers) == {'CUDAExecutionProvider'}, set(providers)
                r['ort_node_providers'] = sorted(set(providers))
                r['ort_status'] = 'PASS' if r['alignment_pass'] else 'FAIL'
            except Exception: r.update(ort_status='FAIL', ort_error=traceback.format_exc())
            try:
                train = YOLO(str(weight))
                observed = {'cuda_gradient': False, 'cuda_parameters': False}
                def on_start(trainer):
                    observed['cuda_parameters'] = all(p.is_cuda for p in trainer.model.parameters())
                    assert observed['cuda_parameters']
                    observed['before'] = {k: v.detach().clone() for k, v in trainer.model.named_parameters() if 'model.0.' in k}
                    for p in trainer.model.parameters():
                        if p.requires_grad:
                            def check(g):
                                assert g.is_cuda
                                observed['cuda_gradient'] = True
                                return g
                            p.register_hook(check)
                def on_end(trainer):
                    observed['changed'] = any(not torch.equal(observed['before'][k], v) for k, v in trainer.model.named_parameters() if k in observed['before'])
                    observed['optimizer_steps'] = getattr(trainer, 'p0_optimizer_steps', 0)
                train.add_callback('on_train_start', on_start)
                train.add_callback('on_train_epoch_end', on_end)
                start = time.perf_counter()
                train.train(trainer=CudaInitTrainer, data=str(data), device=0, epochs=2, batch=2, nbs=2, warmup_epochs=0, optimizer='SGD', lr0=0.01, imgsz=640, workers=0, amp=False, pretrained=True, plots=False, project=str(OUT / 'runs'), name=name, exist_ok=False, val=True, save=True, seed=123)
                r['train_seconds'] = time.perf_counter() - start
                r['train_evidence'] = {k: v for k, v in observed.items() if k != 'before'}
                assert observed['cuda_gradient'] and observed['cuda_parameters'] and observed['changed']
                checkpoint = Path(train.trainer.save_dir) / 'weights/last.pt'
                reloaded = YOLO(str(checkpoint))
                reloaded.predict(im, device=0, imgsz=640, verbose=False)
                r['checkpoint_sha256'] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
                r['train_status'] = 'PASS'
            except Exception: r.update(train_status='FAIL', train_error=traceback.format_exc())
        except Exception: r.update(status='BLOCKED', error=traceback.format_exc())
        (OUT / 'yolo-results.json').write_text(json.dumps(all_results, indent=2), encoding='utf-8')
        print(json.dumps(r, indent=2), flush=True)

if __name__ == '__main__': main()
