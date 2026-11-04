// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed class ProjectFolder {
  public string Root,Site,Equipment,Camera,CameraId,Project;
  public override string ToString(){return Site+" / "+Equipment+" / "+Camera;}
 }
 // UI policy shared by the WPF handlers and deterministic regression tests.
 public static class Workflow {
  public static string Component(string value){
   if(String.IsNullOrWhiteSpace(value)||value!=value.Trim()||value.IndexOfAny(Path.GetInvalidFileNameChars())>=0||value=="."||value==".."||value.EndsWith("."))throw new ArgumentException("厂区、设备和摄像头须为有效的单层文件夹名称");
   Rules.SafePath(Path.GetTempPath(),value+"/check");return value;
  }
  static IEnumerable<string> Children(string path){return Directory.EnumerateDirectories(path).Where(p=>(File.GetAttributes(p)&FileAttributes.ReparsePoint)==0&&!Path.GetFileName(p).StartsWith(".")&&Path.GetFileName(p)!="assets").OrderBy(p=>p,StringComparer.OrdinalIgnoreCase);}
  public static List<ProjectFolder> Detect(string root){
   root=Path.GetFullPath(root);if(!Directory.Exists(root))throw new DirectoryNotFoundException("主目录不存在");
   if((File.GetAttributes(root)&FileAttributes.ReparsePoint)!=0)throw new IOException("请选择实际主目录，不使用目录链接");
   var found=new List<ProjectFolder>();int visited=0;
   Action<string,int> scan=null;scan=(path,depth)=>{
    Work.Check();if(++visited>10000)throw new IOException("目录过多，请选择更具体的主目录");
    if(File.Exists(Path.Combine(path,"project.ids.json"))){
     var s=new Store(path);Rules.Validate(s.Data);var p=s.Find(s.Data.project_id);string site=s.Find(p.Text("site_id")).Text("name");
     foreach(var c in s.Data.entities.Where(e=>e.kind=="Camera"))found.Add(new ProjectFolder{Root=path,Site=site,Project=p.Text("name"),Equipment=s.Find(c.Text("equipment_id")).Text("name"),Camera=c.Text("name"),CameraId=c.id});
     if(!s.Data.entities.Any(e=>e.kind=="Camera"))found.Add(new ProjectFolder{Root=path,Site=site,Project=p.Text("name"),Equipment="",Camera=""});return;
    }
    if(depth==3){var cam=new DirectoryInfo(path);found.Add(new ProjectFolder{Root=path,Site=cam.Parent.Parent.Name,Equipment=cam.Parent.Name,Camera=cam.Name});return;}
    foreach(string child in Children(path))scan(child,depth+1);
   };scan(root,0);return found;
  }
  public static Store OpenOrCreate(string root,string project,string site,string equipment,string camera,ProjectFolder detected){
   if(String.IsNullOrWhiteSpace(root))throw new ArgumentException("请先选择主目录");
   Component(site);Component(equipment);Component(camera);if(String.IsNullOrWhiteSpace(project))throw new ArgumentException("请填写项目名称");
   root=Path.GetFullPath(root);Directory.CreateDirectory(root);
   string target=Rules.SafePath(root,site+"/"+equipment+"/"+camera);
   if(detected!=null&&detected.Site==site&&detected.Equipment==equipment&&detected.Camera==camera){
    string candidate=Path.GetFullPath(detected.Root);if(!candidate.Equals(root,StringComparison.OrdinalIgnoreCase)&&!candidate.StartsWith(root.TrimEnd(Path.DirectorySeparatorChar)+Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase))throw new IOException("检测目录不在主目录内");
    target=candidate;
   }
   Rules.SafePath(target,"project.ids.json");
   if(File.Exists(Path.Combine(target,"project.ids.json"))){var existing=new Store(target);Rules.VerifyAssets(existing.Data,target);var p=existing.Find(existing.Data.project_id);if(existing.Find(p.Text("site_id")).Text("name")!=site||!existing.Data.entities.Any(e=>e.kind=="Camera"&&e.Text("name")==camera&&existing.Find(e.Text("equipment_id")).Text("name")==equipment))throw new IOException("此目录中的项目关联与填写内容不同，请先检测并选择已有摄像头");return existing;}
   var s=Store.Create(target,project,site);var eq=s.Add("Equipment",new Dictionary<string,object>{{"name",equipment},{"project_id",s.Data.project_id}});s.Revise(eq,"local-user");var cam=s.Add("Camera",new Dictionary<string,object>{{"name",camera},{"equipment_id",eq.id}});s.Revise(cam,"local-user");s.Save();return s;
  }
  static string FilePart(string value){var invalid=Path.GetInvalidFileNameChars();string p=new string((value??"").Select(c=>invalid.Contains(c)?'_':c).ToArray()).Trim().TrimEnd('.');return String.IsNullOrEmpty(p)?"未命名":p;}
  public static string PackagePath(Store store,string cameraId,string directory,DateTime date){
   var project=store.Find(store.Data.project_id);var camera=store.Find(cameraId);var equipment=store.Find(camera.Text("equipment_id"));
   string stem=FilePart(store.Find(project.Text("site_id")).Text("name"))+"-"+FilePart(equipment.Text("name"))+"-"+FilePart(camera.Text("name"))+"-"+date.ToString("yyyyMMdd");return AvailablePath(Path.Combine(directory,stem+".ids"));
  }
  public static string AvailablePath(string path){string stem=Path.Combine(Path.GetDirectoryName(path),Path.GetFileNameWithoutExtension(path)),ext=Path.GetExtension(path);int i=0;string candidate=path;while(File.Exists(candidate)||Directory.Exists(candidate)){if(++i>9999)throw new IOException("同名包过多，请更换导出目录");candidate=stem+"-"+i.ToString("00")+ext;}return candidate;}
  public static string ReviewStatus(string actor,string frameState,string requested,bool hasAnnotation){
   if(String.IsNullOrWhiteSpace(actor))throw new ArgumentException("请填写审核人");
   if(actor=="本地管理员")return requested;
   if(frameState=="normal"||hasAnnotation)return "confirmed";
   if(frameState=="unknown")return "unknown";
   throw new InvalidOperationException("请先完成标注、点击正常，或将无法判断的帧标记为未知");
  }
  public static string NextFrame(IEnumerable<Entity> entities,string current){var ids=entities.Where(e=>e.kind=="Frame").OrderBy(e=>e.Text("video_id")).ThenBy(e=>e.Number("source_timestamp_100ns")).Select(e=>e.id).ToList();int i=ids.IndexOf(current);return i>=0&&i+1<ids.Count?ids[i+1]:null;}
 }
}
