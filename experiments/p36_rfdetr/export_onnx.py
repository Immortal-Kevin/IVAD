"""Official exporter + ONNX checker/reload with actual CUDA node profiling."""
import hashlib
import json
import os
import sys
import traceback
from pathlib import Path

os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1')
sys.path.insert(0,str(Path(__file__).parent))
from adapter import NanoAdapter


def run(weights,output):
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    result=dict(status='BLOCKED',weights=weights)
    try:
        import torch
        import numpy as np
        import onnx
        import onnxruntime as ort
        adapter=NanoAdapter.restore(weights)
        path=adapter.export(output)
        path=Path(path)
        result.update(onnx_path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        onnx.checker.check_model(str(path));result['checker']='PASS'
        ort.preload_dlls()
        options=ort.SessionOptions();options.enable_profiling=True;options.profile_file_prefix=str(output/'ort-profile')
        options.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        session=ort.InferenceSession(str(path),sess_options=options,providers=[('CUDAExecutionProvider',{'use_tf32':'0'})])
        session.disable_fallback()
        shape=[int(v) for v in session.get_inputs()[0].shape]
        x=torch.rand(shape,device='cuda',dtype=torch.float32)
        torch.backends.cuda.matmul.allow_tf32=False
        torch.backends.cudnn.allow_tf32=False
        with torch.inference_mode():reference=adapter.model.model.model.cuda().eval()(x)
        binding=session.io_binding();binding.bind_input(session.get_inputs()[0].name,'cuda',0,np.float32,shape,x.data_ptr())
        for out in session.get_outputs():binding.bind_output(out.name,'cuda')
        session.run_with_iobinding(binding)
        arrays=binding.copy_outputs_to_cpu()
        assert all(np.isfinite(a).all() for a in arrays)
        differences={}
        for out,array in zip(session.get_outputs(),arrays):
            key={'dets':'pred_boxes','labels':'pred_logits'}.get(out.name)
            if key is None:raise RuntimeError('Unknown RF-DETR export output name')
            expected=reference[key].float().cpu().numpy()
            if expected.shape!=array.shape or not np.allclose(expected,array,rtol=.005,atol=.02):raise RuntimeError('PT/ONNX raw tensor parity failed')
            differences[out.name]=float(np.max(np.abs(expected-array)))
        profile=Path(session.end_profiling())
        events=json.loads(profile.read_text(encoding='utf8'))
        nodes=[dict(name=e.get('name'),provider=e['args']['provider'],op=e['args'].get('op_name')) for e in events if e.get('args',{}).get('provider')]
        if not nodes or {n['provider'] for n in nodes}!={'CUDAExecutionProvider'}:raise RuntimeError('CUDA-only actual node execution not proven')
        result.update(status='PASS',cuda_nodes=len(nodes),providers=sorted({n['provider'] for n in nodes}),input_shape=shape,output_shapes=[list(a.shape) for a in arrays],actual_nodes=nodes,cpu_fallback=False,pt_onnx_raw_max_abs_errors=differences,parity_tolerance=dict(rtol=.005,atol=.02))
    except Exception as exc:
        result.update(error=repr(exc),traceback=traceback.format_exc());traceback.print_exc()
    (output/'export-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='actual_nodes'},ensure_ascii=False))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':sys.exit(run(*sys.argv[1:]))
