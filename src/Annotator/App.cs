// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Diagnostics;
using System.Threading;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Shapes;
using Ivad.Ids;
using Forms=System.Windows.Forms;

namespace Ivad.Annotator {
 public sealed class Choice {public string Id {get;set;}public string Name {get;set;}public override string ToString(){return Name;}}
 public sealed partial class MainWindow:Window {
  Store store;Entity frame;string selected;ListBox frames=new ListBox(),geometries=new ListBox{Height=95};
  ComboBox cameras=new ComboBox(),videos=new ComboBox(),faults=new ComboBox(),shape=new ComboBox(),state=new ComboBox(),review=new ComboBox();
  TextBox projectName=Text("新项目"),masterRoot=Text(""),faultName=Text("异常"),actor=Text("本地审核员"),interval=Text("1"),rangeStart=Text("0"),rangeEnd=Text(""),limit=Text("500");
  ComboBox siteName=new ComboBox{IsEditable=true,Text="厂区"},equipmentName=new ComboBox{IsEditable=true,Text="设备"},cameraName=new ComboBox{IsEditable=true,Text="摄像头"},detectedFolders=new ComboBox();
  List<ProjectFolder> folders=new List<ProjectFolder>();
  TextBlock context=new TextBlock{Text="请选择项目与图片",TextWrapping=TextWrapping.Wrap},extractionState=new TextBlock{Text="等待抽帧",TextWrapping=TextWrapping.Wrap},extractionCount=new TextBlock{Text="0 / —"},reviewLabel;
  ProgressBar extractionBar=new ProgressBar{Height=14,Minimum=0,Maximum=1};
  StackPanel tools=new StackPanel{Orientation=Orientation.Horizontal};
  volatile string extractionProgress;bool extractionJob;
  TextBlock status=new TextBlock{Text="选择主目录开始。每次标注编辑自动保存。",TextWrapping=TextWrapping.Wrap};
  Canvas canvas=new Canvas{Background=Brushes.Black};Grid imageHost=new Grid{Background=Brushes.Black};Image image=new Image();
  TabControl tabs=new TabControl{MinWidth=245};StackPanel actions;Button cancel=new Button{Content="取消任务",IsEnabled=false,MinWidth=85};
  Point? start;List<Point> polygon=new List<Point>();double[] original,preview;int handle=-1;bool busy,closeWhenIdle,refreshing,loadingFrame,reviewEdited;
  CancellationTokenSource cancellation;volatile string progressText;string extractionSummary;DateTime lastProgress;System.Windows.Threading.DispatcherTimer ticker;
  static TextBox Text(string value){return new TextBox{Text=value};}
  static new void Name(DependencyObject control,string name){AutomationProperties.SetName(control,name);AutomationProperties.SetAutomationId(control,name);}
  public MainWindow(){
   WindowStyle=WindowStyle.SingleBorderWindow;ResizeMode=ResizeMode.CanResize;ShowInTaskbar=true;
   Width=Math.Min(1600,SystemParameters.WorkArea.Width);Height=Math.Min(960,SystemParameters.WorkArea.Height);MinWidth=Math.Min(900,SystemParameters.WorkArea.Width);MinHeight=Math.Min(540,SystemParameters.WorkArea.Height);WindowStartupLocation=WindowStartupLocation.CenterScreen;
   BuildInterface();
  }
  void AddTool(Panel panel,string text,Action action){var button=new Button{Content=text,Padding=new Thickness(6,4,6,4),Margin=new Thickness(0,3,4,3)};Name(button,text);button.Click+=(s,e)=>Guard(action);panel.Children.Add(button);}
  bool DiscardDraft(bool includeReview=true){if(polygon.Count==0&&!start.HasValue&&(!includeReview||!reviewEdited))return true;if(MessageBox.Show(this,"当前仍有未完成绘制或未保存的审核选择。已完成的几何标注已自动保存。放弃尚未保存的部分并继续？选择取消可返回完成绘制并保存审核。","未完成的编辑",MessageBoxButton.OKCancel,MessageBoxImage.Question)!=MessageBoxResult.OK)return false;polygon.Clear();start=null;preview=null;if(includeReview)reviewEdited=false;canvas.ReleaseMouseCapture();Redraw();return true;}
  void DetectFolders(){string root=masterRoot.Text;Run("检测现有文件夹",()=>Workflow.Detect(root),list=>{folders=list;siteName.ItemsSource=list.Select(f=>f.Site).Distinct().ToList();equipmentName.ItemsSource=list.Select(f=>f.Equipment).Distinct().ToList();cameraName.ItemsSource=list.Select(f=>f.Camera).Distinct().ToList();detectedFolders.ItemsSource=list;if(list.Count>0)detectedFolders.SelectedIndex=0;});}
  void OpenCameraProject(){if(!DiscardDraft())return;string root=masterRoot.Text,n=projectName.Text,site=siteName.Text,eq=equipmentName.Text,cam=cameraName.Text;var detected=detectedFolders.SelectedItem as ProjectFolder;Run("保存并打开摄像头项目",()=>Workflow.OpenOrCreate(root,n,site,eq,cam,detected),s=>{Use(s);if(detected!=null&&detected.CameraId!=null)foreach(Choice c in cameras.Items)if(c.Id==detected.CameraId)cameras.SelectedItem=c;});}
  void UpdateReviewVisibility(){var visibility=actor.Text=="本地管理员"?Visibility.Visible:Visibility.Collapsed;review.Visibility=reviewLabel.Visibility=visibility;}
  void UpdateContext(){if(store==null)return;string id=frame==null?(cameras.SelectedItem as Choice)==null?null:((Choice)cameras.SelectedItem).Id:store.Find(frame.Text("video_id")).Text("camera_id");var camera=id==null?null:store.Find(id);context.Text="项目："+store.Find(store.Data.project_id).Text("name")+"   设备："+(camera==null?"—":store.Find(camera.Text("equipment_id")).Text("name"))+"   摄像头："+(camera==null?"—":camera.Text("name"));}
  void SaveReview(){SaveAndAdvance(false);}
  void SaveAndAdvance(bool forceNormal,bool useSelectedState=false){
   if(busy)return;RequireFrame();
   // A pending shape is not an empty frame. Keep the draft instead of discarding it.
   if(polygon.Count>0||start.HasValue){status.Text="请先完成形状或取消绘制，再保存当前帧。";return;}
   string id=frame.id,a=actor.Text;bool annotated=Shapes().Any(x=>x.kind=="Annotation");
   string st=forceNormal?"normal":useSelectedState?new[]{"unannotated","normal","abnormal","unknown"}[state.SelectedIndex]:annotated?"abnormal":"normal";
   string rv=Workflow.ReviewStatus(a,st,new[]{"confirmed","rejected","needs_work","unknown"}[review.SelectedIndex],annotated),root=store.Root,next=Workflow.NextFrame(store.Data.entities,id);
   int tool=shape.SelectedIndex;string name=faultName.Text,fault=(faults.SelectedItem as Choice)==null?null:((Choice)faults.SelectedItem).Id;
   Run("保存审核状态",()=>{var s=new Store(root);s.Review(id,st,rv,a);return s;},s=>{
    reviewEdited=false;Use(s);if(next!=null){frames.SelectedItem=frames.Items.Cast<Choice>().FirstOrDefault(c=>c.Id==next);frames.ScrollIntoView(frames.SelectedItem);}
    if(fault!=null)faults.SelectedItem=faults.Items.Cast<Choice>().FirstOrDefault(c=>c.Id==fault);shape.SelectedIndex=tool;faultName.Text=name;
    extractionSummary=(forceNormal?"已标记为正常": "已保存")+(next==null?"，已是最后一帧。":"并进入下一帧。");
   });
  }
  void ExportPackage(){Require();string camera=frame==null?Selected(cameras):store.Find(frame.Text("video_id")).Text("camera_id");string proposed=Workflow.PackagePath(store,camera,store.Root,DateTime.Now);var d=new Microsoft.Win32.SaveFileDialog{Filter="IDS 包|*.ids",DefaultExt=".ids",AddExtension=true,OverwritePrompt=false,InitialDirectory=store.Root,FileName=System.IO.Path.GetFileName(proposed)};if(d.ShowDialog(this)!=true)return;string p=Workflow.AvailablePath(d.FileName),root=store.Root;Run("导出 IDS 包",()=>{Packages.Export(new Store(root),p,null);return p;},x=>{extractionSummary="已保存："+x;});}
  void UpdateExtraction(){string value=extractionProgress;if(value==null)return;var parts=value.Split('|');int current,total;if(parts.Length!=3||!Int32.TryParse(parts[1],out current)||!Int32.TryParse(parts[2],out total))return;extractionBar.IsIndeterminate=total<0&&busy;extractionBar.Maximum=Math.Max(1,total);extractionBar.Value=Math.Max(0,current);extractionCount.Text=current+" / "+(total<0?"统计中":total.ToString());extractionState.Text=parts[0];}
  void Label(string text){actions.Children.Add(new TextBlock{Text=text,TextWrapping=TextWrapping.Wrap,FontSize=12,Foreground=Color("#526B82"),Margin=new Thickness(0,8,0,10)});}
  void Field(string label,Control c){actions.Children.Add(new TextBlock{Text=label,TextWrapping=TextWrapping.Wrap,FontSize=12,Foreground=Color("#526B82"),Margin=new Thickness(0,12,0,5)});c.MinHeight=34;Name(c,label);actions.Children.Add(c);}
  void Button(string text,Action action){actions.Children.Add(ActionButton(text,action));}
  void Guard(Action action){if(busy)return;try{action();}catch(Exception e){Error(e);}}
  void Error(Exception e){status.Text="操作失败："+e.Message;Log(e.ToString());}
  static void Log(string text){AppDiagnostics.Write("annotator.log",text);}
  async void Run<T>(string title,Func<T> work,Action<T> done){
   if(busy)return;StopPreview();busy=true;workspace.IsEnabled=navigation.IsEnabled=false;tabs.IsEnabled=frames.IsEnabled=canvas.IsEnabled=tools.IsEnabled=false;cancel.IsEnabled=true;cancellation=new CancellationTokenSource();var token=cancellation.Token;progressText=title;extractionSummary=null;status.Text=title;Log("START "+title);
   try{T result=await Task.Run(()=>{Work.Configure(()=>token.IsCancellationRequested,message=>{if(message.StartsWith("IVAD_PROGRESS|")){extractionProgress=message.Substring(14);progressText=title+"："+message.Split('|')[1];return;}if((DateTime.UtcNow-lastProgress).TotalMilliseconds>=150){progressText=title+"："+message;lastProgress=DateTime.UtcNow;}});try{return work();}finally{Work.Configure(null,null);}});busy=false;done(result);status.Text=title+"完成。"+(extractionSummary??"已提交的数据保存在本地。");Log("PASS "+title);}
   catch(OperationCanceledException e){if(extractionJob)extractionProgress="已取消；源视频与已提交数据保留|0|-1";status.Text=e.Message;Log("CANCEL "+title);if(store!=null){try{store.Reload();busy=false;Refresh();}catch(Exception reload){Error(reload);}}}
   catch(Exception e){if(extractionJob)extractionProgress="失败；可重试，详见任务状态|0|-1";Error(e);if(store!=null){try{store.Reload();busy=false;Refresh();}catch(Exception reload){Log(reload.ToString());}}}
   finally{busy=false;extractionJob=false;UpdateExtraction();workspace.IsEnabled=navigation.IsEnabled=true;tabs.IsEnabled=frames.IsEnabled=canvas.IsEnabled=tools.IsEnabled=true;cancel.IsEnabled=false;cancellation.Dispose();cancellation=null;if(closeWhenIdle)Close();}
  }
  void Commit(Action<Store> edit){Require();string root=store.Root;bool pendingReview=reviewEdited;int pendingState=state.SelectedIndex,pendingResult=review.SelectedIndex;Run("保存编辑",()=>{var s=new Store(root);try{edit(s);return s;}catch{s.AbortAssets();throw;}},s=>{Use(s);if(pendingReview){state.SelectedIndex=pendingState;review.SelectedIndex=pendingResult;reviewEdited=true;}});}
  void Use(Store next){if(store==null||store.Root!=next.Root){frame=null;selected=null;}store=next;Refresh();}
  void Require(){if(store==null||store.Data==null)throw new InvalidOperationException("请先选择主目录并保存打开摄像头项目");}
  void RequireFrame(){Require();if(frame==null)throw new InvalidOperationException("请选择帧");}
  string Folder(){var dialog=new Window{Title="项目目录",Owner=this,Width=650,Height=190,ResizeMode=ResizeMode.NoResize,WindowStartupLocation=WindowStartupLocation.CenterOwner};var panel=new StackPanel{Margin=new Thickness(15)};dialog.Content=panel;panel.Children.Add(new TextBlock{Text="输入主目录或 IDS 导入目录；首次导入请选择空目录。"});var path=Text("");Name(path,"项目目录路径");path.Margin=new Thickness(0,10,0,10);panel.Children.Add(path);var row=new StackPanel{Orientation=Orientation.Horizontal};panel.Children.Add(row);var browse=new Button{Content="浏览…",Width=80};row.Children.Add(browse);browse.Click+=(s,e)=>{using(var f=new Forms.FolderBrowserDialog())if(f.ShowDialog()==Forms.DialogResult.OK)path.Text=f.SelectedPath;};var ok=new Button{Content="确定",IsDefault=true,Width=80,Margin=new Thickness(10,0,0,0)};Name(ok,"确定目录");row.Children.Add(ok);ok.Click+=(s,e)=>{if(!String.IsNullOrWhiteSpace(path.Text))dialog.DialogResult=true;};dialog.Loaded+=(s,e)=>path.Focus();return dialog.ShowDialog()==true?System.IO.Path.GetFullPath(path.Text):null;}
  string Open(string filter){var d=new Microsoft.Win32.OpenFileDialog{Filter=filter};return d.ShowDialog(this)==true?d.FileName:null;}
  string Selected(ComboBox c){var v=c.SelectedItem as Choice;if(v==null)throw new InvalidOperationException("请先添加并选择关联项");return v.Id;}
  void Choices(ComboBox box,string kind,Func<Entity,string> label){string old=(box.SelectedItem as Choice)==null?null:((Choice)box.SelectedItem).Id;box.ItemsSource=store.Data.entities.Where(e=>e.kind==kind).Select(e=>new Choice{Id=e.id,Name=label(e)}).ToList();box.SelectedIndex=0;foreach(Choice c in box.Items)if(c.Id==old)box.SelectedItem=c;}
  void Refresh(){
   Require();string old=frame==null?null:frame.id,oldSelected=selected;
   Choices(cameras,"Camera",e=>store.Find(e.Text("equipment_id")).Text("name")+" / "+e.Text("name"));Choices(faults,"Fault",e=>e.Text("name"));refreshingSources=true;try{Choices(videos,"Video",e=>e.Text("original_name")+" · "+store.Find(e.Text("camera_id")).Text("name"));}finally{refreshingSources=false;}
   frames.ItemsSource=store.Data.entities.Where(e=>e.kind=="Frame").OrderBy(e=>e.Text("video_id")).ThenBy(e=>e.Number("source_timestamp_100ns")).Select(e=>new Choice{Id=e.id,Name=(e.Number("pts_us")/1000000).ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+" s · "+FrameStateText(e.Text("state"))}).ToList();
   frame=null;foreach(Choice c in frames.Items)if(c.Id==old)frames.SelectedItem=c;if(frames.SelectedItem==null&&frames.Items.Count>0)frames.SelectedIndex=0;
   if(frame!=null){selected=Shapes().Any(e=>e.id==oldSelected)?oldSelected:null;UpdateGeometryList();Redraw();}else{selected=null;image.Source=null;canvas.Children.Clear();canvas.Children.Add(image);geometries.ItemsSource=null;}
   var project=store.Find(store.Data.project_id);projectName.Text=project.Text("name");siteName.Text=store.Find(project.Text("site_id")).Text("name");Title="IVAD Annotator · "+project.Text("name");projectSummary.Text=project.Text("name")+"  /  "+siteName.Text;UpdateContext();UpdateVideoFrames();UpdateFrameDetails();
  }
  double[] Options(){double step,from,to;int max;if(!Double.TryParse(interval.Text,out step)||!Double.TryParse(rangeStart.Text,out from)||!Int32.TryParse(limit.Text,out max))throw new ArgumentException("请填写有效的抽帧参数");if(String.IsNullOrWhiteSpace(rangeEnd.Text))to=Double.MaxValue;else if(!Double.TryParse(rangeEnd.Text,out to))throw new ArgumentException("结束时间无效");if(step<.000001||Double.IsInfinity(step)||Double.IsNaN(step)||from<0||Double.IsNaN(from)||Double.IsInfinity(from)||to<=from||Double.IsNaN(to)||Double.IsInfinity(to)||max<1||max>5000)throw new ArgumentException("请检查抽帧范围、间隔和数量上限");return new[]{step,from,to,(double)max};}
  void ImportVideo(){Require();if(!DiscardDraft())return;string camera=Selected(cameras);string path=Open("视频|*.mp4;*.avi;*.mov;*.mkv;*.wmv|全部文件|*.*");if(path==null)return;string root=store.Root;Run("导入视频",()=>{var s=new Store(root);var v=s.ImportVideo(path,camera);return Tuple.Create(s,v.id);},result=>{Use(result.Item1);videos.SelectedItem=videos.Items.Cast<Choice>().FirstOrDefault(v=>v.Id==result.Item2);});}
  void ExtractProcess(string root,string video,double[] options){extractionSummary=VideoJobs.Run(root,video,options,Log);}
  double Scale(){return frame==null?1:Math.Max(.001,Math.Min(Math.Max(1,imageHost.ActualWidth)/frame.Number("width"),Math.Max(1,imageHost.ActualHeight)/frame.Number("height")));}
  void ShowFrame(){polygon.Clear();start=null;preview=null;var b=new BitmapImage();b.BeginInit();b.CacheOption=BitmapCacheOption.OnLoad;b.UriSource=new Uri(Rules.SafePath(store.Root,frame.Text("asset_path")));b.EndInit();b.Freeze();image.Source=b;loadingFrame=true;state.SelectedIndex=Array.IndexOf(new[]{"unannotated","normal","abnormal","unknown"},frame.Text("state"));var r=store.Data.entities.LastOrDefault(e=>e.kind=="Review"&&e.Text("frame_id")==frame.id);review.SelectedIndex=r==null?0:Array.IndexOf(new[]{"confirmed","rejected","needs_work","unknown"},r.Text("status"));loadingFrame=false;reviewEdited=false;UpdateGeometryList();UpdateContext();Redraw();UpdateFrameDetails();}
  IEnumerable<Entity> Shapes(){return store.Data.entities.Where(e=>(e.kind=="Annotation"||e.kind=="ROI")&&e.Text("frame_id")==frame.id&&e.Text("deleted")!="True");}
  void UpdateGeometryList(){refreshing=true;string old=selected;geometries.ItemsSource=Shapes().Select(e=>new Choice{Id=e.id,Name=(e.kind=="ROI"?"ROI":store.Find(e.Text("fault_id")).Text("name"))+" / "+e.Text("shape")+" / "+e.id.Substring(0,6)}).ToList();foreach(Choice c in geometries.Items)if(c.Id==old)geometries.SelectedItem=c;refreshing=false;}
  double[] Points(Entity e){return Codec.Parse<double[]>(Codec.Json(e.data["points"]));}
  double[] Handles(Entity e,double[] p){return e.Text("shape")=="box"?new[]{p[0],p[1],p[2],p[1],p[2],p[3],p[0],p[3]}:p;}
  void Redraw(){if(frame==null)return;double scale=Scale();canvas.Width=image.Width=frame.Number("width")*scale;canvas.Height=image.Height=frame.Number("height")*scale;canvas.HorizontalAlignment=HorizontalAlignment.Center;canvas.VerticalAlignment=VerticalAlignment.Center;while(canvas.Children.Count>1)canvas.Children.RemoveAt(1);
   foreach(var e in Shapes()){var p=e.id==selected&&preview!=null?preview:Points(e);Brush color=e.id==selected?Brushes.Gold:e.kind=="ROI"?Brushes.DeepSkyBlue:Brushes.Lime;if(e.Text("shape")=="box")DrawBox(new Point(p[0]*scale,p[1]*scale),new Point(p[2]*scale,p[3]*scale),color);else{var line=new Polygon{Stroke=color,StrokeThickness=2,Fill=Brushes.Transparent,IsHitTestVisible=false};for(int i=0;i<p.Length;i+=2)line.Points.Add(new Point(p[i]*scale,p[i+1]*scale));canvas.Children.Add(line);}if(e.id==selected){var h=Handles(e,p);for(int i=0;i<h.Length;i+=2){var dot=new Rectangle{Width=10,Height=10,Fill=Brushes.White,Stroke=Brushes.DarkOrange,IsHitTestVisible=false};Canvas.SetLeft(dot,h[i]*scale-5);Canvas.SetTop(dot,h[i+1]*scale-5);canvas.Children.Add(dot);}}}
   if(polygon.Count>0){var line=new Polyline{Stroke=Brushes.Yellow,StrokeThickness=2,IsHitTestVisible=false};foreach(var p in polygon)line.Points.Add(new Point(p.X*scale,p.Y*scale));canvas.Children.Add(line);}
  }
  void DrawBox(Point a,Point b,Brush color){var rect=new Rectangle{Width=Math.Abs(a.X-b.X),Height=Math.Abs(a.Y-b.Y),Stroke=color,StrokeThickness=2,IsHitTestVisible=false};Canvas.SetLeft(rect,Math.Min(a.X,b.X));Canvas.SetTop(rect,Math.Min(a.Y,b.Y));canvas.Children.Add(rect);}
  Point Clamp(Point p){return new Point(Math.Max(0,Math.Min(canvas.Width,p.X)),Math.Max(0,Math.Min(canvas.Height,p.Y)));}
  bool Inside(Entity e,Point q){var p=Points(e);if(e.Text("shape")=="box")return q.X>=p[0]&&q.X<=p[2]&&q.Y>=p[1]&&q.Y<=p[3];bool inside=false;for(int i=0,j=p.Length-2;i<p.Length;j=i,i+=2)if((p[i+1]>q.Y)!=(p[j+1]>q.Y)&&q.X<(p[j]-p[i])*(q.Y-p[i+1])/(p[j+1]-p[i+1])+p[i])inside=!inside;return inside;}
  void Down(object sender,MouseButtonEventArgs e){if(frame==null||busy)return;canvas.Focus();Point p=Clamp(e.GetPosition(canvas));if(shape.SelectedIndex==0){start=p;canvas.CaptureMouse();}else if(shape.SelectedIndex==3){Point q=new Point(p.X/Scale(),p.Y/Scale());Entity picked=Shapes().FirstOrDefault(x=>x.id==selected);handle=-1;if(picked!=null){var h=Handles(picked,Points(picked));for(int i=0;i<h.Length;i+=2)if((new Point(h[i],h[i+1])-q).Length<=8/Scale()){handle=i/2;break;}}if(handle<0)picked=Shapes().Reverse().FirstOrDefault(x=>Inside(x,q));selected=picked==null?null:picked.id;if(picked!=null){original=Points(picked);preview=(double[])original.Clone();start=p;canvas.CaptureMouse();}UpdateGeometryList();Redraw();}else{polygon.Add(new Point(p.X/Scale(),p.Y/Scale()));Redraw();}}
  void Move(object sender,MouseEventArgs e){if(!start.HasValue||busy)return;Point p=Clamp(e.GetPosition(canvas));if(shape.SelectedIndex==0){Redraw();DrawBox(start.Value,p,Brushes.Yellow);return;}if(shape.SelectedIndex!=3||selected==null)return;var entity=store.Find(selected);preview=(double[])original.Clone();double x=p.X/Scale(),y=p.Y/Scale();if(handle>=0){if(entity.Text("shape")=="box"){int opposite=(handle+2)%4;var h=Handles(entity,original);preview=new[]{Math.Min(x,h[opposite*2]),Math.Min(y,h[opposite*2+1]),Math.Max(x,h[opposite*2]),Math.Max(y,h[opposite*2+1])};}else{preview[handle*2]=x;preview[handle*2+1]=y;}}else{double dx=(p.X-start.Value.X)/Scale(),dy=(p.Y-start.Value.Y)/Scale();var xs=original.Where((v,i)=>i%2==0);var ys=original.Where((v,i)=>i%2==1);dx=Math.Max(-xs.Min(),Math.Min(frame.Number("width")-xs.Max(),dx));dy=Math.Max(-ys.Min(),Math.Min(frame.Number("height")-ys.Max(),dy));for(int i=0;i<preview.Length;i++)preview[i]+=i%2==0?dx:dy;}Redraw();}
  void Up(object sender,MouseButtonEventArgs e){if(!start.HasValue)return;Point a=start.Value,b=Clamp(e.GetPosition(canvas));start=null;canvas.ReleaseMouseCapture();if(shape.SelectedIndex==3){if(preview!=null&&!preview.SequenceEqual(original)){string id=selected,who=actor.Text;double[] p=preview;preview=null;Guard(()=>Commit(s=>s.EditGeometry(id,p,who)));}else{preview=null;Redraw();}return;}if(Math.Abs(a.X-b.X)<2||Math.Abs(a.Y-b.Y)<2){Redraw();return;}double scale=Scale();Guard(()=>{string f=frame.id,fault=Selected(faults);Commit(s=>s.AddAnnotation(f,fault,"box",new[]{Math.Min(a.X,b.X)/scale,Math.Min(a.Y,b.Y)/scale,Math.Max(a.X,b.X)/scale,Math.Max(a.Y,b.Y)/scale},false));});}
  void CompletePolygon(){RequireFrame();if(shape.SelectedIndex!=1&&shape.SelectedIndex!=2)throw new InvalidOperationException("请选择多边形或ROI工具");if(polygon.Count<3)throw new InvalidOperationException("至少需要3个点");bool roi=shape.SelectedIndex==2;string id=frame.id,fault=roi?"":Selected(faults);double[] points=polygon.SelectMany(p=>new[]{p.X,p.Y}).ToArray();Commit(s=>s.AddAnnotation(id,fault,"polygon",points,roi));}
  void DeleteSelected(){RequireFrame();if(selected==null)throw new InvalidOperationException("请先选中标注");string id=selected,who=actor.Text;Commit(s=>s.DeleteGeometry(id,who));}
  void ShowGallery(){Require();string fault=Selected(faults);var panel=new WrapPanel();foreach(var f in store.Data.entities.Where(e=>e.kind=="Frame"&&store.Data.entities.Any(a=>a.kind=="Annotation"&&a.Text("frame_id")==e.id&&a.Text("fault_id")==fault&&a.Text("deleted")!="True"))){var b=new BitmapImage();b.BeginInit();b.CacheOption=BitmapCacheOption.OnLoad;b.UriSource=new Uri(Rules.SafePath(store.Root,f.Text("asset_path")));b.DecodePixelWidth=220;b.EndInit();panel.Children.Add(new Image{Source=b,Width=220,Height=160,Stretch=Stretch.Uniform,Margin=new Thickness(6)});}new Window{Owner=this,Title="故障类型图库",Width=800,Height=550,Content=new ScrollViewer{Content=panel}}.ShowDialog();}
  public void SmokeProject(string root){store=new Store(root);Refresh();if(frame==null)throw new InvalidOperationException("smoke requires frames");store.AddAnnotation(frame.id,Selected(faults),"box",new[]{4.0,4,20,20},false);store.Review(frame.id,"abnormal","confirmed","ui-smoke");Refresh();Packages.Export(store,System.IO.Path.Combine(root,"ui-smoke.ids.zip"),null);status.Text="模拟服务调用，仅验证WPF启动与渲染；真实GUI操作另行验收。";}
 }
 public static class Program {
  [STAThread] public static int Main(string[] args){
   try{return MainCore(args);}catch(Exception e){AppDiagnostics.Write("startup-errors.log",e.ToString());if(args.Length>=2&&(args[0]=="--ui-check"||args[0]=="--smoke"||args[0]=="--deployment-check")){try{File.WriteAllText(args[1]+".error.txt",e.ToString());}catch{}}if(args.Length==0)MessageBox.Show("无法启动 IVAD Annotator："+e.Message+"\n请检查包内运行环境说明。日志保存在程序 logs 目录或本地应用数据目录。","IVAD Annotator",MessageBoxButton.OK,MessageBoxImage.Error);return 1;}
  }
  static int MainCore(string[] args){
   if(args.Length>0&&args[0]=="--extract"){
    string job=args.Length>7?args[7]:args[1];string result=System.IO.Path.Combine(job,args.Length>7?"result.txt":"extraction.log");
    try{if(args.Length>7)Work.Configure(()=>File.Exists(System.IO.Path.Combine(job,"cancel")),message=>{try{File.WriteAllText(System.IO.Path.Combine(job,"progress.txt"),message);if(message.StartsWith("IVAD_PROGRESS|"))File.WriteAllText(System.IO.Path.Combine(job,"frames-progress.txt"),message);}catch(IOException){}},path=>File.AppendAllText(System.IO.Path.Combine(job,"created.txt"),path+Environment.NewLine));var culture=System.Globalization.CultureInfo.InvariantCulture;int n=args.Length>7?Media.ExtractWithProgress(args[1],args[2],Double.Parse(args[3],culture),(int)Double.Parse(args[6],culture),Double.Parse(args[4],culture),Double.Parse(args[5],culture),System.IO.Path.Combine(job,"frames")):Media.Extract(args[1],args[2],Double.Parse(args[3],culture),500);File.WriteAllText(result,"PASS extracted="+n+"; reaching configured limit requires another run for remaining frames");return 0;}
    catch(OperationCanceledException e){File.WriteAllText(result,e.ToString());return 2;}catch(Exception e){File.WriteAllText(result,e.ToString());return 1;}
   }
   if(args.Length==3&&args[0]=="--deployment-crash")return DeploymentChecks.CrashWriter(args[1],args[2]);
   var app=new Application();var window=new MainWindow();
   if(args.Length==2&&(args[0]=="--deployment-check"||args[0]=="--deployment-reopen")){int result=window.RunDeploymentChecks(args[1],args[0]=="--deployment-reopen");app.Shutdown(result);return result;}
   if(args.Length==3&&args[0]=="--ui-check"){int result=window.RunUiChecks(args[1],args[2]);app.Shutdown(result);return result;}
   if(args.Length>=2&&args[0]=="--smoke")window.Loaded+=(s,e)=>{var timer=new System.Windows.Threading.DispatcherTimer{Interval=TimeSpan.FromMilliseconds(800)};timer.Tick+=(x,y)=>{timer.Stop();try{if(args.Length==3)window.SmokeProject(args[2]);window.UpdateLayout();var bmp=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bmp.Render(window);var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bmp));using(var f=File.Create(args[1]))encoder.Save(f);}catch(Exception ex){File.WriteAllText(args[1]+".error.txt",ex.ToString());app.Shutdown(1);}finally{window.Close();}};timer.Start();};
   return app.Run(window);
  }
 }
}
