// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media.Imaging;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  ComboBox frameVideoFilter=new ComboBox(),frameStateFilter=new ComboBox();
  List<Entity> orderedFrames=new List<Entity>();
  Dictionary<string,List<Entity>> shapeIndex=new Dictionary<string,List<Entity>>();
  Dictionary<string,Entity> latestReviews=new Dictionary<string,Entity>();
  Dictionary<string,Choice> frameChoices=new Dictionary<string,Choice>();
  ObservableCollection<Choice> visibleFrames=new ObservableCollection<Choice>();
  int confirmedCount,visibleConfirmedCount;bool filtering;
  BatchUndo batchUndo;
  sealed class CachedBitmap {public string key;public BitmapImage bitmap;public long bytes;}
  readonly LinkedList<CachedBitmap> bitmapLru=new LinkedList<CachedBitmap>();
  long bitmapBytes;const long BitmapBudget=64L*1024*1024;
  BitmapImage GetBitmap(Entity f){
   string path=Rules.SafePath(store.Root,f.Text("asset_path"));var info=new FileInfo(path);string key=path+"/"+info.Length+"/"+info.LastWriteTimeUtc.Ticks;
   for(var n=bitmapLru.First;n!=null;n=n.Next)if(n.Value.key==key){var b=n.Value.bitmap;bitmapLru.Remove(n);bitmapLru.AddFirst(n);return b;}
   var bitmap=new BitmapImage();bitmap.BeginInit();bitmap.CacheOption=BitmapCacheOption.OnLoad;bitmap.UriSource=new Uri(path);bitmap.CreateOptions=BitmapCreateOptions.IgnoreImageCache;bitmap.EndInit();bitmap.Freeze();
   long bytes=(long)bitmap.PixelWidth*bitmap.PixelHeight*((bitmap.Format.BitsPerPixel+7)/8);
   while(bitmapLru.Count>0&&(bitmapLru.Count>=12||bitmapBytes+bytes>BitmapBudget)){bitmapBytes-=bitmapLru.Last.Value.bytes;bitmapLru.RemoveLast();}
   if(bytes<=BitmapBudget){bitmapLru.AddFirst(new CachedBitmap{key=key,bitmap=bitmap,bytes=bytes});bitmapBytes+=bytes;}
   return bitmap;
  }
  void ClearImageCache(){bitmapLru.Clear();bitmapBytes=0;batchUndo=null;}
  Entity LatestReview(string id){Entity r;return latestReviews.TryGetValue(id,out r)?r:null;}
  string FrameLabel(Entity f){return (f.Number("pts_us")/1000000).ToString("F3",System.Globalization.CultureInfo.InvariantCulture)+" s · "+FrameStateText(f.Text("state"));}
  bool FrameMatches(Entity f){if(frameStateFilter.SelectedIndex==3 ? f.Text("queue_deleted")!="True" : f.Text("queue_deleted")=="True")return false;var v=frameVideoFilter.SelectedItem as Choice;var r=LatestReview(f.id);return (v==null||v.Id==""||v.Id==f.Text("video_id"))&&(frameStateFilter.SelectedIndex==0||frameStateFilter.SelectedIndex==3||(frameStateFilter.SelectedIndex==1?(r==null||r.Text("status")!="confirmed"):r!=null&&r.Text("status")=="confirmed"));}
  void BuildFrameFilters(Panel panel){
   frames.SelectionMode=SelectionMode.Extended;
   frameStateFilter.ItemsSource=new[]{"全部状态","待标注 / 未确认","已确认","已删除"};frameStateFilter.SelectedIndex=0;
   Name(frameVideoFilter,"帧视频筛选");Name(frameStateFilter,"帧状态筛选");panel.Children.Add(frameVideoFilter);panel.Children.Add(frameStateFilter);
   frameVideoFilter.SelectionChanged+=(s,e)=>ChangeFrameFilter();frameStateFilter.SelectionChanged+=(s,e)=>ChangeFrameFilter();
   var row=new System.Windows.Controls.Primitives.UniformGrid{Columns=2};AddTool(row,"批量标记正常",BatchNormal);AddTool(row,"撤销最近批次",UndoNormalBatch);AddTool(row,"批量删除抽帧",()=>QueueChange(true));AddTool(row,"恢复选中帧",()=>QueueChange(false));foreach(Button b in row.Children){b.Padding=new Thickness(2);b.Margin=new Thickness(1);b.Content=new TextBlock{Text=b.Content.ToString(),TextWrapping=TextWrapping.Wrap,TextAlignment=TextAlignment.Center,FontSize=11};}panel.Children.Add(row);panel.Children.Add(selectionCount);frames.RangeChanged+=()=>selectionCount.Text="已选择 "+frames.Ids.Count+" 帧";
   panel.Children.Add(new TextBlock{Text="Ctrl 多选 · Shift 范围选择",FontSize=11,TextWrapping=TextWrapping.Wrap});
  }
  int acceptedVideo=0,acceptedState=0;
  void ChangeFrameFilter(){if(filtering||store==null)return;if(busy||polygon.Count>0||start.HasValue||reviewEdited){filtering=true;frameVideoFilter.SelectedIndex=acceptedVideo;frameStateFilter.SelectedIndex=acceptedState;filtering=false;status.Text="请先保存审核选择并完成或取消绘制，再切换筛选。草稿已保留。";return;}acceptedVideo=frameVideoFilter.SelectedIndex;acceptedState=frameStateFilter.SelectedIndex;ApplyFrameFilter();}
  void RebuildFrameMetadata(){
   orderedFrames=store.Data.entities.Where(e=>e.kind=="Frame").OrderBy(e=>e.Text("video_id")).ThenBy(e=>e.Number("source_timestamp_100ns")).ToList();
   shapeIndex=store.Data.entities.Where(e=>e.kind=="Annotation"||e.kind=="ROI").GroupBy(e=>e.Text("frame_id")).ToDictionary(g=>g.Key,g=>g.ToList());
   latestReviews=store.Data.entities.Where(e=>e.kind=="Review").GroupBy(e=>e.Text("frame_id")).ToDictionary(g=>g.Key,g=>g.Last());confirmedCount=latestReviews.Values.Count(e=>e.Text("status")=="confirmed");
   frameChoices=orderedFrames.ToDictionary(e=>e.id,e=>new Choice{Id=e.id,Name=FrameLabel(e)});
   filtering=true;string old=(frameVideoFilter.SelectedItem as Choice)==null?"":((Choice)frameVideoFilter.SelectedItem).Id;var choices=new List<Choice>{new Choice{Id="",Name="全部视频"}};choices.AddRange(store.Data.entities.Where(e=>e.kind=="Video").Select(e=>new Choice{Id=e.id,Name=e.Text("original_name")}));frameVideoFilter.ItemsSource=choices;frameVideoFilter.SelectedItem=choices.FirstOrDefault(c=>c.Id==old)??choices[0];acceptedVideo=frameVideoFilter.SelectedIndex;acceptedState=frameStateFilter.SelectedIndex;filtering=false;
   visibleFrames=new ObservableCollection<Choice>(orderedFrames.Where(FrameMatches).Select(e=>frameChoices[e.id]));visibleConfirmedCount=visibleFrames.Count(c=>LatestReview(c.Id)!=null&&LatestReview(c.Id).Text("status")=="confirmed");frames.ItemsSource=visibleFrames;
  }
  void ClearFrame(){frame=null;selected=null;image.Source=null;videoStill.Source=null;geometries.ItemsSource=null;canvas.Children.Clear();canvas.Children.Add(image);UpdateFrameDetails();}
  void ApplyFrameFilter(){
   string old=frame==null?null:frame.id;refreshing=true;visibleFrames=new ObservableCollection<Choice>(orderedFrames.Where(FrameMatches).Select(e=>frameChoices[e.id]));visibleConfirmedCount=visibleFrames.Count(c=>LatestReview(c.Id)!=null&&LatestReview(c.Id).Text("status")=="confirmed");frames.ItemsSource=visibleFrames;frames.SelectedItem=visibleFrames.FirstOrDefault(c=>c.Id==old);if(frames.SelectedItem==null&&visibleFrames.Count>0)frames.SelectedIndex=0;refreshing=false;
   if(frames.SelectedItem==null)ClearFrame();else{frame=store.Find(((Choice)frames.SelectedItem).Id);selected=null;ShowFrame();}UpdateVideoFrames();
  }
  string NextVisibleFrame(string id){int i=visibleFrames.IndexOf(frameChoices[id]);return i>=0&&i+1<visibleFrames.Count?visibleFrames[i+1].Id:null;}
  void UpdateSavedFrame(string id){
   bool shown=visibleFrames.Contains(frameChoices[id]);var prior=LatestReview(id);if(shown&&prior!=null&&prior.Text("status")=="confirmed")visibleConfirmedCount--;if(prior!=null&&prior.Text("status")=="confirmed")confirmedCount--;
   // A successful review appends frame revision, Review, Review revision in that order.
   var r=store.Data.entities[store.Data.entities.Count-2];latestReviews[id]=r;if(r.Text("status")=="confirmed")confirmedCount++;
   var f=store.Find(id);if(shown&&FrameMatches(f)&&r.Text("status")=="confirmed")visibleConfirmedCount++;frameChoices[id].Name=FrameLabel(f);
   if(!FrameMatches(f)){refreshing=true;visibleFrames.Remove(frameChoices[id]);refreshing=false;}
   UpdateFrameDetails();
  }
  void BatchNormal(){
   Require();if(polygon.Count>0||start.HasValue||reviewEdited){status.Text="请先保存当前草稿，批次尚未执行。";return;}
   string[] ids=frames.SelectionIds();string a=actor.Text;
   Run("批量标记正常",()=>store.MarkNormalBatch(ids,a),undo=>{batchUndo=undo;Refresh();extractionSummary="整批已提交，可撤销最近批次。";});
  }
  void UndoNormalBatch(){Require();if(polygon.Count>0||start.HasValue||reviewEdited){status.Text="请先保存当前草稿。";return;}var undo=batchUndo;string a=actor.Text;Run("撤销最近批次",()=>{store.UndoBatch(undo,a);return store;},s=>{batchUndo=null;Refresh();});}
 }
}
