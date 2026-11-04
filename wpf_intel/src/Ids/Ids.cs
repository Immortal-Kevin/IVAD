// SPDX-License-Identifier: Apache-2.0
// Copyright 2026 IVAD contributors
using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using System.Web.Script.Serialization;

namespace Ivad.Ids {
 public sealed class Entity {
  public string id {get;set;} public string kind {get;set;} public int revision {get;set;}
  public Dictionary<string,object> data {get;set;}
  public Entity(){id=Guid.NewGuid().ToString("D");revision=1;data=new Dictionary<string,object>();}
  public string Text(string key){object v;return data.TryGetValue(key,out v)&&v!=null?Convert.ToString(v,System.Globalization.CultureInfo.InvariantCulture):"";}
  public double Number(string key){return Convert.ToDouble(data[key],System.Globalization.CultureInfo.InvariantCulture);}
 }
 public sealed class Asset { public string path {get;set;} public string sha256 {get;set;} public long bytes {get;set;} }
 public sealed class Document {
  public string schema {get;set;} public string project_id {get;set;} public long sequence {get;set;}
  public List<Entity> entities {get;set;} public List<Asset> assets {get;set;}
  public Document(){schema="ids/1.0";entities=new List<Entity>();assets=new List<Asset>();}
 }
 public sealed class Envelope {
  public string format {get;set;} public string mode {get;set;} public string base_sha256 {get;set;}
  public string target_sha256 {get;set;} public List<string> included_assets {get;set;}
 }
 public static class Codec {
  public static JavaScriptSerializer Serializer(){var s=new JavaScriptSerializer{MaxJsonLength=16*1024*1024,RecursionLimit=100};s.RegisterConverters(new[]{new StableIdsConverter()});return s;}
  public static string Json(object o){return Serializer().Serialize(o);}
  public static T Parse<T>(string s){return Serializer().Deserialize<T>(s);}
  public static string Hash(byte[] b){var watch=System.Diagnostics.Stopwatch.StartNew();using(var h=SHA256.Create()){string result=BitConverter.ToString(h.ComputeHash(b)).Replace("-","").ToLowerInvariant();System.Threading.Interlocked.Increment(ref Work.MemoryHashCalls);System.Threading.Interlocked.Add(ref Work.MemoryHashBytes,b.Length);System.Threading.Interlocked.Add(ref Work.MemoryHashTicks,watch.ElapsedTicks);return result;}}
  public static string HashFile(string p){return Work.HashFile(p);}
  public static string Fingerprint(Document d){return Hash(Encoding.UTF8.GetBytes(Json(d)));}
  public static Document Clone(Document d){return Parse<Document>(Json(d));}
 }
 public static class Rules {
  static string[] Kinds={"Site","Project","Equipment","Camera","Video","Frame","Fault","Annotation","ROI","Review","Revision"};
  static void Need(bool ok,string text){if(!ok)throw new InvalidDataException(text);}
  public static string SafePath(string root,string relative){
   Need(!String.IsNullOrWhiteSpace(relative)&&!Path.IsPathRooted(relative)&&!relative.Contains("\\")&&!relative.Contains(":"),"非法包路径");
   string[] segments=relative.Split('/');
   Need(segments.All(s=>s!=".."&&s!="."&&s.Length>0&&!s.EndsWith(".")&&!s.EndsWith(" ")&&s.IndexOfAny(Path.GetInvalidFileNameChars())<0),"非法路径分段");
   foreach(string s in segments){string n=s.Split('.')[0].ToUpperInvariant();Need(!(new[]{"CON","PRN","AUX","NUL","COM1","COM2","COM3","COM4","COM5","COM6","COM7","COM8","COM9","LPT1","LPT2","LPT3","LPT4","LPT5","LPT6","LPT7","LPT8","LPT9"}).Contains(n),"Windows保留文件名");}
   string full=Path.GetFullPath(Path.Combine(root,relative.Replace('/',Path.DirectorySeparatorChar)));
   Need(full.StartsWith(Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase),"路径越界");
   for(string p=Path.GetDirectoryName(full);p!=null&&p.Length>=Path.GetFullPath(root).Length;p=Path.GetDirectoryName(p))
    if(Directory.Exists(p))Need((File.GetAttributes(p)&FileAttributes.ReparsePoint)==0,"不允许目录链接");
   if(File.Exists(full))Need((File.GetAttributes(full)&FileAttributes.ReparsePoint)==0,"不允许文件链接");
   return full;
  }
  public static void Validate(Document d){
   Need(d!=null&&d.schema=="ids/1.0"&&d.sequence>=0&&d.entities!=null&&d.assets!=null,"不支持的IDS文档");
   var ids=new Dictionary<string,Entity>();
   foreach(var e in d.entities){Guid g;Need(e!=null&&Guid.TryParseExact(e.id,"D",out g)&&g!=Guid.Empty&&Kinds.Contains(e.kind)&&e.revision>0&&e.data!=null,"实体无效");Need(!ids.ContainsKey(e.id),"重复ID");ids.Add(e.id,e);}
   Need(ids.ContainsKey(d.project_id)&&ids[d.project_id].kind=="Project","项目身份缺失");
   Need(d.entities.Count(e=>e.kind=="Project")==1,"一个IDS文档只能有一个项目");
   var assets=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
   foreach(var a in d.assets){Need(a!=null&&a.path.StartsWith("assets/",StringComparison.Ordinal),"资产必须位于assets");SafePath(Path.GetTempPath(),a.path);Need(assets.Add(a.path)&&a.bytes>=0&&a.sha256!=null&&System.Text.RegularExpressions.Regex.IsMatch(a.sha256,"^[a-f0-9]{64}$"),"重复或无效资产");}
   Action<Entity,string,string> link=(e,key,kind)=>{string id=e.Text(key);Need(ids.ContainsKey(id)&&ids[id].kind==kind,"无效关联: "+e.kind+"."+key);};
   foreach(var e in d.entities){
    if(new[]{"Site","Project","Equipment","Camera","Fault"}.Contains(e.kind))Need(!String.IsNullOrWhiteSpace(e.Text("name")),"名称不能为空");
    if(e.kind=="Project")link(e,"site_id","Site");
    if(e.kind=="Equipment"){link(e,"project_id","Project");Need(e.Text("project_id")==d.project_id,"跨项目设备");}
    if(e.kind=="Camera")link(e,"equipment_id","Equipment");
    if(e.kind=="Video"){link(e,"camera_id","Camera");Need(assets.Contains(e.Text("asset_path")),"视频文件未登记");Need(!String.IsNullOrWhiteSpace(e.Text("original_name")),"视频来源缺失");}
    if(e.kind=="Frame"){
     link(e,"video_id","Video");Need(assets.Contains(e.Text("asset_path")),"帧文件未登记");
     Need(e.Number("width")>0&&e.Number("height")>0&&e.Number("pts_us")>=0&&e.Number("source_timestamp_100ns")>=0,"帧尺寸/时间无效");
     Need(e.Text("time_source")=="media_foundation_sample","必须记录真实解码样本时间");
     Need(e.Number("pts_us")==Math.Floor(e.Number("source_timestamp_100ns")/10),"PTS单位不一致");
     Need(new[]{"normal","abnormal","unknown","unannotated"}.Contains(e.Text("state")),"帧状态无效");
    }
    if(e.kind=="Fault"){Need(e.Number("taxonomy_version")>=1,"分类版本无效");}
    if(e.kind=="Annotation"||e.kind=="ROI"){
     link(e,"frame_id","Frame");var f=ids[e.Text("frame_id")];
     if(e.kind=="Annotation")link(e,"fault_id","Fault");
     if(e.kind=="ROI"){link(e,"camera_id","Camera");Need(e.Text("camera_id")==ids[f.Text("video_id")].Text("camera_id"),"ROI摄像头与源视频不一致");}
     Need(e.Text("coordinate_space")=="source_pixels","坐标系必须为原图像素");
     double[] points=Codec.Parse<double[]>(Codec.Json(e.data["points"]));
     string shape=e.Text("shape");Need(shape=="box"||shape=="polygon","形状无效");
     Need(shape=="box"?points.Length==4:points.Length>=6&&points.Length%2==0,"坐标数量无效");
     for(int i=0;i<points.Length;i++)Need(!Double.IsNaN(points[i])&&!Double.IsInfinity(points[i])&&points[i]>=0&&points[i]<=(i%2==0?f.Number("width"):f.Number("height")),"坐标超出原图");
     if(shape=="box")Need(points[2]>points[0]&&points[3]>points[1],"矩形面积必须大于零");
     else {double area=0;for(int i=0;i<points.Length;i+=2){int j=(i+2)%points.Length;area+=points[i]*points[j+1]-points[j]*points[i+1];}Need(Math.Abs(area)>0.001,"多边形面积必须大于零");}
    }
    if(e.kind=="Review"){link(e,"frame_id","Frame");Need(new[]{"confirmed","rejected","needs_work","unknown"}.Contains(e.Text("status"))&&!String.IsNullOrWhiteSpace(e.Text("reviewer")),"审核状态或审核人缺失");}
    if(e.kind=="Revision"){Need(ids.ContainsKey(e.Text("entity_id"))&&!String.IsNullOrWhiteSpace(e.Text("actor"))&&!String.IsNullOrWhiteSpace(e.Text("utc")),"修订关联缺失");Need(e.Number("entity_revision")>=1&&e.data.ContainsKey("snapshot"),"修订快照缺失");}
   }
   Need(!d.entities.Where(e=>e.kind=="Frame").GroupBy(e=>e.Text("video_id")+"/"+e.Text("source_timestamp_100ns")).Any(g=>g.Count()>1),"重复源视频PTS帧");
  }
  public static void VerifyAssets(Document d,string root){foreach(var a in d.assets){string p=SafePath(root,a.path);Need(File.Exists(p)&&new FileInfo(p).Length==a.bytes&&Codec.HashFile(p)==a.sha256,"资产哈希不符: "+a.path);}}
 }
 public sealed partial class Store {
  public string Root {get;private set;} public Document Data {get;private set;}
  string expected;
  readonly List<string> createdAssets=new List<string>();
  public string Manifest {get{return Path.Combine(Root,"project.ids.json");}}
  public Store(string root){Root=Path.GetFullPath(root);NvidiaBridge.Hydrate(Root);if(File.Exists(Manifest)){byte[] bytes=File.ReadAllBytes(Manifest);Data=Codec.Parse<Document>(Encoding.UTF8.GetString(bytes).TrimStart('\uFEFF'));Rules.Validate(Data);expected=Codec.Hash(bytes);InitializeFast(Encoding.UTF8.GetString(bytes).TrimStart('\uFEFF'));}}
  public static Store Create(string root,string name,string site){
   var s=new Store(root);if(s.Data!=null)throw new IOException("目标已有项目");
   Directory.CreateDirectory(s.Root);s.Data=new Document();
   var a=s.Add("Site",new Dictionary<string,object>{{"name",site}});var p=s.Add("Project",new Dictionary<string,object>{{"name",name},{"site_id",a.id}});s.Data.project_id=p.id;s.Save();return s;
  }
  public Entity Add(string kind,Dictionary<string,object> data){var e=new Entity{kind=kind,data=data};Data.entities.Add(e);if(entityIndex!=null)entityIndex[e.id]=e;return e;}
  public Entity Find(string id){Entity e;if(entityIndex!=null&&entityIndex.TryGetValue(id,out e))return e;return Data.entities.Single(x=>x.id==id);}
  public void Revise(Entity e,string actor){Data.entities.Add(new Entity{kind="Revision",data=new Dictionary<string,object>{{"entity_id",e.id},{"entity_revision",e.revision},{"actor",actor},{"utc",DateTime.UtcNow.ToString("o")},{"snapshot",Codec.Json(e.data)}}});}
  public Asset CopyAsset(string source){
   string hash=Codec.HashFile(source),ext=Path.GetExtension(source).ToLowerInvariant();
   if(ext.Length>12||ext.Any(c=>!(Char.IsLetterOrDigit(c)||c=='.')))throw new InvalidDataException("文件扩展名无效");
   string rel="assets/"+hash+ext;var old=Data.assets.FirstOrDefault(a=>a.path==rel);if(old!=null)return old;
   string target=Rules.SafePath(Root,rel);Directory.CreateDirectory(Path.GetDirectoryName(target));
   if(File.Exists(target)){if(Codec.HashFile(target)!=hash)throw new IOException("已有资产哈希不符");}else {
    string temp=target+"."+Guid.NewGuid().ToString("N")+".tmp";
    try{using(var input=File.OpenRead(source))using(var output=new FileStream(temp,FileMode.CreateNew)){Work.Created(temp);Work.Copy(input,output,"复制资产",input.Length);}
     if(Codec.HashFile(temp)!=hash)throw new IOException("复制期间源文件改变，拒绝导入");Work.Check();File.Move(temp,target);createdAssets.Add(target);Work.Created(target);
    }finally{if(File.Exists(temp))File.Delete(temp);}
   }
   var added=new Asset{path=rel,sha256=hash,bytes=new FileInfo(target).Length};Data.assets.Add(added);return added;
  }
  public void Save(){
   Rules.Validate(Data);Directory.CreateDirectory(Root);
   string lockfile=Path.Combine(Root,".write.lock");
   using(var hold=new FileStream(lockfile,FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
    Work.Report("提交前校验资产");
    Rules.VerifyAssets(Data,Root);
    if(File.Exists(Manifest)&&expected!=Codec.HashFile(Manifest))throw new IOException("项目被另一进程修改，请重新打开");
    long seq=Data.sequence;Data.sequence++;
    string temp=Manifest+"."+Guid.NewGuid().ToString("N")+".tmp";
    try{File.WriteAllText(temp,Codec.Json(Data),new UTF8Encoding(false));string nextHash=Codec.HashFile(temp);Work.Check();
     NvidiaBridge.Commit(Root,temp,expected);if(NvidiaBridge.Enabled){File.Delete(temp);}else if(File.Exists(Manifest))File.Replace(temp,Manifest,Manifest+".backup",true);else File.Move(temp,Manifest);
     expected=nextHash;createdAssets.Clear();InitializeFast(File.ReadAllText(Manifest));
    }catch{Data.sequence=seq;if(File.Exists(temp))File.Delete(temp);throw;}
   }
  }
  public void Reload(){var s=new Store(Root);Data=s.Data;expected=s.expected;InitializeFast(s.committedJson);}
  public void AbortAssets(){CleanupOwned(Root,createdAssets);createdAssets.Clear();}
  public static void CleanupOwned(string root,IEnumerable<string> files){
   // Only files created by this Store may be removed, and never if another committed document references them.
   using(var hold=new FileStream(Path.Combine(root,".write.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
    string manifest=Path.Combine(root,"project.ids.json");Document committed=File.Exists(manifest)?Codec.Parse<Document>(File.ReadAllText(manifest)):null;
    foreach(string path in files){string expected=Rules.SafePath(root,"assets/"+Path.GetFileName(path));if(!String.Equals(Path.GetFullPath(path),expected,StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("清理路径不属于任务资产目录");if(File.Exists(path)&&(committed==null||!committed.assets.Any(a=>String.Equals(Rules.SafePath(root,a.path),path,StringComparison.OrdinalIgnoreCase))))File.Delete(path);}
   }
  }
  public Entity ImportVideo(string file,string camera){try{
   if(Find(camera).kind!="Camera")throw new InvalidDataException("请选择摄像头");
   var a=CopyAsset(file);var existing=Data.entities.FirstOrDefault(e=>e.kind=="Video"&&e.Text("camera_id")==camera&&e.Text("asset_path")==a.path);if(existing!=null)return existing;
   var added=Add("Video",new Dictionary<string,object>{{"camera_id",camera},{"asset_path",a.path},{"original_name",Path.GetFileName(file)}});Revise(added,"local-user");Save();return added;
  }catch{AbortAssets();Reload();throw;}}
  public void EditGeometry(string id,double[] points,string actor){var e=Find(id);if((e.kind!="Annotation"&&e.kind!="ROI")||e.Text("deleted")=="True")throw new InvalidDataException("请选择有效标注");e.data["points"]=points;e.revision++;Revise(e,actor);Save();}
  public void DeleteGeometry(string id,string actor){var e=Find(id);if(e.kind!="Annotation"&&e.kind!="ROI")throw new InvalidDataException("请选择标注");if(e.Text("deleted")=="True")return;e.data["deleted"]=true;e.revision++;Revise(e,actor);Save();}
  public Entity AddAnnotation(string frame,string fault,string shape,double[] points,bool roi){
   var data=new Dictionary<string,object>{{"frame_id",frame},{"fault_id",fault},{"shape",shape},{"points",points},{"coordinate_space","source_pixels"}};
   if(roi)data["camera_id"]=Find(Find(frame).Text("video_id")).Text("camera_id");
   var e=Add(roi?"ROI":"Annotation",data);Revise(e,"local-user");Save();return e;
  }
  public void Review(string frame,string state,string review,string actor){var e=Find(frame);e.data["state"]=state;e.revision++;Revise(e,actor);var r=Add("Review",new Dictionary<string,object>{{"frame_id",frame},{"status",review},{"reviewer",actor},{"utc",DateTime.UtcNow.ToString("o")}});Revise(r,actor);Save();}
 }
 public static class Packages {
  const long Limit=20L*1024*1024*1024;
  static void Entry(ZipArchive zip,string name,byte[] bytes){var e=zip.CreateEntry(name,CompressionLevel.Optimal);using(var s=e.Open())s.Write(bytes,0,bytes.Length);}
  public static void Export(Store store,string output,Document baseline){
   Rules.Validate(store.Data);Rules.VerifyAssets(store.Data,store.Root);
   if(baseline!=null){Rules.Validate(baseline);if(baseline.project_id!=store.Data.project_id)throw new InvalidDataException("增量基线项目不同");}
   if(File.Exists(output))throw new IOException("导出包不可覆盖，请使用新文件名");
   if(baseline!=null)baseline=QueueProjection.Active(baseline);var current=QueueProjection.Active(store.Data);var included=current.assets.Where(a=>baseline==null||!baseline.assets.Any(b=>b.path==a.path&&b.sha256==a.sha256)).ToList();
   var env=new Envelope{format="ids-package/1.0",mode=baseline==null?"full":"incremental",base_sha256=baseline==null?null:Codec.Fingerprint(baseline),target_sha256=Codec.Fingerprint(current),included_assets=included.Select(a=>a.path).ToList()};
   string temp=output+"."+Guid.NewGuid().ToString("N")+".tmp";
   try{using(var fs=new FileStream(temp,FileMode.CreateNew))using(var z=new ZipArchive(fs,ZipArchiveMode.Create)){
    Entry(z,"package.json",Encoding.UTF8.GetBytes(Codec.Json(env)));Entry(z,"document.json",Encoding.UTF8.GetBytes(Codec.Json(current)));
    foreach(var a in included){var entry=z.CreateEntry(a.path,CompressionLevel.NoCompression);using(var source=File.OpenRead(Rules.SafePath(store.Root,a.path)))using(var dest=entry.Open())if(Work.Copy(source,dest,"导出 "+a.path,a.bytes)!=a.sha256)throw new InvalidDataException("导出期间资产发生变化");}
   }Work.Check();File.Move(temp,output);}finally{if(File.Exists(temp))File.Delete(temp);}
  }
  public static Store Import(string input,string target){
   var existing=new Store(target);Directory.CreateDirectory(target);
   string stage=Path.Combine(target,".import-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(stage);
   var newFiles=new List<string>();bool committed=false;
   try{
    Envelope env;Document doc;
    using(var fs=File.OpenRead(input))using(var z=new ZipArchive(fs,ZipArchiveMode.Read)){
     if(z.Entries.Count>100000)throw new InvalidDataException("文件数量超限");
     var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);long total=0;
     foreach(var e in z.Entries){Rules.SafePath(stage,e.FullName);if(!names.Add(e.FullName)||e.Length>Limit||(total+=e.Length)>Limit)throw new InvalidDataException("重复路径或解压大小超限");if((e.ExternalAttributes>>16&0xF000)==0xA000)throw new InvalidDataException("禁止符号链接");}
     Func<string,string> read=name=>{var e=z.GetEntry(name);if(e==null||e.Length>16*1024*1024)throw new InvalidDataException("元数据缺失或超限");using(var s=new StreamReader(e.Open(),Encoding.UTF8))return s.ReadToEnd();};
     env=Codec.Parse<Envelope>(read("package.json"));doc=Codec.Parse<Document>(read("document.json"));Rules.Validate(doc);
     if(env.format!="ids-package/1.0"||!(env.mode=="full"||env.mode=="incremental")||env.included_assets==null||env.target_sha256!=Codec.Fingerprint(doc))throw new InvalidDataException("包格式/摘要错误");
     if(env.mode=="incremental"&&(existing.Data==null||(env.base_sha256!=Codec.Fingerprint(existing.Data)&&env.target_sha256!=Codec.Fingerprint(existing.Data))))throw new InvalidDataException("增量基线冲突，未修改目标");
     if(env.mode=="full"&&existing.Data!=null&&Codec.Fingerprint(existing.Data)!=env.target_sha256)throw new InvalidDataException("完整包与已有项目冲突，须导入空目录");
     var listed=new HashSet<string>(env.included_assets,StringComparer.OrdinalIgnoreCase);
     if(listed.Count!=env.included_assets.Count||listed.Any(p=>!doc.assets.Any(a=>a.path==p))||z.Entries.Any(e=>e.FullName!="package.json"&&e.FullName!="document.json"&&!listed.Contains(e.FullName)))throw new InvalidDataException("包包含未声明文件");
     if(env.mode=="full"&&listed.Count!=doc.assets.Count)throw new InvalidDataException("完整包缺少文件");
     foreach(var a in doc.assets){
      if(listed.Contains(a.path)){var e=z.GetEntry(a.path);if(e==null||e.Length!=a.bytes)throw new InvalidDataException("文件大小错误");string dst=Rules.SafePath(stage,a.path);Directory.CreateDirectory(Path.GetDirectoryName(dst));using(var source=e.Open())using(var dest=new FileStream(dst,FileMode.CreateNew))Work.Copy(source,dest,"导入 "+a.path,a.bytes);if(Codec.HashFile(dst)!=a.sha256)throw new InvalidDataException("文件哈希错误");}
      else {string p=Rules.SafePath(target,a.path);if(!File.Exists(p)||new FileInfo(p).Length!=a.bytes||Codec.HashFile(p)!=a.sha256)throw new InvalidDataException("缺少增量基础文件");}
     }
    }
    Work.Check();
    using(var hold=new FileStream(Path.Combine(target,".write.lock"),FileMode.OpenOrCreate,FileAccess.ReadWrite,FileShare.None)){
     var now=new Store(target);if((now.Data==null)!=(existing.Data==null)||(now.Data!=null&&Codec.Fingerprint(now.Data)!=Codec.Fingerprint(existing.Data)))throw new IOException("导入期间目标已变更");
     foreach(var a in doc.assets){string src=Rules.SafePath(stage,a.path),dst=Rules.SafePath(target,a.path);if(!File.Exists(src))continue;if(File.Exists(dst)){if(Codec.HashFile(dst)!=a.sha256)throw new InvalidDataException("已有文件冲突");}else{Directory.CreateDirectory(Path.GetDirectoryName(dst));File.Move(src,dst);newFiles.Add(dst);}}
     string m=Path.Combine(stage,"commit.json");File.WriteAllText(m,Codec.Json(doc),new UTF8Encoding(false));
     Work.Check();NvidiaBridge.Commit(target,m,existing.Data==null?null:Codec.Fingerprint(existing.Data));string dest=Path.Combine(target,"project.ids.json");if(NvidiaBridge.Enabled){File.Delete(m);}else if(File.Exists(dest))File.Replace(m,dest,dest+".backup",true);else File.Move(m,dest);committed=true;
    }
    return new Store(target);
   }finally{if(!committed&&newFiles.Count>0)Store.CleanupOwned(target,newFiles);if(Directory.Exists(stage))Directory.Delete(stage,true);}
  }
 }
}
