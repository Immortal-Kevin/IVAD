"""Own compatibility API, not a replacement for full upstream tqdm testing."""
import io
import ssl
import subprocess
import sys
from pathlib import Path
import pytest
from PIL import Image
from ivad_app.compat.progress import tqdm, trange
from ivad_app.compat.windows_trust import where
from ivad_app.services.media_service import dhash

def test_offline_worker_blocks_network_in_child_only():
    script = '''
import os, socket
os.environ['HF_TOKEN']='fixture-not-a-secret'
from ivad_app.compute.offline_policy import enforce_offline_worker
enforce_offline_worker()
assert 'HF_TOKEN' not in os.environ
assert os.environ['HF_HUB_OFFLINE']=='1'
for operation in (lambda s:s.connect(('127.0.0.1',9)),
                  lambda s:s.sendto(b'fixture',('127.0.0.1',9))):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        try: operation(sock)
        except PermissionError: pass
        else: raise AssertionError('Network was not blocked')
'''
    subprocess.run([sys.executable,'-c',script],check=True,timeout=20)

def test_progress_tracks_iteration_and_closes_on_error():
    bar=tqdm(range(3),disable=True)
    assert list(bar)==[0,1,2] and bar.n==3 and bar.closed
    bar=tqdm(total=5,disable=True)
    with pytest.raises(ValueError):
        with bar:
            bar.update(2);raise ValueError('fixture')
    assert bar.n==2 and bar.closed

def test_progress_lightning_state_contract():
    stream=io.StringIO();bar=tqdm(total=2,file=stream)
    bar.set_description('fixture',refresh=False)
    bar.update(1);bar.set_postfix({'loss':.5});bar.refresh()
    assert 'fixture' in stream.getvalue() and '1/2' in stream.getvalue()
    assert bar.format_dict['n']==1
    bar.reset(total=3);assert bar.n==0 and bar.total==3
    assert list(trange(2,disable=True))==[0,1]

def test_windows_ca_keeps_certificate_verification():
    path=where()
    assert Path(path).is_file() and where()==path
    context=ssl.create_default_context(cafile=path)
    assert context.verify_mode==ssl.CERT_REQUIRED and context.check_hostname
    assert context.cert_store_stats()['x509_ca']>0

def test_existing_dhash_is_bit_exact_without_numpy_runtime():
    # NumPy appears only in this test's historical oracle, not the media service.
    import numpy as np
    for seed in range(8):
        rng=np.random.default_rng(seed)
        image=Image.fromarray(rng.integers(0,256,(90,160,3),dtype=np.uint8))
        old=np.asarray(image.convert('L').resize((9,8)))
        bits=old[:,1:]>old[:,:-1]
        expected=f'{int("".join("1" if b else "0" for b in bits.ravel()),2):016x}'
        assert dhash(image)==expected
