"""Boundary safety tests using explicit synthetic fixtures, never human truth."""
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0,str(Path(__file__).parent))
from adapter import convert
from export_coco import export,sha


class Contracts(unittest.TestCase):
    def test_real_format_empty_and_multiclass(self):
        ctx=dict(frame_id='fixture',camera_id='camera',media_id='media',time_us=100,model_version='fixture')
        empty=convert(SimpleNamespace(xyxy=[],confidence=[],class_id=[]),width=100,height=80,class_names={},context=ctx)
        self.assertEqual(empty['boxes'],[])
        result=convert(SimpleNamespace(xyxy=[[1,2,3,4],[5,6,7,8]],confidence=[.8,.9],class_id=[0,1]),width=100,height=80,class_names={0:'A',1:'B'},context=ctx)
        self.assertEqual([b['class_name'] for b in result['boxes']],['A','B'])

    def test_invalid_prediction_rejected(self):
        for box,score in [([3,0,1,4],.9),([1,4,20,1],.9),([1,1,3,4],float('nan'))]:
            with self.assertRaises(ValueError):
                convert(SimpleNamespace(xyxy=[box],confidence=[score],class_id=[0]),width=100,height=80,class_names={0:'A'},context=dict(frame_id='f',camera_id=None,media_id='m',time_us=0,model_version='v'))

    def test_predicted_boundary_clipping_retains_raw_coordinates(self):
        result=convert(SimpleNamespace(xyxy=[[-1,0,110,90]],confidence=[.7],class_id=[0]),width=100,height=80,class_names={0:'A'},context=dict(frame_id='f',camera_id=None,media_id='m',time_us=0,model_version='v'))
        self.assertEqual(result['boxes'][0]['xyxy'],[0,0,100,80])
        self.assertEqual(result['boxes'][0]['raw_xyxy'],[-1,0,110,90])

    def test_only_declared_background_is_removed(self):
        det=SimpleNamespace(xyxy=[[1,1,3,4]],confidence=[.1],class_id=[1],data={'class_name':['__background__']})
        ctx=dict(frame_id='f',camera_id=None,media_id='m',time_us=0,model_version='v')
        result=convert(det,width=10,height=10,class_names={0:'fault'},context=ctx)
        self.assertEqual(result['boxes'],[]);self.assertEqual(result['background_removed'],1)
        det.data={'class_name':['unrecognized']}
        with self.assertRaises(ValueError):convert(det,width=10,height=10,class_names={0:'fault'},context=ctx)

    def test_zero_area_predictions_are_not_targets(self):
        det=SimpleNamespace(xyxy=[[1,0,3,0]],confidence=[.01],class_id=[0])
        result=convert(det,width=10,height=10,class_names={0:'fault'},context=dict(frame_id='f',camera_id=None,media_id='m',time_us=0,model_version='v'))
        self.assertEqual(result['boxes'],[]);self.assertEqual(result['degenerate_removed'],1)

    def test_export_refuses_polygon_hash_conflict_and_normal_box(self):
        with tempfile.TemporaryDirectory() as d:
            from PIL import Image
            root=Path(d);Image.new('RGB',(10,10)).save(root/'frame.png')
            sample=dict(split='train',annotation_source='Human Generated',width=10,height=10,image='frame.png',sha256=sha(root/'frame.png'),frame_id='f',annotation=dict(image_tag='ABNORMAL',objects=[dict(kind='polygon',source='Human Generated',geometry=[1,1,2,2],label_id='c')]))
            manifest=dict(classes=[dict(uuid='c',class_id=0,name='fixture')],samples=[sample],version_id='fixture')
            path=root/'manifest.json'
            for case in range(3):
                if case==1:sample['annotation']['objects'][0]['kind']='box';sample['sha256']='bad'
                if case==2:sample['sha256']=sha(root/'frame.png');sample['annotation']['image_tag']='NORMAL'
                path.write_text(json.dumps(manifest),encoding='utf8')
                with self.assertRaises(ValueError):export(path,root/f'out{case}')
                self.assertFalse((root/f'out{case}').exists())


if __name__=='__main__':unittest.main()
