"""Exercise the installed RF COCO label mapper, no neural computation."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/p37a-20261016/loader-mapping';OUT.mkdir(exist_ok=True)
from rfdetr.datasets.coco import _train_split_cat2label
results=[]
for ids in [(0,1),(1,5),(3,17)]:
    path=OUT/('-'.join(map(str,ids)));(path/'train').mkdir(parents=True,exist_ok=True)
    data=dict(categories=[dict(id=ids[1],name='B',supercategory='B'),dict(id=ids[0],name='fault',supercategory='fault')],annotations=[dict(category_id=ids[1])])
    (path/'train/_annotations.coco.json').write_text(json.dumps(data),encoding='utf8')
    actual=_train_split_cat2label(path);assert actual=={ids[0]:0,ids[1]:1};results.append(dict(category_ids=ids,model_mapping=actual,status='PASS'))
(OUT/'result.json').write_text(json.dumps(results,indent=2),encoding='utf8');print(json.dumps(results))
