// SPDX-License-Identifier: Apache-2.0
// Opt-in diagnostics in the shipped application; all fixtures are generated locally.
// Internal WPF command/service checks are NOT native mouse or keyboard acceptance.
using System;
using System.IO;
using System.Text;
using System.Linq;
using System.Diagnostics;
using System.Reflection;
using System.Security.Principal;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Threading;
using Ivad.Ids;
namespace Ivad.Annotator {
 internal static class DeploymentChecks {
 static byte[] Bytes(Action<BinaryWriter> a){using(var s=new MemoryStream()){using(var w=new BinaryWriter(s,Encoding.ASCII,true))a(w);return s.ToArray();}}
 static void Chunk(BinaryWriter w,string id,byte[] data){w.Write(Encoding.ASCII.GetBytes(id));w.Write(data.Length);w.Write(data);if((data.Length&1)!=0)w.Write((byte)0);}
 static byte[] List(string type,Action<BinaryWriter> a){return Bytes(w=>{w.Write(Encoding.ASCII.GetBytes(type));a(w);});}
 internal static void Avi(string path){int width=64,height=48,count=6,fps=2,size=width*height*3;
  var header=List("hdrl",w=>{
   Chunk(w,"avih",Bytes(x=>{x.Write(1000000/fps);x.Write(size*fps);x.Write(0);x.Write(0);x.Write(count);x.Write(0);x.Write(1);x.Write(size);x.Write(width);x.Write(height);for(int i=0;i<4;i++)x.Write(0);}));
   Chunk(w,"LIST",List("strl",x=>{
    Chunk(x,"strh",Bytes(y=>{y.Write(Encoding.ASCII.GetBytes("vidsDIB "));y.Write(0);y.Write((short)0);y.Write((short)0);y.Write(0);y.Write(1);y.Write(fps);y.Write(0);y.Write(count);y.Write(size);y.Write(-1);y.Write(0);y.Write((short)0);y.Write((short)0);y.Write((short)width);y.Write((short)height);}));
    Chunk(x,"strf",Bytes(y=>{y.Write(40);y.Write(width);y.Write(height);y.Write((short)1);y.Write((short)24);y.Write(0);y.Write(size);for(int i=0;i<4;i++)y.Write(0);}));
   }));
  });
  var movi=List("movi",w=>{for(int f=0;f<count;f++){byte[] p=new byte[size];for(int i=0;i<size;i+=3){p[i]=(byte)(f*30);p[i+1]=80;p[i+2]=200;}Chunk(w,"00db",p);}});
  File.WriteAllBytes(path,Bytes(w=>Chunk(w,"RIFF",List("AVI ",x=>{Chunk(x,"LIST",header);Chunk(x,"LIST",movi);})))) ;
 }

