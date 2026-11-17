// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  public void OpenSelectionFixture(string root,int count=10000,bool nativeTiming=false){
   if(count<2||count>10000)throw new ArgumentOutOfRangeException("count");
   var s=Fixture(root,2);if(s.Data.entities.Count(e=>e.kind=="Frame")<count){var model=s.Data.entities.First(e=>e.kind=="Frame");for(int i=2;i<count;i++){var e=Codec.Parse<Entity>(Codec.Json(model));e.id=Guid.NewGuid().ToString();e.data["pts_us"]=(long)i*100000;e.data["source_timestamp_100ns"]=(long)i*1000000;s.Data.entities.Add(e);}s.Save();}Use(s);Navigate("标注与审核");Title="IVAD H4-H5 ISOLATED INPUT TEST · "+count;
   if(nativeTiming)EnableNativeInputTiming(root,count);
  }
  // Test-only observation of native Windows input reaching the actual visible WPF window.
  // It never injects input, calls a command, or enables telemetry for normal launches.
  void EnableNativeInputTiming(string root,int count){
   string path=Path.Combine(root,"native-input-"+DateTime.UtcNow.ToString("yyyyMMddTHHmmss")+"-"+Guid.NewGuid().ToString("N")+".jsonl");
   int serial=0;
   PreviewKeyDown+=(sender,e)=>{
    bool shift=(System.Windows.Input.Keyboard.Modifiers&System.Windows.Input.ModifierKeys.Shift)!=0;
    bool control=(System.Windows.Input.Keyboard.Modifiers&System.Windows.Input.ModifierKeys.Control)!=0;
    string action=shift&&e.Key==System.Windows.Input.Key.End?"shift-end":shift&&e.Key==System.Windows.Input.Key.Home?"shift-home":control&&e.Key==System.Windows.Input.Key.S?"ctrl-s":null;
    if(action==null||busy||e.IsRepeat||frame==null)return;
    int timestamp=e.Timestamp,id=++serial;long seq=store.Data.sequence;string oldFrame=frame.id;var watch=Stopwatch.StartNew();long hashBefore=Work.HashCalls;
    EventHandler rendered=null;
    rendered=(x,y)=>{
     if(action=="ctrl-s"&&(busy||frame==null||frame.id==oldFrame||store.Data.sequence==seq))return;
     System.Windows.Media.CompositionTarget.Rendering-=rendered;
     Dispatcher.BeginInvoke(System.Windows.Threading.DispatcherPriority.ApplicationIdle,new Action(()=>{
      bool overlap=serial!=id;double ms=unchecked((uint)(Environment.TickCount-timestamp));
      var row=new{id=id,action=action,frames=count,selected=frames.Ids.Count,windows_message_to_wpf_render_idle_ms=ms,handler_to_render_idle_ms=watch.Elapsed.TotalMilliseconds,overlap=overlap,old_frame_uuid=oldFrame,next_frame_uuid=frame==null?null:frame.id,sequence_before=seq,sequence_after=store.Data.sequence,file_sha_calls=Work.HashCalls-hashBefore,physical_input=true,scope="Native Windows message timestamp to WPF Rendering then ApplicationIdle; excludes compositor/display scanout and tool transport"};
      File.AppendAllText(path,Codec.Json(row)+Environment.NewLine);
     }));
    };
    System.Windows.Media.CompositionTarget.Rendering+=rendered;
   };
  }
  public int RealCopyCheck(string input,string output){
   System.Threading.SynchronizationContext.SetSynchronizationContext(new System.Windows.Threading.DispatcherSynchronizationContext(Dispatcher));
   Directory.CreateDirectory(output);var results=new List<object>();try{
    var s=Packages.Import(input,Path.Combine(output,"project"));Use(s);Navigate("标注与审核");string id=orderedFrames.First().id;saveAdvanceCommand.Execute(null,this);WaitHotfix();
    var candidate=orderedFrames.FirstOrDefault(e=>e.Text("state")=="unannotated"&&!shapeIndex.ContainsKey(e.id));if(candidate!=null){var undo=s.MarkNormalBatch(new[]{candidate.id},"isolated-test");s.UndoBatch(undo,"isolated-test");results.Add("batch normal and undo PASS");}else results.Add("batch normal NOT APPLICABLE: no eligible original frame; synthetic test covers path");
    var baseline=Codec.Clone(s.Data);string full=Path.Combine(output,"full.ids");Packages.Export(s,full,null);var receiver=Packages.Import(full,Path.Combine(output,"receiver"));s.SetQueueDeleted(new[]{id},true,"isolated-test");string delta=Path.Combine(output,"deleted.ids");Packages.Export(s,delta,baseline);receiver=Packages.Import(delta,receiver.Root);Check(!receiver.Data.entities.Any(e=>e.id==id),"real-copy deleted excluded");baseline=Codec.Clone(s.Data);s.SetQueueDeleted(new[]{id},false,"isolated-test");string restored=Path.Combine(output,"restored.ids");Packages.Export(s,restored,baseline);receiver=Packages.Import(restored,receiver.Root);Check(Codec.Fingerprint(receiver.Data)==Codec.Fingerprint(QueueProjection.Active(s.Data)),"real-copy restore fingerprint");Rules.VerifyAssets(receiver.Data,receiver.Root);File.WriteAllText(Path.Combine(output,"result.json"),Codec.Json(new{status="PASS",frames=orderedFrames.Count,input_sha256=Codec.HashFile(input),checks=results,scope="authorized IDS copy only; in-process WPF routed save and real filesystem full/delta/restore"}));ticker.Stop();return 0;
   }catch(Exception e){File.WriteAllText(Path.Combine(output,"result.json"),Codec.Json(new{status="FAIL",error=e.ToString()}));ticker.Stop();return 1;}
  }
  public int H45Checks(string output){
   Directory.CreateDirectory(output);var results=new List<object>();var benches=new List<object>();int failed=0;
   Action<string,Action> test=(name,work)=>{try{work();results.Add(new{name=name,status="PASS",scope="in-process WPF/filesystem, not physical input"});}catch(Exception e){failed++;results.Add(new{name=name,status="FAIL",error=e.ToString()});}File.WriteAllText(Path.Combine(output,"results.json"),Codec.Json(new{failed=failed,tests=results,benchmarks=benches}));};
   foreach(int count in new[]{600,1000,1800,2708,10000})test("range-"+count,()=>{
    var list=new RangeFrameList{Height=600,Width=260};var choices=Enumerable.Range(0,count).Select(i=>new Choice{Id=Guid.NewGuid().ToString(),Name=i+" s"}).ToArray();list.ItemsSource=choices;var host=new Border{Child=list};host.Measure(new Size(260,600));host.Arrange(new Rect(0,0,260,600));list.ApplyTemplate();list.Measure(new Size(260,600));list.Arrange(new Rect(0,0,260,600));list.UpdateLayout();
    foreach(int n in new[]{Math.Min(1000,count),count}.Distinct()){
     var times=new List<double>();Work.ResetMetrics();for(int k=0;k<100;k++){var watch=Stopwatch.StartNew();list.ResetSelection();list.SelectRange(0,n-1,false);list.UpdateLayout();times.Add(watch.Elapsed.TotalMilliseconds);Check(list.Ids.Count==n,"exact range count");}
     times.Sort();int realized=Enumerable.Range(0,count).Count(i=>list.ItemContainerGenerator.ContainerFromIndex(i)!=null);Check(realized>0&&realized<100,"virtualized containers");Check(Work.HashCalls==0,"zero selection hashes");double p95=times[94];Check(p95<=(n<=1000?100:200),"range performance target");benches.Add(new{frames=count,selected=n,samples=100,p50_ms=times[49],p95_ms=p95,realized_rows=realized,file_sha256_calls=Work.HashCalls,scope="UUID range model plus realized-row paint and offscreen WPF layout; NOT physical Shift latency"});
    }
    list.SelectedIndex=0;list.SelectRange(0,count-1,false);list.SelectedIndex=1;Check(list.Ids.Count==1&&list.Ids.Contains(choices[1].Id),"navigation clears stale bulk selection");
   });
   var s=Fixture(Path.Combine(output,"project"),24);string root=s.Root;var ids=s.Data.entities.Where(e=>e.kind=="Frame").Take(3).Select(e=>e.id).ToArray();var original=Codec.Clone(s.Data);string before=Codec.Fingerprint(s.Data);
   test("IDS-canonical-order-after-reflection-cache-and-parse",()=>{string json=Codec.Json(s.Data);foreach(var e in s.Data.entities){typeof(Entity).GetProperty("data").GetValue(e,null);typeof(Entity).GetProperty("revision").GetValue(e,null);}for(int i=0;i<5;i++){Check(json==Codec.Json(s.Data),"stable serialization after named reflection access");Check(json==Codec.Json(Codec.Parse<Document>(json)),"stable parse reserialize bytes");}Check(json.StartsWith("{\"schema\":\"ids/1.0\""),"legacy declaration order retained");});
   test("delete-restore-preserve-all-geometry-pts-files",()=>{string fault=s.Data.entities.First(e=>e.kind=="Fault").id;s.AddGeometryCurrent(ids[0],fault,"box",new[]{1.0,1,20,20},false);s.ReviewCurrent(ids[0],"abnormal","confirmed","test");original=Codec.Clone(s.Data);s.SetQueueDeleted(ids,true,"test");Check(ids.All(id=>s.Find(id).Text("queue_deleted")=="True"),"deleted persisted");var reopened=new Store(root);Check(Codec.Fingerprint(s.Data)==Codec.Fingerprint(reopened.Data),"reopen");Check(ids.All(id=>File.Exists(Rules.SafePath(root,s.Find(id).Text("asset_path")))),"physical files retained");Check(s.Data.entities.Count==original.entities.Count+ids.Length,"all original entities retained");s.SetQueueDeleted(ids,false,"test");foreach(var id in ids){var old=original.entities.First(e=>e.id==id);var f=s.Find(id);Check(f.Text("state")==old.Text("state")&&f.Text("pts_us")==old.Text("pts_us")&&f.Text("video_id")==old.Text("video_id"),"state PTS identity restored");}});
   test("delete-cancel-and-write-conflict-atomic-rollback",()=>{before=Codec.Fingerprint(s.Data);Work.Configure(()=>true,null);bool rejected=false;try{s.SetQueueDeleted(ids,true,"test");}catch(OperationCanceledException){rejected=true;}finally{Work.Configure(null,null);}Check(rejected&&before==Codec.Fingerprint(s.Data)&&before==Codec.Fingerprint(new Store(root).Data),"cancel rollback");using(var hold=new FileStream(Path.Combine(root,".write.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){rejected=false;try{s.SetQueueDeleted(ids,true,"test");}catch(IOException){rejected=true;}Check(rejected&&before==Codec.Fingerprint(s.Data),"lock rollback");}});
   test("active-IDS-full-delta-restore-no-dangling-references",()=>{
    string full=Path.Combine(output,"before.ids");Packages.Export(s,full,null);var receiver=Packages.Import(full,Path.Combine(output,"receiver"));var baseline=Codec.Clone(s.Data);
    s.SetQueueDeleted(ids,true,"test");string delta=Path.Combine(output,"deleted-delta.ids");Packages.Export(s,delta,baseline);receiver=Packages.Import(delta,receiver.Root);Check(!receiver.Data.entities.Any(e=>ids.Contains(e.id)||ids.Contains(e.Text("frame_id"))),"deleted absent from standard IDS active set");Rules.Validate(receiver.Data);Rules.VerifyAssets(receiver.Data,receiver.Root);
    string clean=Path.Combine(output,"deleted-full.ids");Packages.Export(s,clean,null);var empty=Packages.Import(clean,Path.Combine(output,"empty"));Check(Codec.Fingerprint(empty.Data)==Codec.Fingerprint(receiver.Data),"full delta match");
    baseline=Codec.Clone(s.Data);s.SetQueueDeleted(ids,false,"test");string restore=Path.Combine(output,"restored-delta.ids");Packages.Export(s,restore,baseline);receiver=Packages.Import(restore,receiver.Root);Check(ids.All(id=>receiver.Find(id).kind=="Frame"),"restored exported");Check(Codec.Fingerprint(QueueProjection.Active(s.Data))==Codec.Fingerprint(receiver.Data),"active identity");Packages.Import(restore,receiver.Root);Check(Codec.Fingerprint(receiver.Data)==Codec.Fingerprint(new Store(receiver.Root).Data),"idempotent");
   });
   test("deleted-frames-hidden-normal-rejected-restore-filter",()=>{s.SetQueueDeleted(ids,true,"test");Use(s);Navigate("标注与审核");Check(!visibleFrames.Any(c=>ids.Contains(c.Id)),"default hidden");frameStateFilter.SelectedIndex=3;Check(visibleFrames.Count==3&&visibleFrames.All(c=>ids.Contains(c.Id)),"deleted filter");string fingerprint=Codec.Fingerprint(s.Data);bool rejected=false;try{s.MarkNormalBatch(new[]{ids[1]},"test");}catch(InvalidDataException){rejected=true;}Check(rejected&&fingerprint==Codec.Fingerprint(s.Data),"cannot relabel deleted");s.SetQueueDeleted(ids,false,"test");Refresh();frameStateFilter.SelectedIndex=0;Check(visibleFrames.Count==24,"restored queue");});
   ticker.Stop();return failed==0?0:1;
  }
 }
}
