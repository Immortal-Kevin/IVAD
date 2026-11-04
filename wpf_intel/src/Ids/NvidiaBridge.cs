// Private NVIDIA integration. No public distribution license granted.
// NVIDIA integration layer; upstream Intel IDS business rules remain unchanged.
using System;
using System.IO;
using System.Diagnostics;
using System.Collections.Generic;
namespace Ivad.Ids {
 public static class NvidiaBridge {
  static Process worker;static readonly object sync=new object();
  public static bool Enabled {get{return Environment.GetEnvironmentVariable("IVAD_NVIDIA_BRIDGE")=="1";}}
  public static string Call(Dictionary<string,object> request){lock(sync){
   if(String.IsNullOrEmpty(Environment.GetEnvironmentVariable("IVAD_IPC_TOKEN")))Environment.SetEnvironmentVariable("IVAD_IPC_TOKEN",Guid.NewGuid().ToString("N")+Guid.NewGuid().ToString("N"));
   request["protocol"]="ivad-local/1";request["token"]=Environment.GetEnvironmentVariable("IVAD_IPC_TOKEN");
   if(worker==null||worker.HasExited){
    string python=Environment.GetEnvironmentVariable("IVAD_NVIDIA_PYTHON");
    if(String.IsNullOrEmpty(python))throw new IOException("NVIDIA Python未配置");
    worker=new Process{StartInfo=new ProcessStartInfo{FileName=python,Arguments="-X utf8 -m ivad_app.services.ids_bridge",UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true}};
    worker.StartInfo.StandardOutputEncoding=System.Text.Encoding.UTF8;
    worker.Start();worker.ErrorDataReceived+=(s,e)=>{};worker.BeginErrorReadLine();
   }
   worker.StandardInput.WriteLine(Codec.Json(request));worker.StandardInput.Flush();
   string line=worker.StandardOutput.ReadLine();if(line==null)throw new IOException("NVIDIA数据库桥接进程已退出");
   var response=Codec.Parse<Dictionary<string,object>>(line);
   if(!(bool)response["ok"])throw new IOException(Convert.ToString(response["error"]));
   return Convert.ToString(response["result"]);
  }}
  public static void Hydrate(string root){if(Enabled)Call(new Dictionary<string,object>{{"action","hydrate"},{"root",root}});}
  public static void Commit(string root,string file,string expected){if(Enabled)Call(new Dictionary<string,object>{{"action","commit"},{"root",root},{"file",file},{"expected",expected}});}
 }
}
