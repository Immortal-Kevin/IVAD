"""RF environment capability probe; no legacy engine or ONNX import."""
import json,subprocess,traceback
def main():
    result=dict(available=False,devices=[],errors=[])
    try:
        import torch
        result.update(available=torch.cuda.is_available(),torch=torch.__version__,cuda=torch.version.cuda)
        rows=subprocess.check_output(['nvidia-smi','--query-gpu=index,uuid,name,driver_version,memory.total','--format=csv,noheader,nounits'],text=True,timeout=10)
        for line in rows.strip().splitlines():
            index,uuid,name,driver,total=[v.strip() for v in line.split(',')];i=int(index);ok=False;bf16=False
            if result['available'] and i<torch.cuda.device_count():
                x=torch.ones(16,device=f'cuda:{i}');ok=x.is_cuda and float((x+x).sum().item())==32
                with torch.cuda.device(i):bf16=torch.cuda.is_bf16_supported()
            result['devices'].append(dict(index=i,uuid=uuid,name=name,driver=driver,total_mib=int(total),cuda_tensor_verified=ok,bf16_supported=bf16))
    except Exception:result['errors'].append(traceback.format_exc())
    print(json.dumps(result))
if __name__=='__main__':main()
