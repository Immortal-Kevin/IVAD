"""由P0解释器独立执行；只探测，不安装依赖、不启动YOLO。"""
import json, subprocess, traceback

def main():
    result = {'available': False, 'devices': [], 'errors': []}
    try:
        import torch
        import onnxruntime as ort
        result.update(torch=torch.__version__, cuda=torch.version.cuda, ort=ort.__version__, providers=ort.get_available_providers())
        result['available'] = torch.cuda.is_available()
        text = subprocess.check_output(['nvidia-smi', '--query-gpu=index,uuid,name,driver_version,memory.total,memory.free,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], text=True, timeout=10)
        for line in text.strip().splitlines():
            fields = [value.strip() for value in line.split(',')]
            index, uuid, name, driver, total, free, used, utilization = fields
            item = {'index': int(index), 'uuid': uuid, 'name': name, 'driver': driver, 'total_mib': int(total), 'free_mib': int(free), 'used_mib': int(used), 'utilization_percent': None if utilization == '[N/A]' else int(utilization), 'cuda_tensor_verified': False}
            if result['available'] and item['index'] < torch.cuda.device_count():
                x = torch.ones(16, device=f"cuda:{item['index']}")
                assert x.is_cuda and float((x + x).sum().item()) == 32
                item['cuda_tensor_verified'] = True
                item['torch_gpu_name'] = torch.cuda.get_device_name(item['index'])
            result['devices'].append(item)
    except Exception:
        result['errors'].append(traceback.format_exc())
    print(json.dumps(result, ensure_ascii=False))

if __name__ == '__main__': main()
