// SPDX-License-Identifier: Apache-2.0
// In-process WPF regression checks. Never substitutes for native mouse acceptance.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  static void Check(bool result,string message){if(!result)throw new InvalidOperationException(message);}
  void AwaitOperation(){var loop=new DispatcherFrame();var timeout=DateTime.UtcNow.AddSeconds(30);var timer=new DispatcherTimer{Interval=TimeSpan.FromMilliseconds(20)};timer.Tick+=(s,e)=>{if(!busy||DateTime.UtcNow>timeout){timer.Stop();loop.Continue=false;}};timer.Start();Dispatcher.PushFrame(loop);Check(!busy,"Background operation timeout");Check(!status.Text.StartsWith("操作失败"),status.Text);}
  static IEnumerable<FrameworkElement> Elements(DependencyObject node){for(int i=0;i<VisualTreeHelper.GetChildrenCount(node);i++){var child=VisualTreeHelper.GetChild(node,i);var element=child as FrameworkElement;if(element!=null)yield return element;foreach(var nested in Elements(child))yield return nested;}}
  static bool Within(DependencyObject child,DependencyObject ancestor){for(var p=child;p!=null;p=LogicalTreeHelper.GetParent(p))if(p==ancestor)return true;return false;}
  public int RunUiChecks(string output,string package){
   System.Threading.SynchronizationContext.SetSynchronizationContext(new DispatcherSynchronizationContext(Dispatcher));
   Directory.CreateDirectory(output);var results=new List<object>();int failed=0;
   Action<string,Action> test=(name,action)=>{File.AppendAllText(Path.Combine(output,"execution.log"),"START "+name+Environment.NewLine);try{action();results.Add(new{name=name,status="PASS",mode="in-process WPF controls / synthetic layout; NOT native GUI"});File.AppendAllText(Path.Combine(output,"execution.log"),"PASS "+name+Environment.NewLine);}catch(Exception e){failed++;results.Add(new{name=name,status="FAIL",error=e.ToString()});File.AppendAllText(Path.Combine(output,"execution.log"),"FAIL "+name+" "+e+Environment.NewLine);}};
   test("window/native-chrome-contract",()=>Check(WindowStyle==WindowStyle.SingleBorderWindow&&ResizeMode==ResizeMode.CanResize&&ShowInTaskbar,"native window controls configured"));
   test("controls/empty-main-directory-and-hidden-review",()=>{Check(masterRoot.Text=="","no implicit directory");Check(review.Visibility==Visibility.Collapsed&&reviewLabel.Visibility==Visibility.Collapsed,"review hidden by default");actor.Text="本地管理员";Check(review.Visibility==Visibility.Visible,"admin visible");actor.Text="本地审核员";Check(review.Visibility==Visibility.Collapsed,"non-admin hidden");});
   test("controls/load-isolated-fixture",()=>{Use(Packages.Import(package,Path.Combine(output,"project")));Navigate("标注与审核");Check(frame!=null,"fixture has frames");Check(context.Text.Contains("项目：")&&context.Text.Contains("设备：")&&context.Text.Contains("摄像头："),"read only context");});
   test("controls/two-stages-and-utility-navigation",()=>{Check(tabs.Items.Count==2&&((TabItem)tabs.Items[0]).Header.ToString()=="视频与抽帧"&&((TabItem)tabs.Items[1]).Header.ToString()=="标注与审核","exact two stage headers");Navigate("项目");Check(projectPage.Visibility==Visibility.Visible&&tabs.Visibility==Visibility.Collapsed,"project utility page");Navigate("IDS");Check(idsPage.Visibility==Visibility.Visible&&projectPage.Visibility==Visibility.Collapsed,"IDS utility page");Navigate("标注与审核");Check(tabs.Visibility==Visibility.Visible&&tabs.SelectedIndex==1,"return to annotation");});
   test("controls/stage-field-isolation",()=>{Check(Within(rangeStart,videoParameters)&&Within(rangeEnd,videoParameters)&&Within(interval,videoParameters)&&Within(videos,videoParameters),"video-only parameters");Check(Within(actor,annotationParameters)&&Within(state,annotationParameters)&&Within(faults,annotationParameters)&&!Within(review,videoParameters),"annotation-only parameters");Check(!Within(masterRoot,tabs)&&!Within(cameras,tabs),"project settings outside main tabs");});
   test("controls/themed-editable-combo-keeps-text-entry",()=>{Navigate("项目");var content=(FrameworkElement)Content;content.Measure(new Size(1500,850));content.Arrange(new Rect(0,0,1500,850));content.UpdateLayout();string old=siteName.Text;var edit=(TextBox)siteName.Template.FindName("PART_EditableTextBox",siteName);Check(edit!=null&&edit.Visibility==Visibility.Visible,"editable combo template part");edit.Text="临时界面输入";Check(siteName.Text=="临时界面输入","editable text propagated to combo");siteName.Text=old;Navigate("标注与审核");});
   test("controls/previous-next-boundaries",()=>{frames.SelectedIndex=0;string first=frame.id;NavigateFrame(-1);Check(frame.id==first,"first boundary");NavigateFrame(1);Check(frames.SelectedIndex==1,"next button");NavigateFrame(-1);Check(frame.id==first,"previous button");});
   test("controls/video-list-and-preview-source-separation",()=>{Navigate("视频与抽帧");Check(videoFrames.Items.Count>0&&videoStill.Source!=null,"extracted frame preview");Check(player.Source==null&&player.Visibility==Visibility.Collapsed,"no autoplay or open file");var expected=(Choice)videoFrames.Items[1];videoFrames.SelectedIndex=1;Check(frame.id==expected.Id,"video selection syncs annotation frame");Navigate("标注与审核");Check(frame.id==expected.Id&&player.Source==null,"stage switch keeps selection and closes player");});
   test("controls/review-save-next-preserve-fault-and-tool",()=>{
    var created=store.Add("Fault",new Dictionary<string,object>{{"name","持续标注故障"},{"taxonomy_version",1}});store.Save();Refresh();faults.SelectedItem=faults.Items.Cast<Choice>().First(x=>x.Id==created.id);faultName.Text="持续输入名称";shape.SelectedIndex=1;string old=frame.id,next=Workflow.NextFrame(store.Data.entities,old);state.SelectedIndex=1;review.SelectedIndex=1;SaveReview();AwaitOperation();
    Check(frame.id==next,"must advance after successful commit");Check(Selected(faults)==created.id&&faultName.Text=="持续输入名称"&&shape.SelectedIndex==1,"fault/tool preserved");var reopened=new Store(store.Root);Check(reopened.Data.entities.Last(x=>x.kind=="Review"&&x.Text("frame_id")==old).Text("status")=="confirmed","non-admin auto-confirm persists");
   });
   test("controls/admin-result-and-last-frame",()=>{actor.Text="本地管理员";frames.SelectedIndex=frames.Items.Count-1;string last=frame.id;state.SelectedIndex=3;review.SelectedIndex=2;shape.SelectedIndex=2;SaveReview();AwaitOperation();Check(frame.id==last&&shape.SelectedIndex==2,"last frame stays");Check(new Store(store.Root).Data.entities.Last(x=>x.kind=="Review"&&x.Text("frame_id")==last).Text("status")=="needs_work","admin result preserved");actor.Text="本地审核员";});
   test("controls/geometry-select-delete-persistence",()=>{var a=store.AddAnnotation(frame.id,Selected(faults),"box",new[]{1.0,1,25,25},false);Refresh();geometries.SelectedItem=geometries.Items.Cast<Choice>().First(x=>x.Id==a.id);Check(selected==a.id&&shape.SelectedIndex==3,"geometry selected / move tool");DeleteSelected();AwaitOperation();Check(new Store(store.Root).Find(a.id).Text("deleted")=="True","soft deletion persisted");});
   test("controls/progress-planning-count-and-completion",()=>{extractionProgress="统计实际抽帧总数|2|-1";UpdateExtraction();Check(extractionCount.Text=="2 / 统计中","unknown total not fabricated");extractionProgress="正在抽帧|2|6";UpdateExtraction();Check(extractionBar.Value==2&&extractionBar.Maximum==6&&extractionCount.Text=="2 / 6","exact fraction");extractionProgress="抽帧完成，已保存|6|6";UpdateExtraction();Check(extractionBar.Value==6&&extractionState.Text.Contains("已保存"),"committed state");});
   test("controls/frame-list-bindings",()=>{var content=(FrameworkElement)Content;content.Measure(new Size(1480,850));content.Arrange(new Rect(0,0,1480,850));content.UpdateLayout();Check(Elements(frames).OfType<TextBlock>().Any(x=>x.Text.Contains("s ·")),"frame labels bind Choice properties");});
   test("actions/right-footer-arrows-and-single-primary",()=>{
    Check(Within(saveNext,annotationActionBar)&&Within(markNormal,annotationActionBar)&&!Within(saveNext,annotationParameters)&&!Within(markNormal,annotationParameters),"both actions outside left panel and in preview footer");
    Check(((TextBlock)previousFrame.Content).Text=="<"&&((TextBlock)nextFrame.Content).Text==">"&&previousFrame.ToolTip.ToString()=="上一帧"&&nextFrame.ToolTip.ToString()=="下一帧","arrow labels and accessible tooltips");
    Check(previousFrame.MinHeight>=40&&nextFrame.Width>=40&&saveNext.Style==Resources["Primary"],"large navigation and primary save");
   });
   test("actions/ctrl-s-binding-scope",()=>{
    var bindings=InputBindings.OfType<KeyBinding>().Where(b=>b.Key==Key.S&&b.Modifiers==ModifierKeys.Control).ToList();Check(bindings.Count==1&&bindings[0].Command==saveAdvanceCommand,"one unambiguous Ctrl+S binding");
    Navigate("视频与抽帧");Check(!saveAdvanceCommand.CanExecute(null,this),"no save on video page");Navigate("IDS");Check(!saveAdvanceCommand.CanExecute(null,this),"no save on IDS page");Navigate("项目");Check(!saveAdvanceCommand.CanExecute(null,this),"no save on project page");Navigate("标注与审核");Check(saveAdvanceCommand.CanExecute(null,this),"save enabled on annotation");
   });
   test("actions/ctrl-s-empty-frame-normal-and-single-commit",()=>{
    frames.SelectedIndex=1;Check(!Shapes().Any(x=>x.kind=="Annotation"),"empty fault fixture");string id=frame.id,next=Workflow.NextFrame(store.Data.entities,id);int count=store.Data.entities.Count(x=>x.kind=="Review");shape.SelectedIndex=1;string fault=Selected(faults);state.SelectedIndex=0;
    saveAdvanceCommand.Execute(null,this);Check(busy&&!saveAdvanceCommand.CanExecute(null,this),"disabled during commit");SaveReview();AwaitOperation();var disk=new Store(store.Root);
    Check(disk.Find(id).Text("state")=="normal"&&frame.id==next,"empty frame normal and advanced");Check(disk.Data.entities.Count(x=>x.kind=="Review")==count+1,"busy duplicate ignored");Check(disk.Data.entities.Last(x=>x.kind=="Review"&&x.Text("frame_id")==id).Text("status")=="confirmed","auto confirmed");Check(shape.SelectedIndex==1&&Selected(faults)==fault&&status.Text.Contains("已保存并进入下一帧"),"preferences and lightweight feedback");
   });
   test("actions/ctrl-s-box-abnormal-and-persistent",()=>{
    frames.SelectedIndex=1;string id=frame.id,next=Workflow.NextFrame(store.Data.entities,id);var box=store.AddAnnotation(id,Selected(faults),"box",new[]{2.0,2,28,28},false);Refresh();shape.SelectedIndex=3;state.SelectedIndex=1;
    saveAdvanceCommand.Execute(null,this);AwaitOperation();var disk=new Store(store.Root);Check(disk.Find(id).Text("state")=="abnormal"&&frame.id==next&&shape.SelectedIndex==3,"fault overrides stale normal and advances");Check(disk.Find(box.id).Text("deleted")!="True"&&Points(disk.Find(box.id)).SequenceEqual(new[]{2.0,2,28,28}),"geometry survives review save");
   });
   test("actions/normal-button-saves-advances-keeps-geometry",()=>{
    frames.SelectedIndex=1;string id=frame.id,next=Workflow.NextFrame(store.Data.entities,id);string[] ids=Shapes().Select(x=>x.id).ToArray();Check(ids.Length>0,"annotated fixture");markNormal.RaiseEvent(new RoutedEventArgs(System.Windows.Controls.Primitives.ButtonBase.ClickEvent));AwaitOperation();var disk=new Store(store.Root);
    Check(disk.Find(id).Text("state")=="normal"&&frame.id==next&&status.Text.Contains("已标记为正常并进入下一帧"),"normal button commits and advances");Check(ids.All(x=>disk.Find(x).Text("deleted")!="True"),"normal action does not delete geometry");
   });
   test("actions/primary-button-deleted-box-and-roi-are-not-faults",()=>{
    frames.SelectedIndex=1;string id=frame.id;foreach(var a in Shapes().Where(x=>x.kind=="Annotation").ToList())store.DeleteGeometry(a.id,"test");var roi=store.AddAnnotation(id,null,"polygon",new[]{1.0,1,30,1,30,30},true);Refresh();state.SelectedIndex=2;
    saveNext.RaiseEvent(new RoutedEventArgs(System.Windows.Controls.Primitives.ButtonBase.ClickEvent));AwaitOperation();var disk=new Store(store.Root);Check(disk.Find(id).Text("state")=="normal"&&disk.Find(roi.id).Text("deleted")!="True","ROI preserved, deleted faults excluded, primary saves normal");
   });
   test("actions/incomplete-drawing-stays-without-dialog",()=>{
    frames.SelectedIndex=1;string id=frame.id,before=Codec.Fingerprint(store.Data);shape.SelectedIndex=1;polygon.Add(new Point(1,1));polygon.Add(new Point(2,2));saveAdvanceCommand.Execute(null,this);
    Check(!busy&&frame.id==id&&polygon.Count==2&&Codec.Fingerprint(store.Data)==before&&status.Text.Contains("请先完成形状"),"pending polygon retained with nonmodal feedback");polygon.Clear();start=new Point(1,1);markNormal.RaiseEvent(new RoutedEventArgs(System.Windows.Controls.Primitives.ButtonBase.ClickEvent));Check(!busy&&start.HasValue&&frame.id==id,"pending box retained");start=null;Redraw();
   });
   test("actions/validation-failure-does-not-advance",()=>{
    string id=frame.id,before=Codec.Fingerprint(new Store(store.Root).Data);actor.Text="";saveAdvanceCommand.Execute(null,this);Check(!busy&&frame.id==id&&status.Text.StartsWith("操作失败")&&Codec.Fingerprint(new Store(store.Root).Data)==before,"invalid reviewer cannot advance or mutate");actor.Text="本地审核员";
   });
   test("actions/explicit-unknown-remains-supported",()=>{
    frames.SelectedIndex=1;string id=frame.id;state.SelectedIndex=3;SaveAndAdvance(false,true);AwaitOperation();Check(new Store(store.Root).Find(id).Text("state")=="unknown","explicit state path preserves unknown");
   });
   test("actions/last-frame-save-and-normal-feedback",()=>{
    frames.SelectedIndex=frames.Items.Count-1;string last=frame.id;saveAdvanceCommand.Execute(null,this);AwaitOperation();Check(frame.id==last&&status.Text.Contains("已是最后一帧")&&!nextFrame.IsEnabled,"keyboard last-frame stable");markNormal.RaiseEvent(new RoutedEventArgs(System.Windows.Controls.Primitives.ButtonBase.ClickEvent));AwaitOperation();Check(frame.id==last&&status.Text.Contains("已标记为正常，已是最后一帧"),"normal last-frame stable");
   });
   test("actions/compact-labels-source-heading-and-confirmed-count",()=>{
    Check(frames.Items.Cast<Choice>().All(x=>x.Name==(store.Find(x.Id).Number("pts_us")/1000000).ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+" s · "+FrameStateText(store.Find(x.Id).Text("state"))),"rows contain only seconds and state");
    var source=store.Find(frame.Text("video_id"));Check(frameSource.Text.Contains(store.Find(source.Text("camera_id")).Text("name"))&&frameSource.Text.Contains(source.Text("original_name"))&&frameSource.ToolTip.ToString()==frameSource.Text,"current source once above list with full tooltip");
    int count=store.Data.entities.Where(x=>x.kind=="Review").GroupBy(x=>x.Text("frame_id")).Count(g=>g.Last().Text("status")=="confirmed");Check(frameSummary.Text=="已确认 "+count+" / "+frames.Items.Count,"confirmed count retained");
   });
   foreach(var dimensions in new[]{new[]{1920,1080},new[]{2560,1440},new[]{2560,1600}})foreach(double dpi in new[]{1.0,1.25,1.5,2.0}){
    int w=dimensions[0],h=dimensions[1];double scale=dpi;
    test("layout/"+w+"x"+h+"-"+(int)(scale*100)+"percent",()=>{
     var content=(FrameworkElement)Content;double width=w/scale-20,height=h/scale-70;
     foreach(TabItem tab in tabs.Items){Navigate(tab.Header.ToString());content.Measure(new Size(width,height));content.Arrange(new Rect(0,0,width,height));content.UpdateLayout();
      bool video=tabs.SelectedIndex==0;var landmarks=video?new FrameworkElement[]{tabs,videoFrames,videoHost,status,extractionBar,extractionState,videoParameters}:new FrameworkElement[]{tabs,frames,imageHost,context,status,saveNext,markNormal,previousFrame,nextFrame,annotationActionBar,frameSource,annotationParameters};
      foreach(FrameworkElement element in landmarks){Rect bounds=element.TransformToAncestor(content).TransformBounds(new Rect(element.RenderSize));Check(bounds.Left>=-1&&bounds.Top>=-1&&bounds.Right<=width+1&&bounds.Bottom<=height+1,"outside client: "+element.GetType().Name+" "+bounds+" client="+width+"x"+height);}
      var host=video?videoHost:imageHost;Check(host.ActualWidth>=170&&host.ActualHeight>80,"usable preview: "+host.RenderSize);var scroll=video?videoParameters:annotationParameters;Check(scroll.ActualWidth>130&&scroll.ViewportHeight>60,"scrollable parameters");
      var picture=new RenderTargetBitmap(w,h,96*scale,96*scale,PixelFormats.Pbgra32);picture.Render(content);var png=new PngBitmapEncoder();png.Frames.Add(BitmapFrame.Create(picture));using(var file=File.Create(Path.Combine(output,(video?"video-":"annotation-")+w+"x"+h+"-"+(int)(scale*100)+".png")))png.Save(file);
     }
    });
   }
   test("controls/reopen-preserves-saved-records",()=>{string before=Codec.Fingerprint(store.Data);Use(new Store(store.Root));Check(Codec.Fingerprint(store.Data)==before,"reopen identical");reviewEdited=false;});
   ticker.Stop();File.WriteAllText(Path.Combine(output,"results.json"),Codec.Json(new{passed=results.Count-failed,failed=failed,gui_status="NOT TESTED",scope="In-process controls and synthetic physical dimensions/DPI. No native mouse or actual monitor/maximize test.",tests=results}));return failed==0?0:1;
  }
 }
}
