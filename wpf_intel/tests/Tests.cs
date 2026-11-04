// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Collections.Generic;
using Ivad.Ids;
using Ivad.Annotator;
using Ivad.Full;
partial class Tests {
 static int pass,fail;static List<object> results=new List<object>();
 static void Test(string name,Action action){try{action();pass++;results.Add(new{name=name,status="PASS",mode="actual"});Console.WriteLine("PASS "+name);}catch(Exception e){fail++;results.Add(new{name=name,status="FAIL",error=e.ToString(),mode="actual"});Console.WriteLine("FAIL "+name+" "+e);}}
 static void Assert(bool b,string s){if(!b)throw new Exception(s);}
 static void Reject(Action a){bool bad=false;try{a();}catch{bad=true;}Assert(bad,"Expected rejection");}
 static byte[] Bytes(Action<BinaryWriter> a){using(var s=new MemoryStream()){using(var w=new BinaryWriter(s,Encoding.ASCII,true))a(w);return s.ToArray();}}
 static void Chunk(BinaryWriter w,string id,byte[] data){w.Write(Encoding.ASCII.GetBytes(id));w.Write(data.Length);w.Write(data);if((data.Length&1)!=0)w.Write((byte)0);}
 static byte[] List(string type,Action<BinaryWriter> a){return Bytes(w=>{w.Write(Encoding.ASCII.GetBytes(type));a(w);});}
 static void Avi(string path){int width=64,height=48,count=6,fps=2,size=width*height*3;
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
 [STAThread] static int Main(string[] args){
  string root=Path.GetFullPath(args[0]);Directory.CreateDirectory(root);root=Path.Combine(root,DateTime.UtcNow.ToString("yyyyMMddTHHmmss")+"-"+Guid.NewGuid().ToString("N").Substring(0,8));Directory.CreateDirectory(root);
  Store s=null;Entity camera=null,video=null,frame=null,fault=null;string full=Path.Combine(root,"full.ids.zip"),delta=Path.Combine(root,"delta.ids.zip");Document baseline=null;
  Test("project/create-reopen",()=>{s=Store.Create(Path.Combine(root,"source"),"测试项目","测试厂区");var d=new Store(s.Root);Assert(d.Data.project_id==s.Data.project_id,"stable ID");});
  Test("entities/equipment-camera-fault",()=>{var e=s.Add("Equipment",new Dictionary<string,object>{{"name","输送机"},{"project_id",s.Data.project_id}});camera=s.Add("Camera",new Dictionary<string,object>{{"name","相机1"},{"equipment_id",e.id}});fault=s.Add("Fault",new Dictionary<string,object>{{"name","测试故障"},{"taxonomy_version",1}});s.Save();});
  Test("video/import-real-generated-avi",()=>{string avi=Path.Combine(root,"sample.avi");Avi(avi);video=s.ImportVideo(avi,camera.id);Assert(File.Exists(Rules.SafePath(s.Root,video.Text("asset_path"))),"copy");});
  Test("video/media-foundation-extract-real-PTS",()=>{int n=Media.Extract(s.Root,video.id,.5,10);s.Reload();var fs=s.Data.entities.Where(e=>e.kind=="Frame").ToList();Assert(n==6&&fs.Count==6,"expected6 got"+n);Assert(fs[1].Number("source_timestamp_100ns")==5000000,"actual PTS");Assert(fs[1].Number("pts_us")==500000,"microseconds");frame=fs[0];});
  Test("video/reextract-idempotent",()=>{Assert(Media.Extract(s.Root,video.id,.5,10)==0,"no duplicate frames");});
  Test("annotation/box-save",()=>{s.AddAnnotation(frame.id,fault.id,"box",new[]{2.0,3.0,40.0,35.0},false);Assert(new Store(s.Root).Data.entities.Any(e=>e.kind=="Annotation"),"persisted");});
  Test("annotation/polygon-and-ROI",()=>{s.AddAnnotation(frame.id,fault.id,"polygon",new[]{1.0,1,10,1,10,10},false);s.AddAnnotation(frame.id,"","polygon",new[]{0.0,0,50,0,50,40},true);});
  Test("review/state-and-history",()=>{s.Review(frame.id,"abnormal","confirmed","reviewer");Assert(s.Data.entities.Any(e=>e.kind=="Revision"&&e.Text("entity_id")==frame.id),"history");});
  Test("validation/duplicate-ID",()=>{var d=Codec.Clone(s.Data);d.entities.Add(d.entities[0]);Reject(()=>Rules.Validate(d));});
  Test("validation/dangling-reference",()=>{var d=Codec.Clone(s.Data);d.entities.First(e=>e.kind=="Video").data["camera_id"]=Guid.NewGuid().ToString();Reject(()=>Rules.Validate(d));});
  Test("validation/outside-coordinate",()=>{var d=Codec.Clone(s.Data);d.entities.First(e=>e.kind=="Annotation").data["points"]=new[]{-1.0,0,10,10};Reject(()=>Rules.Validate(d));});
  Test("validation/unknown-state",()=>{var d=Codec.Clone(s.Data);d.entities.First(e=>e.kind=="Frame").data["state"]="probably-normal";Reject(()=>Rules.Validate(d));});
  Test("package/full-roundtrip",()=>{Packages.Export(s,full,null);baseline=Codec.Clone(s.Data);var restored=Packages.Import(full,Path.Combine(root,"receiver"));Assert(Codec.Fingerprint(restored.Data)==Codec.Fingerprint(s.Data),"lossless");Rules.VerifyAssets(restored.Data,restored.Root);});
  Test("package/snapshot-immutable",()=>{Reject(()=>Packages.Export(s,full,null));});
  Test("package/incremental-roundtrip",()=>{s.Review(frame.id,"unknown","needs_work","reviewer2");Packages.Export(s,delta,baseline);var r=Packages.Import(delta,Path.Combine(root,"receiver"));Assert(Codec.Fingerprint(r.Data)==Codec.Fingerprint(s.Data),"delta");});
  Test("package/bidirectional-incremental",()=>{var r=new Store(Path.Combine(root,"receiver"));var b=Codec.Clone(r.Data);r.Review(frame.id,"normal","confirmed","remote-reviewer");string p=Path.Combine(root,"return.ids.zip");Packages.Export(r,p,b);s=Packages.Import(p,s.Root);Assert(Codec.Fingerprint(s.Data)==Codec.Fingerprint(r.Data),"bidirectional");});
  Test("package/conflict-no-change",()=>{string before=Codec.HashFile(s.Manifest);Reject(()=>Packages.Import(delta,s.Root));Assert(Codec.HashFile(s.Manifest)==before,"unchanged");});
  Test("package/corrupt-hash-rollback",()=>{string bad=Path.Combine(root,"bad.zip");File.Copy(full,bad);using(var z=ZipFile.Open(bad,ZipArchiveMode.Update)){var a=z.Entries.First(e=>e.FullName.StartsWith("assets/"));string n=a.FullName;a.Delete();var e2=z.CreateEntry(n);using(var w=new StreamWriter(e2.Open()))w.Write("corrupt");}string target=Path.Combine(root,"failed-import");Reject(()=>Packages.Import(bad,target));Assert(!File.Exists(Path.Combine(target,"project.ids.json")),"rollback");Assert(!Directory.Exists(Path.Combine(target,"assets")),"no assets committed");});
  Test("package/path-traversal-rejected",()=>{string p=Path.Combine(root,"evil.zip");using(var z=ZipFile.Open(p,ZipArchiveMode.Create)){z.CreateEntry("../escaped.txt");}Reject(()=>Packages.Import(p,Path.Combine(root,"safe")));Assert(!File.Exists(Path.Combine(root,"escaped.txt")),"no escape");});
  Test("package/undeclared-files-rejected",()=>{string p=Path.Combine(root,"extra.zip");File.Copy(full,p);using(var z=ZipFile.Open(p,ZipArchiveMode.Update))z.CreateEntry("secret.txt");Reject(()=>Packages.Import(p,Path.Combine(root,"extra")));});
  Test("package/case-collision-rejected",()=>{string p=Path.Combine(root,"case.zip");using(var z=ZipFile.Open(p,ZipArchiveMode.Create)){z.CreateEntry("a.txt");z.CreateEntry("A.txt");}Reject(()=>Packages.Import(p,Path.Combine(root,"case")));});
  Test("storage/concurrent-writer-conflict",()=>{var stale=new Store(s.Root);s.Review(frame.id,"unknown","unknown","a");Reject(()=>stale.Save());});
  Test("full/adapter-rejects-unsupported-polygon",()=>{s.Review(frame.id,"abnormal","confirmed","a");Reject(()=>CocoAdapter.Export(s,Path.Combine(root,"coco-reject")));Assert(!Directory.Exists(Path.Combine(root,"coco-reject")),"atomic adapter");});
  Test("full/coco-stable-fault-map",()=>{foreach(var e in s.Data.entities.Where(e=>e.kind=="Annotation"&&e.Text("shape")=="polygon"))e.data["deleted"]=true;s.Save();string o=Path.Combine(root,"coco");CocoAdapter.Export(s,o);Assert(File.ReadAllText(Path.Combine(o,"annotations.json")).Contains(fault.id),"semantic identity preserved");});
  Test("full/training-fails-closed",()=>{var b=new RfDetrBackend();Assert(!b.CanTrain,"blocked");Reject(()=>b.Train(full,"not-approved.pt"));});
  Test("full/latest-review-wins",()=>{s.Review(frame.id,"abnormal","rejected","reviewer");string o=Path.Combine(root,"coco-rejected");CocoAdapter.Export(s,o);var parsed=Codec.Parse<Dictionary<string,object>>(File.ReadAllText(Path.Combine(o,"annotations.json")));Assert(Codec.Json(parsed["images"])=="[]","old confirmed review must not override rejection");});
  Test("storage/windows-reserved-paths",()=>{foreach(string p in new[]{"assets/CON.txt","assets/a:stream","assets/../x","assets/a\\b","assets/end. "})Reject(()=>Rules.SafePath(s.Root,p));});
  Extended(root);
  WorkflowTests(root);
  File.WriteAllText(Path.Combine(root,"results.json"),Codec.Json(new{passed=pass,failed=fail,tests=results}));File.WriteAllText(Path.Combine(Path.GetFullPath(args[0]),"latest.txt"),root);
  Console.WriteLine("RESULT passed="+pass+" failed="+fail+" artifacts="+root);return fail==0?0:1;
 }
}
