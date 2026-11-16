// SPDX-License-Identifier: Apache-2.0
using System;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  TextBlock selectionCount=new TextBlock{Text="已选择 0 帧",Margin=new Thickness(0,5,0,5)};
  void QueueChange(bool deleted){
   Require();if(reviewEdited||polygon.Count>0||start.HasValue){status.Text="请先保存当前草稿，未执行删除或恢复。";return;}
   var ids=frames.SelectionIds();if(ids.Length==0){status.Text="请先选择帧。";return;}
   var set=new System.Collections.Generic.HashSet<string>(ids);
   bool warning=store.Data.entities.Any(e=>e.kind=="Annotation"&&set.Contains(e.Text("frame_id"))&&e.Text("deleted")!="True")||ids.Any(id=>store.Find(id).Text("state")=="abnormal"&&LatestReview(id)!=null&&LatestReview(id).Text("status")=="confirmed");
   string message=(deleted?"从标注队列软删除":"恢复")+ids.Length+" 帧。源 PNG、全部标注和审核历史仍保留在本地。"+(deleted?"已删除帧不进入新导出的 IDS；恢复须在原本地项目执行。":"");
   if(deleted&&warning)message+="\n警告：所选包含已有标注框或已确认异常帧，删除会将其排除出有效数据集。";
   if(MessageBox.Show(this,message,"确认"+(deleted?"批量软删除":"恢复帧"),MessageBoxButton.OKCancel,warning?MessageBoxImage.Warning:MessageBoxImage.Question)!=MessageBoxResult.OK)return;
   string actorName=actor.Text;int old=frames.SelectedIndex;
   Run(deleted?"批量软删除":"恢复帧",()=>{store.SetQueueDeleted(ids,deleted,actorName);return store;},s=>{batchUndo=null;Refresh();if(frames.Items.Count>0)frames.SelectedIndex=Math.Min(Math.Max(0,old),frames.Items.Count-1);extractionSummary="已处理 "+ids.Length+" 帧，未删除物理文件。";});
  }
  void ConfigureRangeStyle(){
   var style=new Style(typeof(ListBoxItem),frames.TryFindResource(typeof(ListBoxItem)) as Style);
   var template=new ControlTemplate(typeof(ListBoxItem));var border=new FrameworkElementFactory(typeof(Border));border.SetBinding(Border.BackgroundProperty,new System.Windows.Data.Binding("Background"){RelativeSource=new System.Windows.Data.RelativeSource(System.Windows.Data.RelativeSourceMode.TemplatedParent)});border.SetValue(Border.PaddingProperty,new Thickness(10));border.AppendChild(new FrameworkElementFactory(typeof(ContentPresenter)));template.VisualTree=border;style.Setters.Add(new Setter(Control.TemplateProperty,template));style.Setters.Add(new Setter(Control.BackgroundProperty,Brushes.Transparent));
   var trigger=new Trigger{Property=RangeFrameList.BatchSelectedProperty,Value=true};trigger.Setters.Add(new Setter(Control.BackgroundProperty,new SolidColorBrush(System.Windows.Media.Color.FromRgb(190,220,248))));trigger.Setters.Add(new Setter(Control.ForegroundProperty,Brushes.Black));style.Triggers.Add(trigger);frames.ItemContainerStyle=style;
  }
 }
}