  internal static int CrashWriter(string root,string ready){
   var s=new Store(root);var frame=s.Data.entities.First(x=>x.kind=="Frame");
   // Pause in the actual persistence path after writing/flushing the new manifest,
   // before atomic replacement. The parent terminates only this test child.
   Work.Configure(()=>false,message=>{if(message.StartsWith("SHA256 project.ids.json.")&&message.Contains(".tmp")){
    File.WriteAllText(ready,"manifest temp written; old committed manifest intact");System.Threading.Thread.Sleep(30000);
   }});
   s.Review(frame.id,"unknown","unknown","crash-probe");return 0;
  }
 }
 public sealed partial class MainWindow {
  public int RunDeploymentChecks(string directory,bool reopen){
   System.Threading.SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(Dispatcher));
   string output=Path.GetFullPath(directory);if(!reopen&&Directory.Exists(output)&&Directory.EnumerateFileSystemEntries(output).Any())throw new IOException("部署自检只允许使用全新空目录");Directory.CreateDirectory(output);
   var results=new List<object>();int failed=0;string log=Path.Combine(output,reopen?"reopen.log":"execution.log");
   Action<string,Action> test=(name,action)=>{File.AppendAllText(log,"START "+name+Environment.NewLine);try{action();results.Add(new{name=name,status="PASS",mode="packaged executable; actual filesystem/media or in-process WPF; NOT native GUI"});File.AppendAllText(log,"PASS "+name+Environment.NewLine);}catch(Exception e){failed++;results.Add(new{name=name,status="FAIL",error=e.ToString()});File.AppendAllText(log,"FAIL "+name+" "+e+Environment.NewLine);}};
   string root=Path.Combine(output,"数据 空间"),project=Path.Combine(root,"测试厂区","测试设备","测试摄像头"),receiver=Path.Combine(output,"重新导入"),package=Path.Combine(output,"测试厂区-测试设备-测试摄像头.ids");
   test("runtime/non-elevated-x64-and-clean-environment",()=>{
    Check(Environment.Is64BitProcess,"x64 process");Check(!new WindowsPrincipal(WindowsIdentity.GetCurrent()).IsInRole(WindowsBuiltInRole.Administrator),"ordinary user token");
    Check(String.IsNullOrEmpty(Environment.GetEnvironmentVariable("VIRTUAL_ENV"))&&String.IsNullOrEmpty(Environment.GetEnvironmentVariable("PYTHONPATH")),"no Python environment");
   });
   if(!reopen){
    test("project/create-via-background-ui-handler",()=>{masterRoot.Text=root;projectName.Text="便携测试项目";siteName.Text="测试厂区";equipmentName.Text="测试设备";cameraName.Text="测试摄像头";OpenCameraProject();AwaitOperation();Check(store.Root==project&&File.Exists(store.Manifest),"new project in chosen data directory");});
    test("video/generate-and-import-Chinese-long-filename",()=>{
     string video=Path.Combine(output,"非敏感测试视频 带空格 "+new string('长',100)+".avi");DeploymentChecks.Avi(video);string camera=Selected(cameras);
     Run("部署测试导入",()=>{var s=new Store(project);s.ImportVideo(video,camera);return s;},Use);AwaitOperation();Check(store.Data.entities.Count(x=>x.kind=="Video")==1,"real synthetic AVI imported");
     File.WriteAllText(Path.Combine(output,"path-lengths.json"),Codec.Json(new{video_path_characters=video.Length,file_name_characters=Path.GetFileName(video).Length,contains_chinese=true,contains_spaces=true}));
    });
    test("video/extract-by-relocated-executable-child",()=>{
     string video=store.Data.entities.First(x=>x.kind=="Video").id;
     Run("部署测试抽帧",()=>{ExtractProcess(project,video,new[]{.5,0,3,10.0});return new Store(project);},Use);AwaitOperation();
     Check(frames.Items.Count==6&&store.Data.entities.First(x=>x.kind=="Frame"&&x.Number("pts_us")==500000).Number("source_timestamp_100ns")==5000000,"six frames and exact real PTS");Check(Directory.GetDirectories(Path.Combine(project,".jobs")).Length==0,"worker temporary files cleaned");
    });
    test("annotation/rectangle-and-CtrlS-command-abnormal",()=>{
     Navigate("标注与审核");var fault=store.Add("Fault",new Dictionary<string,object>{{"name","测试故障"},{"taxonomy_version",1}});store.Save();Refresh();frames.SelectedIndex=0;string id=frame.id;
     Commit(s=>s.AddAnnotation(id,fault.id,"box",new[]{2.0,3,40,35},false));AwaitOperation();shape.SelectedIndex=3;saveAdvanceCommand.Execute(null,this);AwaitOperation();
     Check(new Store(project).Find(id).Text("state")=="abnormal"&&frames.SelectedIndex==1&&shape.SelectedIndex==3,"rectangle persisted; command saves abnormal and advances");
    });
    test("annotation/CtrlS-command-empty-normal",()=>{string id=frame.id;Check(!Shapes().Any(x=>x.kind=="Annotation"),"no annotation");saveAdvanceCommand.Execute(null,this);AwaitOperation();Check(new Store(project).Find(id).Text("state")=="normal"&&frames.SelectedIndex==2,"empty frame normal and advances");});
    test("project/reopen-and-IDS-export-import-hashes",()=>{
     string before=Codec.Fingerprint(store.Data);Use(new Store(project));Check(Codec.Fingerprint(store.Data)==before,"reopen persistent");
     Run("部署测试导出",()=>{Packages.Export(new Store(project),package,null);return package;},x=>{});AwaitOperation();
     Run("部署测试导入",()=>Packages.Import(package,receiver),Use);AwaitOperation();Rules.VerifyAssets(store.Data,receiver);Check(Codec.Fingerprint(store.Data)==before,"all metadata and asset hashes equal");
     var repeated=Packages.Import(package,receiver);Check(Codec.Fingerprint(repeated.Data)==before,"repeat import idempotent");File.WriteAllText(Path.Combine(output,"expected-fingerprint.txt"),before);
    });
    test("storage/hard-exit-before-atomic-replace-and-recovery",()=>{
     string crash=Path.Combine(output,"异常退出专用项目"),ready=Path.Combine(output,"crash-ready.txt");var fixture=Packages.Import(package,crash);string before=Codec.Fingerprint(fixture.Data);
     var info=new ProcessStartInfo(Assembly.GetEntryAssembly().Location,"--deployment-crash \""+crash+"\" \""+ready+"\""){UseShellExecute=false,CreateNoWindow=true,WorkingDirectory=output};
     using(var child=Process.Start(info)){try{var wait=Stopwatch.StartNew();while(!File.Exists(ready)&&!child.HasExited&&wait.ElapsedMilliseconds<15000)System.Threading.Thread.Sleep(50);Check(File.Exists(ready)&&!child.HasExited,"child paused after actual temp manifest write");child.Kill();Check(child.WaitForExit(5000),"own test process terminated");}finally{if(!child.HasExited){child.Kill();child.WaitForExit(5000);}}}
     var recovered=new Store(crash);Rules.VerifyAssets(recovered.Data,crash);Check(Codec.Fingerprint(recovered.Data)==before,"last committed data recovered after hard exit");Check(Directory.GetFiles(crash,"project.ids.json.*.tmp").Length==1,"uncommitted temp retained for diagnosis, never loaded");
     var f=recovered.Data.entities.First(x=>x.kind=="Frame");recovered.Review(f.id,"abnormal","confirmed","recovery-test");Check(new Store(crash).Find(f.id).Text("state")=="abnormal","write lock released; new save works");
    });
    test("storage/write-denial-is-reported-no-overwrite",()=>{
     var s=new Store(project);string before=Codec.Fingerprint(s.Data);bool denied=false;
     using(var hold=new FileStream(Path.Combine(project,".write.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){try{s.Review(s.Data.entities.First(x=>x.kind=="Frame").id,"unknown","unknown","denied-test");}catch(IOException){denied=true;}}
     Check(denied&&Codec.Fingerprint(new Store(project).Data)==before,"write contention rejected without changes; ACL-denied directory separately NOT TESTED");
    });
   }else{
    test("restart/reopen-data-and-package-from-new-process",()=>{string expected=File.ReadAllText(Path.Combine(output,"expected-fingerprint.txt"));Use(new Store(project));Navigate("标注与审核");Check(Codec.Fingerprint(store.Data)==expected,"original data stable across process restart");Check(Workflow.Detect(root).Single().Root==project,"directory detection finds saved camera");var imported=new Store(receiver);Rules.VerifyAssets(imported.Data,receiver);Check(Codec.Fingerprint(imported.Data)==expected,"imported data stable");Check(frames.Items.Count==6&&frames.Items.Cast<Choice>().Any(x=>x.Name.Contains("异常"))&&frames.Items.Cast<Choice>().Any(x=>x.Name.Contains("正常")),"saved states visible in frame list");});
   }
   test("runtime/loaded-managed-assemblies-only-package-or-Windows",()=>{
    string windows=Environment.GetFolderPath(Environment.SpecialFolder.Windows)+Path.DirectorySeparatorChar,application=AppDomain.CurrentDomain.BaseDirectory;
    var loaded=AppDomain.CurrentDomain.GetAssemblies().Where(a=>!a.IsDynamic).Select(a=>new{name=a.GetName().Name,path=a.Location}).ToArray();
    Check(loaded.All(a=>a.path.StartsWith(windows,StringComparison.OrdinalIgnoreCase)||a.path.StartsWith(application,StringComparison.OrdinalIgnoreCase)),"no developer-directory managed dependency");
    File.WriteAllText(Path.Combine(output,reopen?"reopen-runtime.json":"runtime.json"),Codec.Json(new{executable=Assembly.GetEntryAssembly().Location,working_directory=Environment.CurrentDirectory,path=Environment.GetEnvironmentVariable("PATH"),clr=Environment.Version.ToString(),os=Environment.OSVersion.VersionString,assemblies=loaded,modules=Process.GetCurrentProcess().Modules.Cast<ProcessModule>().Select(m=>m.FileName).ToArray()}));
   });
   ticker.Stop();File.WriteAllText(Path.Combine(output,reopen?"reopen-results.json":"results.json"),Codec.Json(new{passed=results.Count-failed,failed=failed,gui_status="NOT TESTED",scope="Isolated packaged EXE, actual filesystem/worker/media; WPF routed command is not physical Ctrl+S; no native mouse input",tests=results}));return failed==0?0:1;
  }
 }
}
