// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using System.Diagnostics;
namespace Ivad.Ids {
 public sealed class BatchNormalResult {
  public int Selected,Success,Skipped,Failed;
  public string[] SuccessIds=new string[0];
  public Dictionary<string,int> SkipReasons=new Dictionary<string,int>();
  public BatchUndo Undo;
 }
 public sealed class BatchUndo {
  internal string fingerprint;
  internal List<Entity> before;
  internal List<string> appended;
  internal Dictionary<string,int> revisions;
 }
 public sealed partial class Store {
  Dictionary<string,Entity> entityIndex;
  Dictionary<string,Asset> assetIndex;
  readonly Dictionary<string,string> verifiedStamp=new Dictionary<string,string>();
  string committedJson;bool canonical;
  public static double LastCommitMs,LastPatchMs,LastConflictMs,LastAssetMs,LastStateMs;
  void InitializeFast(string json){
   committedJson=Codec.Json(Data);canonical=true;
   entityIndex=Data.entities.ToDictionary(e=>e.id);assetIndex=Data.assets.ToDictionary(a=>a.path,StringComparer.OrdinalIgnoreCase);
  }
  void VerifyCurrent(Entity frame){
   var a=assetIndex[frame.Text("asset_path")];string path=Rules.SafePath(Root,a.path);var info=new FileInfo(path);
   string stamp=info.Length+"/"+info.LastWriteTimeUtc.Ticks+"/"+info.CreationTimeUtc.Ticks,old;
   if(!verifiedStamp.TryGetValue(a.path,out old)||old!=stamp){if(info.Length!=a.bytes||Codec.HashFile(path)!=a.sha256)throw new InvalidDataException("当前图片哈希不符: "+a.path);verifiedStamp[a.path]=stamp;}
  }
  // Dedicated clean-session transaction. Public general edits still use full Validate/VerifyAssets/Save.
  // Only supplied frame states and freshly generated audit entities can enter this path.
  internal void ReviewCurrent(string id,string state,string review,string actor){
   if(!new[]{"normal","abnormal","unknown","unannotated"}.Contains(state)||!new[]{"confirmed","rejected","needs_work","unknown"}.Contains(review)||String.IsNullOrWhiteSpace(actor))throw new InvalidDataException("审核参数无效");
   var frame=Find(id);if(frame.kind!="Frame"||frame.revision==Int32.MaxValue)throw new InvalidDataException("请选择帧");
   var watch=Stopwatch.StartNew();VerifyCurrent(frame);LastAssetMs=watch.Elapsed.TotalMilliseconds;
   var before=CloneEntity(frame);int n=Data.entities.Count;
   try{ApplyReview(frame,state,review,actor);CommitFrames(new[]{before},Data.entities.Skip(n).ToList());}
   catch{frame.data=before.data;frame.revision=before.revision;RemoveTail(n);throw;}
  }
  static Entity CloneEntity(Entity e){return Codec.Parse<Entity>(Codec.Json(e));}
  void RemoveTail(int count){if(Data.entities.Count>count)Data.entities.RemoveRange(count,Data.entities.Count-count);entityIndex=Data.entities.ToDictionary(e=>e.id);}
  void ApplyReview(Entity frame,string state,string review,string actor){var watch=Stopwatch.StartNew();frame.data["state"]=state;frame.revision++;Revise(frame,actor);var r=Add("Review",new Dictionary<string,object>{{"frame_id",frame.id},{"status",review},{"reviewer",actor},{"utc",DateTime.UtcNow.ToString("o")}});Revise(r,actor);LastStateMs=watch.Elapsed.TotalMilliseconds;}
  void CommitFrames(IEnumerable<Entity> before,List<Entity> appended,List<Entity> removed=null){
   if(Data.sequence==Int64.MaxValue)throw new InvalidDataException("项目序列溢出");
   if(!canonical)throw new InvalidDataException("清单非规范格式，请先执行一次完整保存后重试");
   var watch=Stopwatch.StartNew();string next=committedJson;
   var edits=new List<Tuple<int,int,string>>();
   foreach(var old in before){string token=Codec.Json(old);int pos=next.IndexOf(token,StringComparison.Ordinal);if(pos<0)throw new IOException("会话帧已被未提交更改，请重新打开");edits.Add(Tuple.Create(pos,token.Length,Codec.Json(Find(old.id))));}
   var builder=new StringBuilder(next.Length+4096);int cursor=0;
   foreach(var edit in edits.OrderBy(e=>e.Item1)){builder.Append(next,cursor,edit.Item1-cursor);builder.Append(edit.Item3);cursor=edit.Item1+edit.Item2;}
   builder.Append(next,cursor,next.Length-cursor);next=builder.ToString();
   if(removed!=null&&removed.Count>0){string tail=","+String.Join(",",removed.Select(Codec.Json));int stop=next.LastIndexOf("],\"assets\":",StringComparison.Ordinal);if(stop<tail.Length||next.Substring(stop-tail.Length,tail.Length)!=tail)throw new IOException("批次审计尾部已变化，拒绝撤销");next=next.Remove(stop-tail.Length,tail.Length);}
   int end=next.LastIndexOf("],\"assets\":",StringComparison.Ordinal);if(end<0)throw new InvalidDataException("清单结构不支持局部提交");
   next=next.Insert(end,appended.Count==0?"":","+String.Join(",",appended.Select(Codec.Json)));
   string seq="\"sequence\":"+Data.sequence+",";int at=next.IndexOf(seq,StringComparison.Ordinal);if(at<0)throw new IOException("序列已变化");next=next.Remove(at,seq.Length).Insert(at,"\"sequence\":"+(Data.sequence+1)+",");LastPatchMs=watch.Elapsed.TotalMilliseconds;
   string temp=Manifest+"."+Guid.NewGuid().ToString("N")+".tmp";watch.Restart();
   using(var hold=new FileStream(Path.Combine(Root,".write.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
    var conflict=Stopwatch.StartNew();if(expected!=Codec.HashFile(Manifest))throw new IOException("项目被另一进程修改，请重新打开");LastConflictMs=conflict.Elapsed.TotalMilliseconds;
    try{var bytes=new UTF8Encoding(false).GetBytes(next);string hash=Codec.Hash(bytes);
     using(var output=new FileStream(temp,FileMode.CreateNew,FileAccess.Write,FileShare.None)){output.Write(bytes,0,bytes.Length);output.Flush(true);}Work.Report("HOTFIX_COMMIT_PRE_REPLACE");
     File.Replace(temp,Manifest,Manifest+".backup",true);
     expected=hash;committedJson=next;Data.sequence++;
     foreach(var e in appended)entityIndex[e.id]=e;
     if(removed!=null)foreach(var e in removed)entityIndex.Remove(e.id);
    }finally{if(File.Exists(temp))File.Delete(temp);}
   }
   LastCommitMs=watch.Elapsed.TotalMilliseconds;
  }
  internal BatchUndo MarkNormalBatch(IEnumerable<string> ids,string actor){
   if(String.IsNullOrWhiteSpace(actor))throw new InvalidDataException("审核人不能为空");
   var selected=ids.Distinct().Select(Find).ToList();if(selected.Count==0)throw new InvalidDataException("请先选择帧");
   var forbidden=new HashSet<string>(Data.entities.Where(e=>e.kind=="Annotation"&&e.Text("deleted")!="True").Select(e=>e.Text("frame_id")));
   foreach(var r in Data.entities.Where(e=>e.kind=="Review").GroupBy(e=>e.Text("frame_id")).Select(g=>g.Last()).Where(e=>e.Text("status")=="confirmed"))forbidden.Add(r.Text("frame_id"));
   foreach(var f in selected)if(f.kind!="Frame"||f.Text("queue_deleted")=="True"||f.revision==Int32.MaxValue||f.Text("state")!="unannotated"||forbidden.Contains(f.id))throw new InvalidDataException("批次包含已标注或带异常框的帧，整个批次未提交");
   foreach(var f in selected){var a=assetIndex[f.Text("asset_path")];var info=new FileInfo(Rules.SafePath(Root,a.path));if(!info.Exists||info.Length!=a.bytes)throw new InvalidDataException("批次图片缺失或尺寸已变化");}
   // No image decode or image SHA in a metadata-only batch. Exports always verify every asset.
   var before=selected.Select(CloneEntity).ToList();int n=Data.entities.Count;
   try{int prepared=0;foreach(var f in selected){ApplyReview(f,"normal","confirmed",actor);prepared++;if(prepared%32==0||prepared==selected.Count)Work.Report("IVAD_BATCH|正在准备审核记录；尚未提交|"+prepared+"|"+selected.Count);}Work.Report("IVAD_BATCH|正在原子提交；尚未确认保存|"+selected.Count+"|"+selected.Count);var added=Data.entities.Skip(n).ToList();CommitFrames(before,added);return new BatchUndo{fingerprint=expected,before=before,appended=added.Select(e=>e.id).ToList(),revisions=selected.ToDictionary(e=>e.id,e=>e.revision)};}
   catch{foreach(var old in before){var f=Find(old.id);f.data=old.data;f.revision=old.revision;}RemoveTail(n);throw;}
  }
  // The UI batches eligible targets without relaxing the strict atomic transaction used below.
  // The result is in-memory only: IDS schemas, review UUIDs and revision persistence are unchanged.
  internal BatchNormalResult MarkNormalBatchEligible(IEnumerable<string> ids,string actor,BatchNormalResult result,string draftFrame=null){
   var targets=ids.Distinct().ToArray();result.Selected=targets.Length;
   try{
    if(String.IsNullOrWhiteSpace(actor))throw new InvalidDataException("审核人不能为空");
    var annotated=new HashSet<string>(Data.entities.Where(e=>e.kind=="Annotation"&&e.Text("deleted")!="True").Select(e=>e.Text("frame_id")));
    var reviews=Data.entities.Where(e=>e.kind=="Review").GroupBy(e=>e.Text("frame_id")).ToDictionary(g=>g.Key,g=>g.Last());
    var eligible=new List<string>();int checkedCount=0;
    Work.Report("IVAD_BATCH|正在检查选择；尚未提交|0|"+targets.Length);
    foreach(string id in targets){
     Work.Check();var f=Find(id);Entity r;reviews.TryGetValue(id,out r);string reason=null;
     if(f.kind!="Frame")throw new InvalidDataException("多选集合包含非图片帧，未提交");
     if(id==draftFrame)reason="当前帧有未保存草稿";
     else if(f.Text("queue_deleted")=="True")reason="已软删除";
     else if(annotated.Contains(id))reason="存在异常框或多边形";
     else if(f.Text("locked")=="True"||f.Text("review_locked")=="True"||(r!=null&&(r.Text("status")=="confirmed"||r.Text("locked")=="True")))reason="已确认或审核锁定";
     else if(f.Text("state")!="unannotated")reason="不是未标注状态";
     else if(f.revision==Int32.MaxValue)reason="修订号达到上限";
     if(reason==null)eligible.Add(id);else{result.Skipped++;if(!result.SkipReasons.ContainsKey(reason))result.SkipReasons[reason]=0;result.SkipReasons[reason]++;}
     checkedCount++;if(checkedCount%32==0||checkedCount==targets.Length)Work.Report("IVAD_BATCH|正在检查选择；尚未提交|"+checkedCount+"|"+targets.Length);
    }
    if(eligible.Count>0){result.Undo=MarkNormalBatch(eligible,actor);result.SuccessIds=eligible.ToArray();result.Success=eligible.Count;}
    return result;
   }catch{result.Success=0;result.Failed=result.Selected-result.Skipped;throw;}
  }
  internal void UndoBatch(BatchUndo undo,string actor){
   if(undo==null||undo.fingerprint!=expected)throw new IOException("批次之后已有编辑，拒绝撤销以保护后续数据");
   var before=undo.before.Select(e=>CloneEntity(Find(e.id))).ToList();int n=undo.appended.Count;
   var removed=Data.entities.Skip(Data.entities.Count-n).ToList();
   if(!removed.Select(e=>e.id).SequenceEqual(undo.appended))throw new IOException("批次审计尾部已变化");
   try{foreach(var old in undo.before){var f=Find(old.id);if(f.revision!=undo.revisions[f.id])throw new IOException("帧已编辑");f.data=Codec.Parse<Dictionary<string,object>>(Codec.Json(old.data));f.revision=old.revision;}
    Data.entities.RemoveRange(Data.entities.Count-n,n);CommitFrames(before,new List<Entity>(),removed);
   }catch{foreach(var old in before){var f=Find(old.id);f.data=old.data;f.revision=old.revision;}if(Data.entities.Count==0||Data.entities[Data.entities.Count-1].id!=removed[removed.Count-1].id)Data.entities.AddRange(removed);throw;}

  }
 }
}
