// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  double viewportZoom=1;Vector viewportOffset;Point? panStart;Vector panOrigin;
  void ConfigureViewport(){
   canvas.RenderTransformOrigin=new Point(.5,.5);
   imageHost.PreviewMouseWheel+=(s,e)=>{if(frame==null||busy||start.HasValue||panStart.HasValue)return;ZoomViewport(e.Delta>0?1.25:.8);e.Handled=true;};
   imageHost.PreviewMouseDown+=(s,e)=>{if(e.ChangedButton!=MouseButton.Middle||frame==null||busy||start.HasValue)return;panStart=e.GetPosition(imageHost);panOrigin=viewportOffset;imageHost.CaptureMouse();e.Handled=true;};
   imageHost.PreviewMouseMove+=(s,e)=>{if(!panStart.HasValue)return;viewportOffset=panOrigin+(e.GetPosition(imageHost)-panStart.Value);ApplyViewport();e.Handled=true;};
   imageHost.PreviewMouseUp+=(s,e)=>{if(e.ChangedButton!=MouseButton.Middle||!panStart.HasValue)return;panStart=null;imageHost.ReleaseMouseCapture();e.Handled=true;};
   imageHost.LostMouseCapture+=(s,e)=>{panStart=null;};
  }
  void ApplyViewport(){var g=new TransformGroup();g.Children.Add(new ScaleTransform(viewportZoom,viewportZoom));g.Children.Add(new TranslateTransform(viewportOffset.X,viewportOffset.Y));canvas.RenderTransform=g;}
  void ZoomViewport(double factor){if(frame==null||start.HasValue||panStart.HasValue)return;viewportZoom=Math.Max(.25,Math.Min(8,viewportZoom*factor));ApplyViewport();}
  void ResetViewport(){viewportZoom=1;viewportOffset=new Vector();panStart=null;if(imageHost.IsMouseCaptured)imageHost.ReleaseMouseCapture();ApplyViewport();}
  public void OpenProjectPath(string path){Use(new Store(Path.GetFullPath(path)));Navigate("标注与审核");}
  void SaveIdsBaseline(){Require();var d=new Microsoft.Win32.SaveFileDialog{Filter="IDS 基线|*.ids-baseline.json",DefaultExt=".ids-baseline.json",AddExtension=true,OverwritePrompt=true,FileName="baseline.ids-baseline.json"};if(d.ShowDialog(this)!=true)return;string path=d.FileName,root=store.Root;Run("保存增量基线",()=>{var s=new Store(root);Rules.VerifyAssets(s.Data,s.Root);var doc=QueueProjection.Active(s.Data);File.WriteAllText(path,Codec.Json(doc),new System.Text.UTF8Encoding(false));return path;},x=>{extractionSummary="基线已保存："+x;});}
  void ExportIdsIncremental(){Require();string baseline=Open("IDS 基线|*.ids-baseline.json;*.json");if(baseline==null)return;var d=new Microsoft.Win32.SaveFileDialog{Filter="IDS 增量包|*.ids",DefaultExt=".ids",AddExtension=true,OverwritePrompt=false,FileName="incremental.ids"};if(d.ShowDialog(this)!=true)return;string path=Workflow.AvailablePath(d.FileName),root=store.Root;Run("导出 IDS 增量包",()=>{var doc=Codec.Parse<Document>(File.ReadAllText(baseline));Rules.Validate(doc);Packages.Export(new Store(root),path,doc);return path;},x=>{extractionSummary="增量包已保存："+x;});}
 }
}
