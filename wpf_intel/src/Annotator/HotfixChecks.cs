// SPDX-License-Identifier: Apache-2.0
// Isolated synthetic command benchmarks; never opens or activates a native window.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  void WaitHotfix(){var loop=new DispatcherFrame();var timer=new DispatcherTimer(DispatcherPriority.Background){Interval=TimeSpan.FromMilliseconds(1)};var until=DateTime.UtcNow.AddMinutes(3);timer.Tick+=(s,e)=>{if(!busy||DateTime.UtcNow>until){timer.Stop();loop.Continue=false;}};timer.Start();Dispatcher.PushFrame(loop);Check(!busy&&!status.Text.StartsWith("操作失败"),status.Text);}
  static Store Fixture(string root,int count){
   if(File.Exists(Path.Combine(root,"project.ids.json")))return new Store(root);
   var s=Store.Create(root,"Hotfix synthetic "+count,"Synthetic only");
   var eq=s.Add("Equipment",new Dictionary<string,object>{{"name","Synthetic"},{"project_id",s.Data.project_id}});
   var cam=s.Add("Camera",new Dictionary<string,object>{{"name","Synthetic camera"},{"equipment_id",eq.id}});
   s.Add("Fault",new Dictionary<string,object>{{"name","Synthetic fault"},{"taxonomy_version",1}});
   Directory.CreateDirectory(Path.Combine(root,"assets"));
   var vs=new List<Entity>();
   for(int v=0;v<2;v++){string rel="assets/source-"+v+".bin",p=Path.Combine(root,rel);File.WriteAllText(p,"Synthetic source descriptor "+v);s.Data.assets.Add(new Asset{path=rel,sha256=Codec.HashFile(p),bytes=new FileInfo(p).Length});vs.Add(s.Add("Video",new Dictionary<string,object>{{"camera_id",cam.id},{"asset_path",rel},{"original_name","synthetic-"+v}}));}
   using(var bmp=new System.Drawing.Bitmap(640,360)){
    // Structured synthetic industrial-like gradients/stripes, unique per frame; no reused image asset.
    var rand=new Random(4917);var pixels=new byte[640*360*3];rand.NextBytes(pixels);
    for(int y=0;y<360;y++)for(int x=0;x<640;x++)bmp.SetPixel(x,y,System.Drawing.Color.FromArgb((x/8+y/8)%256,(x/4)%256,(y/2)%256));
    for(int i=0;i<count;i++){
     using(var g=System.Drawing.Graphics.FromImage(bmp)){g.FillRectangle(System.Drawing.Brushes.DimGray,0,0,150,35);g.DrawString("frame "+i,System.Drawing.SystemFonts.DefaultFont,System.Drawing.Brushes.White,2,2);using(var brush=new System.Drawing.SolidBrush(System.Drawing.Color.FromArgb(i%256,(i/256)%256,(i*7)%256)))g.FillRectangle(brush,600,320,32,32);}
     string rel="assets/frame-"+i.ToString("D5")+".png",p=Path.Combine(root,rel);bmp.Save(p,System.Drawing.Imaging.ImageFormat.Png);s.Data.assets.Add(new Asset{path=rel,sha256=Codec.HashFile(p),bytes=new FileInfo(p).Length});
     s.Add("Frame",new Dictionary<string,object>{{"video_id",vs[i<count/2?0:1].id},{"asset_path",rel},{"width",640},{"height",360},{"pts_us",(long)i*100000},{"source_timestamp_100ns",(long)i*1000000},{"time_source","media_foundation_sample"},{"state","unannotated"}});
     if(i%250==0)File.WriteAllText(Path.Combine(root,"fixture-progress.txt"),i+" / "+count);
    }
   }
   s.Save();return s;
  }
  public int HotfixBenchmark(string output,string label,int samples){
   System.Threading.SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(Dispatcher));
   Process.GetCurrentProcess().PriorityClass=ProcessPriorityClass.BelowNormal;
   Directory.CreateDirectory(output);var sets=new List<object>();
   try{
    foreach(int count in new[]{900,2708,10000}){
     string only=Environment.GetEnvironmentVariable("IVAD_BENCH_COUNT");if(!String.IsNullOrEmpty(only)&&only!=count.ToString())continue;
     File.AppendAllText(Path.Combine(output,"progress.log"),label+" fixture "+count+Environment.NewLine);
     var s=Fixture(Path.Combine(output,"fixtures",count.ToString()),count);videoFrames.ItemsSource=null;Use(s);Navigate("标注与审核");
     var content=(FrameworkElement)Content;content.Measure(new Size(1400,850));content.Arrange(new Rect(0,0,1400,850));content.UpdateLayout();frames.SelectedIndex=0;
     long initialSequence=s.Data.sequence;int initialEntities=s.Data.entities.Count;var rows=new List<object>();var times=new List<double>();
     var rendered=new System.Windows.Media.Imaging.RenderTargetBitmap(1400,850,96,96,System.Windows.Media.PixelFormats.Pbgra32);
     for(int i=0;i<samples;i++){
      Work.ResetMetrics();var clock=Stopwatch.StartNew();saveAdvanceCommand.Execute(null,this);WaitHotfix();var layoutClock=Stopwatch.StartNew();content.UpdateLayout();double layoutMs=layoutClock.Elapsed.TotalMilliseconds;var renderClock=Stopwatch.StartNew();rendered.Clear();rendered.Render(content);double renderMs=renderClock.Elapsed.TotalMilliseconds;clock.Stop();
      double ms=clock.Elapsed.TotalMilliseconds;times.Add(ms);rows.Add(new{sample=i,total_ms=ms,sha256_file_calls=Work.HashCalls,sha256_file_bytes=Work.HashBytes,sha256_file_ms=Work.HashTicks*1000.0/Stopwatch.Frequency,layout_ms=layoutMs,render_ms=renderMs,selected_frame=frame.id,transaction_ms=Store.LastCommitMs,patch_ms=Store.LastPatchMs,conflict_ms=Store.LastConflictMs,current_asset_ms=Store.LastAssetMs,state_write_ms=Store.LastStateMs,next_query_ms=lastLookupMs,list_update_ms=lastListMs,next_decode_ms=lastDecodeMs,memory_sha_calls=Work.MemoryHashCalls,memory_sha_bytes=Work.MemoryHashBytes,memory_sha_ms=Work.MemoryHashTicks*1000.0/Stopwatch.Frequency});
      File.AppendAllText(Path.Combine(output,label+"-samples.jsonl"),Codec.Json(new{frames=count,sample=i,total_ms=ms,hash_calls=Work.HashCalls,hash_bytes=Work.HashBytes})+Environment.NewLine);
     }
     var scaleChecks=new List<string>();var filterClock=Stopwatch.StartNew();
     frameVideoFilter.SelectedIndex=1;Check(frames.Items.Count==count/2,"scale video 1 count");frameVideoFilter.SelectedIndex=2;Check(frames.Items.Count==count-count/2,"scale video 2 count");frameVideoFilter.SelectedIndex=0;
     frameStateFilter.SelectedIndex=1;Check(frames.Items.Count==orderedFrames.Count(f=>f.Text("state")=="unannotated"),"scale pending count");frameStateFilter.SelectedIndex=2;Check(frames.Items.Count==orderedFrames.Count(f=>f.Text("state")=="normal"),"scale confirmed count");frameStateFilter.SelectedIndex=0;double filterMs=filterClock.Elapsed.TotalMilliseconds;scaleChecks.Add("video/status filters at actual scale");
     var batchIds=orderedFrames.Where(f=>f.Text("state")=="unannotated").Take(3).Select(f=>f.id).ToArray();frames.SelectedItems.Clear();foreach(var id in batchIds)frames.SelectedItems.Add(frameChoices[id]);Work.ResetMetrics();var batchClock=Stopwatch.StartNew();BatchNormal();WaitHotfix();double batchMs=batchClock.Elapsed.TotalMilliseconds;long batchHashCalls=Work.HashCalls;Check(batchHashCalls==1&&batchIds.All(id=>store.Find(id).Text("state")=="normal"),"scale batch metadata only");Work.ResetMetrics();var undoClock=Stopwatch.StartNew();UndoNormalBatch();WaitHotfix();double undoMs=undoClock.Elapsed.TotalMilliseconds;long undoHashCalls=Work.HashCalls;Check(undoHashCalls==1&&batchIds.All(id=>store.Find(id).Text("state")=="unannotated"),"scale undo metadata only");scaleChecks.Add("programmatic multi-selection batch and undo; each only hashes manifest");
     times.Sort();sets.Add(new{scale_checks=scaleChecks,filter_switch_total_ms=filterMs,batch_3_ms=batchMs,undo_3_ms=undoMs,batch_file_hash_calls=batchHashCalls,undo_file_hash_calls=undoHashCalls,peak_working_set_bytes=Process.GetCurrentProcess().PeakWorkingSet64,frames=count,initial_sequence=initialSequence,initial_entities=initialEntities,samples=samples,p50_ms=times[(int)Math.Ceiling(samples*.50)-1],p95_ms=times[(int)Math.Ceiling(samples*.95)-1],unique_images=s.Data.assets.Count(a=>a.path.EndsWith(".png")),image_bytes=s.Data.assets.Where(a=>a.path.EndsWith(".png")).Sum(a=>a.bytes),width=640,height=360,cache="OS warm after fixture hashing/open; application begins empty, sequential next frames; no OS cache flush",rows=rows});
     File.WriteAllText(Path.Combine(output,label+".json"),Codec.Json(new{label=label,scope="actual in-process WPF routed Ctrl+S command + asynchronous commit + next image decode + layout + offscreen RenderTargetBitmap; no native input/window/compositor",sqlite="N/A: IDS JSON store",sets=sets}));
    }
    ticker.Stop();return 0;
   }catch(Exception e){File.WriteAllText(Path.Combine(output,label+".error.txt"),e.ToString());ticker.Stop();return 1;}
  }
 }
}
