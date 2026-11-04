// Private NVIDIA integration. No public distribution license granted.
using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using System.Collections.Generic;
using Ivad.Ids;
namespace Ivad.Annotator {
 public static class NvidiaMedia {
  public sealed class Result {public string path;public Dictionary<string,object> data;}
  public static int Extract(string root,string video,double seconds,int maximum,double from,double until,bool plan,int total){
   var store=new Store(root);var v=store.Find(video);
   string stage=Path.Combine(root,".nvidia-mf-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(stage);
   var request=new {source=Rules.SafePath(root,v.Text("asset_path")),stage=stage,video=video,seconds=seconds,maximum=maximum,start=from,end=until,plan=plan,seen=store.Data.entities.Where(e=>e.kind=="Frame"&&e.Text("video_id")==video).Select(e=>(long)e.Number("source_timestamp_100ns")).ToArray()};
   string input=Path.Combine(stage,"request.json");File.WriteAllText(input,Codec.Json(request));
   using(var process=new Process{StartInfo=new ProcessStartInfo{FileName=Environment.GetEnvironmentVariable("IVAD_NVIDIA_PYTHON"),Arguments="-X utf8 -m ivad_app.services.ids_media_bridge \""+input+"\"",UseShellExecute=false,CreateNoWindow=true}}){
    try{process.Start();bool cancelled=false;var watch=Stopwatch.StartNew();long cancelAt=0;
     while(!process.WaitForExit(100)){
      try{Work.Check();string progress=Path.Combine(stage,"progress");if(File.Exists(progress))Work.Report("IVAD_PROGRESS|NVIDIA Media Foundation 抽帧|"+File.ReadAllText(progress)+"|"+total);}
      catch(OperationCanceledException){if(!cancelled){cancelled=true;cancelAt=watch.ElapsedMilliseconds;File.WriteAllText(Path.Combine(stage,"cancel"),"cancel");}}
      if((cancelled&&watch.ElapsedMilliseconds-cancelAt>5000)||watch.Elapsed.TotalSeconds>580){process.Kill();process.WaitForExit();throw new OperationCanceledException("MF任务停止；未提交帧");}
     }
     if(cancelled||process.ExitCode==2)throw new OperationCanceledException("MF抽帧取消");
     if(process.ExitCode!=0)throw new IOException(File.Exists(Path.Combine(stage,"error.txt"))?File.ReadAllText(Path.Combine(stage,"error.txt")):"NVIDIA MF worker failed");
     var frames=Codec.Parse<Result[]>(File.ReadAllText(Path.Combine(stage,"result.json")));
     if(plan)return frames.Length;
     if(total>=0&&frames.Length!=total)throw new IOException("抽帧数量发生变化，未提交");
     foreach(var frame in frames){Work.Check();var a=store.CopyAsset(frame.path);frame.data["asset_path"]=a.path;var added=store.Add("Frame",frame.data);store.Revise(added,"nvidia-mf");}
     if(frames.Length>0)store.Save();return frames.Length;
    }catch{store.AbortAssets();throw;}finally{if(Directory.Exists(stage))Directory.Delete(stage,true);}
   }
  }
 }
}
