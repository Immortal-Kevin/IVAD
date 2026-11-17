// SPDX-License-Identifier: LicenseRef-IVAD-Proprietary
// Private NVIDIA integration boundary. Not included in Annotator.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Ivad.Ids;
namespace Ivad.Full {
 public interface ITrainingBackend { string Name {get;} bool CanTrain {get;} void Train(string snapshot,string approvedWeight); }
 public sealed class RfDetrBackend:ITrainingBackend {
  public string Name {get{return "RF-DETR core (license review pending)";}}
  public bool CanTrain {get{return false;}}
  public void Train(string snapshot,string approvedWeight){throw new InvalidOperationException("BLOCKED: 固定训练环境、具体权重授权/哈希与NVIDIA实测尚未批准通过；禁止自动下载或回退");}
 }
 public static class CocoAdapter {
  public static void Export(Store s,string output){
   Rules.Validate(s.Data);Rules.VerifyAssets(s.Data,s.Root);if(Directory.Exists(output))throw new IOException("快照导出目录必须不存在");
   var faults=s.Data.entities.Where(e=>e.kind=="Fault").OrderBy(e=>e.id).ToList();
   var frames=s.Data.entities.Where(e=>e.kind=="Frame"&&(e.Text("state")=="normal"||e.Text("state")=="abnormal")&&LatestConfirmed(s,e)).OrderBy(e=>e.id).ToList();
   var cats=faults.Select((e,i)=>new{id=i+1,name=e.Text("name"),ids_fault_id=e.id,taxonomy_version=e.Number("taxonomy_version")}).ToList();
   var images=new List<object>();var anns=new List<object>();int aid=0;
   string stage=output+".staging-"+Guid.NewGuid().ToString("N");Directory.CreateDirectory(stage);Directory.CreateDirectory(Path.Combine(stage,"images"));
   try{for(int i=0;i<frames.Count;i++){var f=frames[i];string filename=f.id+Path.GetExtension(f.Text("asset_path"));File.Copy(Rules.SafePath(s.Root,f.Text("asset_path")),Path.Combine(stage,"images",filename));images.Add(new{id=i+1,file_name="images/"+filename,width=(int)f.Number("width"),height=(int)f.Number("height"),ids_frame_id=f.id});
    foreach(var a in s.Data.entities.Where(e=>e.kind=="Annotation"&&e.Text("frame_id")==f.id&&e.Text("deleted")!="True")){
     if(a.Text("shape")!="box")throw new InvalidOperationException("当前COCO检测适配器只支持矩形；不能静默丢弃多边形");
     double[] p=Codec.Parse<double[]>(Codec.Json(a.data["points"]));anns.Add(new{id=++aid,image_id=i+1,category_id=faults.FindIndex(e=>e.id==a.Text("fault_id"))+1,bbox=new[]{p[0],p[1],p[2]-p[0],p[3]-p[1]},area=(p[2]-p[0])*(p[3]-p[1]),iscrowd=0,ids_annotation_id=a.id});
    }
   }File.WriteAllText(Path.Combine(stage,"annotations.json"),Codec.Json(new{images=images,annotations=anns,categories=cats}));File.WriteAllText(Path.Combine(stage,"snapshot.ids.json"),Codec.Json(s.Data));Directory.Move(stage,output);
   }finally{if(Directory.Exists(stage))Directory.Delete(stage,true);}
  }
  static bool LatestConfirmed(Store s,Entity frame){var r=s.Data.entities.LastOrDefault(e=>e.kind=="Review"&&e.Text("frame_id")==frame.id);return r!=null&&r.Text("status")=="confirmed";}
 }
}
