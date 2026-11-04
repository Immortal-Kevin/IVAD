// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
namespace Ivad.Ids {
 public sealed partial class Store {
  internal void SetQueueDeleted(IEnumerable<string> ids,bool deleted,string actor){
   if(String.IsNullOrWhiteSpace(actor))throw new InvalidDataException("审核人不能为空");
   var frames=ids.Distinct().Select(Find).ToList();if(frames.Count==0||frames.Any(f=>f.kind!="Frame"||f.revision==Int32.MaxValue))throw new InvalidDataException("请选择有效帧");
   var before=frames.Select(CloneEntity).ToList();int n=Data.entities.Count;
   try{foreach(var f in frames){f.data["queue_deleted"]=deleted;f.revision++;Revise(f,actor);}CommitFrames(before,Data.entities.Skip(n).ToList());}
   catch{foreach(var old in before){var f=Find(old.id);f.data=old.data;f.revision=old.revision;}RemoveTail(n);throw;}
  }
 }
 public static class QueueProjection {
  // Local queue archive is deliberately not distributed. Standard IDS 1.0 contains active frames only.
  public static Document Active(Document input){
   var d=Codec.Clone(input);var removed=new HashSet<string>(d.entities.Where(e=>e.kind=="Frame"&&e.Text("queue_deleted")=="True").Select(e=>e.id));
   bool more=true;while(more){more=false;foreach(var e in d.entities)if((removed.Contains(e.Text("frame_id"))||removed.Contains(e.Text("entity_id")))&&removed.Add(e.id))more=true;}
   var removedPaths=new HashSet<string>(d.entities.Where(e=>removed.Contains(e.id)&&e.kind=="Frame").Select(e=>e.Text("asset_path")),StringComparer.OrdinalIgnoreCase);
   d.entities.RemoveAll(e=>removed.Contains(e.id));var referenced=new HashSet<string>(d.entities.Select(e=>e.Text("asset_path")),StringComparer.OrdinalIgnoreCase);
   d.assets.RemoveAll(a=>removedPaths.Contains(a.path)&&!referenced.Contains(a.path));Rules.Validate(d);return d;
  }
 }
}
