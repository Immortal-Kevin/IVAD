"""P0 实际 GPU 门禁；不提供 CPU fallback。"""
import argparse
import json
import traceback
from pathlib import Path


def openvino_probe():
    import numpy as np
    import openvino as ov
    from openvino import opset13 as ops
    core = ov.Core()
    devices = core.available_devices
    assert any(d.startswith('GPU') for d in devices), devices
    name = core.get_property('GPU', 'FULL_DEVICE_NAME')
    assert 'B390' in name, name
    x = ops.parameter([1, 4], np.float32)
    model = ov.Model([ops.relu(ops.add(x, ops.constant(np.ones((1, 4), dtype=np.float32))))], [x])
    compiled = core.compile_model(model, 'GPU', {'PERFORMANCE_HINT': 'LATENCY'})
    execution = compiled.get_property('EXECUTION_DEVICES')
    assert all(d.startswith('GPU') for d in execution), execution
    result = compiled([np.array([[-2, 0, 2, 4]], dtype=np.float32)])[0]
    np.testing.assert_allclose(result, [[0, 1, 3, 5]], atol=1e-6)
    return dict(version=ov.__version__, devices=devices, name=name, execution_devices=execution, output=result.tolist())


def xpu_probe():
    import torch
    assert torch.xpu.is_available(), 'XPU unavailable'
    name = torch.xpu.get_device_name(0)
    assert 'B390' in name, name
    torch.manual_seed(7)
    model = torch.nn.Linear(4, 2).to('xpu')
    inputs = torch.ones(2, 4, device='xpu')
    target = torch.zeros(2, 2, device='xpu')
    before = model.weight.detach().clone()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    output = model(inputs)
    loss = (output - target).square().mean()
    loss.backward()
    assert output.device.type == loss.device.type == model.weight.grad.device.type == 'xpu'
    optimizer.step()
    torch.xpu.synchronize()
    delta = (model.weight - before).abs().max().item()
    assert delta > 0
    return dict(version=torch.__version__, name=name, properties=str(torch.xpu.get_device_properties(0)), device=str(output.device), loss=loss.item(), weight_delta=delta)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('backend', choices=['openvino', 'xpu'])
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    try:
        result = dict(status='PASS', backend=args.backend, evidence=(openvino_probe() if args.backend == 'openvino' else xpu_probe()))
    except Exception:
        error = traceback.format_exc()
        result = dict(status='BLOCKED' if 'ModuleNotFoundError' in error else 'FAIL', backend=args.backend, traceback=error)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result['status'] == 'PASS' else 1)
