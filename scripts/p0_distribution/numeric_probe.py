"""Exercise actual numeric DLL dispatch, not only imports; emit local evidence."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import numpy as np
import scipy,scipy.linalg,scipy.optimize,scipy.ndimage,scipy.spatial.distance
from scripts.permissive.media_probe import loaded_modules
out=Path(sys.argv[1]);rng=np.random.default_rng(1907);a=rng.normal(size=(32,32));a=a.T@a+np.eye(32);b=rng.normal(size=32)
x=scipy.linalg.solve(a,b);assert np.max(np.abs(a@x-b))<1e-10
u,s,v=scipy.linalg.svd(a);assert np.allclose((u*s)@v,a,rtol=1e-12,atol=1e-12)
r,c=scipy.optimize.linear_sum_assignment(a)
values={'solve':x.tolist(),'singular_values':s.tolist(),'assignment':c.tolist(),
 'gaussian':scipy.ndimage.gaussian_filter(a,1.5).tolist(),'distance':scipy.spatial.distance.cdist(a[:3],a[3:7]).tolist()}
out.write_text(json.dumps({'status':'PASS','numpy':np.__version__,'scipy':scipy.__version__,'numpy_path':np.__file__,
 'scipy_path':scipy.__file__,'values':values,'loaded_modules':loaded_modules()},indent=2),encoding='utf8')
print('PASS: solve, SVD, assignment, Gaussian filter, distances; native module trace captured')
