// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
namespace Ivad.Ids {
 public sealed partial class Store {
  void ValidateLocalGeometry(Entity frame,Entity geometry){
   var video=Find(frame.Text("video_id"));var camera=Find(video.Text("camera_id"));var equipment=Find(camera.Text("equipment_id"));var project=Find(Data.project_id);var site=Find(project.Text("site_id"));
   var entities=new List<Entity>{site,project,equipment,camera,video,frame,geometry};if(geometry.kind=="Annotation")entities.Add(Find(geometry.Text("fault_id")));
   var paths=new HashSet<string>(new[]{video.Text("asset_path"),frame.Text("asset_path")});
   Rules.Validate(new Document{project_id=Data.project_id,sequence=Data.sequence,entities=entities,assets=paths.Select(path=>assetIndex[path]).ToList()});
  }
  internal Entity AddGeometryCurrent(string id,string fault,string shape,double[] points,bool roi){
   var frame=Find(id);VerifyCurrent(frame);int n=Data.entities.Count;
   try{var data=new Dictionary<string,object>{{"frame_id",id},{"fault_id",fault},{"shape",shape},{"points",points},{"coordinate_space","source_pixels"}};
    if(roi)data["camera_id"]=Find(frame.Text("video_id")).Text("camera_id");
    var e=Add(roi?"ROI":"Annotation",data);ValidateLocalGeometry(frame,e);Revise(e,"local-user");CommitFrames(new Entity[0],Data.entities.Skip(n).ToList());return e;
   }catch{RemoveTail(n);throw;}
  }
  internal Entity EditGeometryCurrent(string id,double[] points,string actor,bool deleted){
   var e=Find(id);if((e.kind!="Annotation"&&e.kind!="ROI")||String.IsNullOrWhiteSpace(actor)||e.revision==Int32.MaxValue)throw new InvalidDataException("标注或审核人无效");
   if(e.Text("deleted")=="True")throw new InvalidDataException("标注已删除");
   var frame=Find(e.Text("frame_id"));VerifyCurrent(frame);var before=CloneEntity(e);int n=Data.entities.Count;
   try{if(deleted)e.data["deleted"]=true;else e.data["points"]=points;e.revision++;ValidateLocalGeometry(frame,e);Revise(e,actor);CommitFrames(new[]{before},Data.entities.Skip(n).ToList());return e;}
   catch{e.data=before.data;e.revision=before.revision;RemoveTail(n);throw;}
  }
 }
}
