"""补充真实图片一致性、分段计时、整卡采样显存与60秒稳定性。"""
import os, json, time, threading, subprocess, hashlib, traceback
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
os.environ['YOLO_CONFIG_DIR'] = str(ROOT / 'artifacts/yolo-config')
os.environ['YOLO_AUTOINSTALL'] = 'false'
os.environ['YOLO_OFFLINE'] = 'true'
os.environ['MPLCONFIGDIR'] = str(ROOT / 'artifacts/matplotlib')
import cv2, numpy as np, torch, onnxruntime as ort
from ultralytics import YOLO
from ultralytics.utils.nms import non_max_suppression
from yolo_test import require_cuda, timed, OUT
import faulthandler
faulthandler.cancel_dump_traceback_later()  # 60秒循环是计划测试，不是卡死。

def main():
    import ultralytics
    image_path = Path(ultralytics.__file__).parent / 'assets/bus.jpg'
    result = {'image_source': 'Ultralytics package assets/bus.jpg (public demo, not factory video)', 'image_sha256': hashlib.sha256(image_path.read_bytes()).hexdigest(), 'models': {}}
    ort.preload_dlls()
    for name in ['yolo26n', 'yolo11n']:
        r = {}; result['models'][name] = r
        samples, stop = [], threading.Event()
        def monitor():
            while not stop.is_set():
                try:
                    value = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'], text=True, timeout=5)
                    samples.append({'elapsed': time.perf_counter(), 'total_gpu_used_mib': int(value.splitlines()[0])})
                except Exception: pass
                stop.wait(0.2)
        thread = threading.Thread(target=monitor, daemon=True); thread.start()
        try:
            y = YOLO(str(OUT / f'{name}.pt'))
            model = y.model.cuda().float().eval().fuse()
            # 当前默认ONNX导出nms=None对应raw one-to-many；显式对齐此配置。
            if hasattr(model, 'end2end'): model.end2end = False
            r['torch_end2end'] = bool(getattr(model, 'end2end', False))
            r['decode'] = timed(lambda: cv2.imread(str(image_path)))
            image = cv2.imread(str(image_path))
            def preprocess():
                rgb = cv2.cvtColor(cv2.resize(image, (640, 640)), cv2.COLOR_BGR2RGB)
                return torch.from_numpy(rgb).permute(2, 0, 1).unsqueeze(0).cuda().float().div(255).contiguous()
            r['preprocess_h2d'] = timed(preprocess); x = preprocess()
            assert x.is_cuda and x.is_contiguous()
            torch.cuda.reset_peak_memory_stats()
            with torch.inference_mode():
                def forward():
                    value = model(x)
                    return value[0] if isinstance(value, tuple) else value
                expected = forward()
                r['torch_forward'] = timed(forward)
                r['torch_postprocess'] = timed(lambda: non_max_suppression(expected.clone(), conf_thres=0.25, iou_thres=0.7))
                det_t = non_max_suppression(expected.clone(), conf_thres=0.25, iou_thres=0.7)[0].cpu().numpy()
            r['torch_allocator_peak_bytes'] = torch.cuda.max_memory_allocated()
            opts = ort.SessionOptions()
            opts.add_session_config_entry('session.disable_cpu_ep_fallback', '1')
            session = ort.InferenceSession(str(OUT / f'{name}.onnx'), sess_options=opts, providers=[('CUDAExecutionProvider', {'cudnn_conv_algo_search': 'HEURISTIC', 'use_tf32': '0'})])
            session.disable_fallback(); io = session.io_binding()
            io.bind_input(session.get_inputs()[0].name, 'cuda', 0, np.float32, tuple(x.shape), x.data_ptr())
            for output in session.get_outputs(): io.bind_output(output.name, 'cuda')
            r['ort_forward'] = timed(lambda: session.run_with_iobinding(io))
            raw = io.copy_outputs_to_cpu()[0]
            r['raw_shape'] = list(raw.shape)
            reference = expected.cpu().numpy()
            r['raw_max_abs_error'] = float(np.max(np.abs(reference - raw)))
            r['raw_aligned'] = bool(np.allclose(reference, raw, atol=1e-3, rtol=1e-3))
            # 后处理允许CPU；此处比较同一NMS实现、参数和输入图像。
            r['ort_d2h_postprocess'] = timed(lambda: non_max_suppression(torch.from_numpy(io.copy_outputs_to_cpu()[0]), conf_thres=0.25, iou_thres=0.7))
            det_o = non_max_suppression(torch.from_numpy(raw), conf_thres=0.25, iou_thres=0.7)[0].numpy()
            r['torch_detections'] = det_t.tolist(); r['ort_detections'] = det_o.tolist()
            r['detection_aligned'] = bool(det_t.shape == det_o.shape and len(det_t) > 0 and np.allclose(det_t, det_o, atol=0.05, rtol=1e-3))
            started, iterations = time.perf_counter(), 0
            while time.perf_counter() - started < 60:
                session.run_with_iobinding(io); torch.cuda.synchronize(); iterations += 1
            final = io.copy_outputs_to_cpu()[0]
            r['stability'] = {'duration_seconds': time.perf_counter() - started, 'iterations': iterations, 'finite': bool(np.isfinite(final).all()), 'output_unchanged': bool(np.allclose(raw, final, atol=1e-6))}
            r['status'] = 'PASS' if r['raw_aligned'] and r['detection_aligned'] and r['stability']['finite'] and r['stability']['output_unchanged'] else 'FAIL'
            del session, io, model, y, x, expected
            torch.cuda.empty_cache()
        except Exception: r.update(status='FAIL', traceback=traceback.format_exc())
        finally:
            stop.set(); thread.join(timeout=6)
            r['total_gpu_peak_mib_sampled'] = max((s['total_gpu_used_mib'] for s in samples), default=None)
            r['gpu_memory_samples'] = samples
            (OUT / 'benchmark-supplement.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(name, r['status'], flush=True)

if __name__ == '__main__': main()
