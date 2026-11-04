// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Diagnostics;
using Ivad.Ids;
namespace Ivad.Annotator {
 public static class VideoJobs {
  public static string Run(string root,string video,double[] options,Action<string> log,string workerExecutable=null){
   Work.Check();
   string job=Path.GetDirectoryName(Rules.SafePath(root,".jobs/"+Guid.NewGuid().ToString("N")+"/result.txt"));Directory.CreateDirectory(job);
   string cancelFile=Path.Combine(job,"cancel"),progress=Path.Combine(job,"progress.txt"),result=Path.Combine(job,"result.txt"),journal=Path.Combine(job,"created.txt");
   var timer=Stopwatch.StartNew();bool requested=false,started=false;long cancelAt=0;
   using(var p=new Process{StartInfo=new ProcessStartInfo{FileName=workerExecutable??System.Reflection.Assembly.GetEntryAssembly().Location,Arguments="--extract \""+root+"\" "+video+" "+String.Join(" ",options.Select(x=>x.ToString("R",System.Globalization.CultureInfo.InvariantCulture)))+" \""+job+"\"",UseShellExecute=false,CreateNoWindow=true}}){
    try{
     p.Start();started=true;
     while(!p.WaitForExit(200)){
      try{Work.Check();if(File.Exists(progress)){try{Work.Report(File.ReadAllText(progress));}catch(IOException){}}string framesProgress=Path.Combine(job,"frames-progress.txt");if(File.Exists(framesProgress)){try{Work.Report(File.ReadAllText(framesProgress));}catch(IOException){}}}
      catch(OperationCanceledException){if(!requested){requested=true;cancelAt=timer.ElapsedMilliseconds;File.WriteAllText(cancelFile,"cancel");}}
      if(timer.Elapsed.TotalSeconds>610||(requested&&timer.ElapsedMilliseconds-cancelAt>10000)){
       p.Kill();p.WaitForExit();if(requested)throw new OperationCanceledException("解码器未及时响应取消，已停止进程并清理任务文件；源视频保留。");throw new TimeoutException("解码进程超时；源视频和已提交标注保留，可缩小范围重试。");
      }
     }
     string message=File.Exists(result)?File.ReadAllText(result):"解码进程没有结果";
     if(p.ExitCode==2)throw new OperationCanceledException("抽帧已取消；源视频保留，可重试。");if(p.ExitCode!=0)throw new IOException(message);
     var match=System.Text.RegularExpressions.Regex.Match(message,"^PASS extracted=([0-9]+)");if(!match.Success)throw new InvalidDataException("无法验证抽帧进程结果");int count=Int32.Parse(match.Groups[1].Value);
     Work.Report("IVAD_PROGRESS|抽帧完成，已保存|"+count+"|"+count);
     return "本次新增 "+count+" 帧。"+(count==(int)options[3]?"达到本次新增帧上限；再次执行可继续抽取，已有标注不变。":count==0?"所选范围没有新增帧，请检查范围或已有帧。":"");
    }finally{
     if(started&&!p.HasExited){File.WriteAllText(cancelFile,"cancel");if(!p.WaitForExit(10000)){p.Kill();p.WaitForExit();}}
     if(log!=null)log("EXTRACT elapsed_ms="+timer.ElapsedMilliseconds+"; "+(File.Exists(result)?File.ReadAllText(result):"no worker result"));
     // Only this process's journal is used. Unrelated/old jobs are never swept.
     if(File.Exists(journal))Store.CleanupOwned(root,File.ReadAllLines(journal));
     if(Directory.Exists(job))Directory.Delete(job,true);
    }
   }
  }
 }
}
