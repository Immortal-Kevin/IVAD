// Private NVIDIA integration. No public distribution license granted.
using System;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using Ivad.Ids;
namespace Ivad.Annotator {
 public sealed partial class MainWindow {
  void OpenNvidia(){
   Require();string root=store.Root;
   var panel=new StackPanel{Margin=new Thickness(20)};
   var output=new TextBox{IsReadOnly=true,AcceptsReturn=true,TextWrapping=TextWrapping.Wrap,Height=340,VerticalScrollBarVisibility=ScrollBarVisibility.Auto};
   var epochs=new TextBox{Text="1"};var model=new TextBox();var job=new TextBox();var version=new TextBox();
   panel.Children.Add(new TextBlock{Text="RF-DETR Nano CUDA · 当前项目独立模型库",FontSize=20});
   panel.Children.Add(new TextBlock{Text="Epoch"});panel.Children.Add(epochs);
   panel.Children.Add(new TextBlock{Text="模型 UUID（验证时必填）"});panel.Children.Add(model);
   panel.Children.Add(new TextBlock{Text="数据版本 UUID（留空从已确认 IDS 创建）"});panel.Children.Add(version);
   panel.Children.Add(new TextBlock{Text="任务 UUID（状态/取消）"});panel.Children.Add(job);
   var buttons=new WrapPanel();panel.Children.Add(buttons);panel.Children.Add(output);
   Action<string,string> add=(label,action)=>{
    var b=new Button{Content=label,Margin=new Thickness(4),Padding=new Thickness(8)};buttons.Children.Add(b);
    b.Click+=async(s,e)=>{
     int n;if(!Int32.TryParse(epochs.Text,out n)){output.Text="Epoch 必须为整数";return;}
     var request=new Dictionary<string,object>{{"action",action},{"root",root},{"epochs",n},{"job_id",job.Text},{"model_id",String.IsNullOrWhiteSpace(model.Text)?null:model.Text},{"version_id",String.IsNullOrWhiteSpace(version.Text)?null:version.Text}};
     buttons.IsEnabled=false;output.Text="正在执行…";
     try{string result=await Task.Run(()=>NvidiaBridge.Call(request));output.Text=result;
      if(action=="train"||action=="validate"){var d=Codec.Parse<Dictionary<string,object>>(result);job.Text=Convert.ToString(d["job_id"]);version.Text=Convert.ToString(d["version_id"]);}
     }catch(Exception ex){output.Text=ex.Message;}finally{buttons.IsEnabled=true;}
    };
   };
   add("GPU 状态","gpu");add("开始训练","train");add("模型验证","validate");add("任务队列与指标","runs");add("任务状态","job");add("取消任务","cancel");add("模型 Registry","registry");add("单帧离线推理","infer");
   new Window{Owner=this,Title="NVIDIA 训练与模型",Width=820,Height=760,Content=new ScrollViewer{Content=panel}}.Show();
  }
 }
}
