"""Worker-local privacy boundary for this single-GPU, local-data application."""
import os
import sys

def enforce_offline_worker():
    os.environ.update(HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                      HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',WANDB_MODE='disabled')
    for key in ('HF_TOKEN','HUGGING_FACE_HUB_TOKEN','WANDB_API_KEY','ROBOFLOW_API_KEY'):
        os.environ.pop(key,None)  # child environment only, never global settings
    def no_network(event,args):
        if event in {'socket.connect','socket.sendto','socket.sendmsg'}:
            raise PermissionError('IVAD offline RF worker does not allow network transfer')
    sys.addaudithook(no_network)
