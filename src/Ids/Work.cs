// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Security.Cryptography;

namespace Ivad.Ids {
 // The context is installed on the worker thread, never on the WPF dispatcher.
 public static class Work {
  [ThreadStatic] static Func<bool> cancelled;
  [ThreadStatic] static Action<string> progress;
  [ThreadStatic] static Action<string> created;
  public static void Configure(Func<bool> cancel,Action<string> report,Action<string> createdFile=null){cancelled=cancel;progress=report;created=createdFile;}
  public static void Created(string path){if(created!=null)created(path);}
  public static void Check(){if(cancelled!=null&&cancelled())throw new OperationCanceledException("任务已取消，未提交的更改已回滚");}
  public static void Report(string message){Check();if(progress!=null)progress(message);}
  public static string Copy(Stream source,Stream target,string label,long total){
   byte[] buffer=new byte[1024*1024];long done=0;int n;
   using(var hash=SHA256.Create()){
    while(true){Check();n=source.Read(buffer,0,buffer.Length);if(n==0)break;done+=n;if(done>total)throw new InvalidDataException("实际流长度超过声明大小");target.Write(buffer,0,n);hash.TransformBlock(buffer,0,n,null,0);Report(label+" "+done+" / "+total+" bytes");}
    if(done!=total)throw new InvalidDataException("实际流长度与声明大小不符");hash.TransformFinalBlock(new byte[0],0,0);return BitConverter.ToString(hash.Hash).Replace("-","").ToLowerInvariant();
   }
  }
  public static string HashFile(string path){
   using(var input=File.OpenRead(path))using(var hash=SHA256.Create()){
    byte[] buffer=new byte[1024*1024];int n;long done=0;
    while(true){Check();n=input.Read(buffer,0,buffer.Length);if(n==0)break;hash.TransformBlock(buffer,0,n,null,0);done+=n;Report("SHA256 "+Path.GetFileName(path)+" "+done+" / "+input.Length+" bytes");}
    hash.TransformFinalBlock(new byte[0],0,0);return BitConverter.ToString(hash.Hash).Replace("-","").ToLowerInvariant();
   }
  }
 }
}
