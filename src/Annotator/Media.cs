// SPDX-License-Identifier: Apache-2.0
// Windows Media Foundation ABI declarations; no third-party decoder binary bundled.
using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using Ivad.Ids;

namespace Ivad.Annotator {
 public static class Media {
  [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFStartup(int version,int flags);
  [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFShutdown();
  [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFCreateAttributes(out IntPtr attributes,int size);
  [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFCreateMediaType(out IntPtr type);
  [DllImport("mfreadwrite.dll",CharSet=CharSet.Unicode,ExactSpelling=true)] static extern int MFCreateSourceReaderFromURL(string url,IntPtr attributes,out IntPtr reader);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Set32(IntPtr p,ref Guid key,int value);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetGuid(IntPtr p,ref Guid key,ref Guid value);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Get64(IntPtr p,ref Guid key,out long value);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Get32(IntPtr p,ref Guid key,out int value);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int GetGuid(IntPtr p,ref Guid key,out Guid value);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int GetBlob(IntPtr p,ref Guid key,[Out] byte[] bytes,int length,out int actual);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SelectStream(IntPtr p,int stream,int selected);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetType(IntPtr p,int stream,IntPtr reserved,IntPtr type);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int GetMediaType(IntPtr p,int stream,out IntPtr type);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Read(IntPtr p,int stream,int control,out int actual,out int flags,out long time,out IntPtr sample);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Buffer(IntPtr p,out IntPtr buffer);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int LockBuffer(IntPtr p,out IntPtr data,out int max,out int length);
  [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int UnlockBuffer(IntPtr p);
  static T Fn<T>(IntPtr p,int slot) where T:class{return Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(Marshal.ReadIntPtr(p),slot*IntPtr.Size),typeof(T)) as T;}
  static void OK(int h){if(h<0)Marshal.ThrowExceptionForHR(h);}
  static Guid G(string s){return new Guid(s);}
  static void Put32(IntPtr p,string key,int v){var g=G(key);OK(Fn<Set32>(p,21)(p,ref g,v));}
  static void PutGuid(IntPtr p,string key,string value){var k=G(key);var v=G(value);OK(Fn<SetGuid>(p,24)(p,ref k,ref v));}
  const int VideoStream=unchecked((int)0xFFFFFFFC);
  sealed class Layout {public int Width,Height,CodedWidth,CodedHeight,X,Y,Stride;}
  static Layout ReadLayout(IntPtr type){
   var key=G("1652c33d-d6b2-4012-b834-72030849a37d");long size;OK(Fn<Get64>(type,8)(type,ref key,out size));var l=new Layout{Width=(int)(size>>32),Height=(int)(size&0xFFFFFFFF)};l.CodedWidth=l.Width;l.CodedHeight=l.Height;l.Stride=l.CodedWidth*4;
   if(l.Width<=0||l.Height<=0||l.Width>16384||l.Height>16384)throw new InvalidDataException("不支持的图像尺寸");
   key=G("644b4e48-1e02-4516-b0eb-c01ca9d49ac6");int stride;if(Fn<Get32>(type,7)(type,ref key,out stride)>=0)l.Stride=stride;
   foreach(string aperture in new[]{"d7388766-18fe-48c6-a177-ee894867c8c4","66758743-7e5f-400d-980a-aa8596c85696"}){
    key=G(aperture);byte[] bytes=new byte[16];int actual;if(Fn<GetBlob>(type,15)(type,ref key,bytes,16,out actual)<0)continue;
    if(actual!=16||BitConverter.ToUInt16(bytes,0)!=0||BitConverter.ToUInt16(bytes,4)!=0)throw new InvalidDataException("不支持小数偏移显示区域");
    l.X=BitConverter.ToInt16(bytes,2);l.Y=BitConverter.ToInt16(bytes,6);l.Width=BitConverter.ToInt32(bytes,8);l.Height=BitConverter.ToInt32(bytes,12);break;
   }
   if(l.X<0||l.Y<0||l.Width<=0||l.Height<=0||l.X+l.Width>l.CodedWidth||l.Y+l.Height>l.CodedHeight||Math.Abs((long)l.Stride)<l.CodedWidth*4L)throw new InvalidDataException("解码显示区域或步幅无效");return l;
  }
  public static int Extract(string project,string videoId,double seconds,int maximum){return Extract(project,videoId,seconds,maximum,0,Double.MaxValue,null);}
  public static int Extract(string project,string videoId,double seconds,int maximum,double from,double until,string staging){
   return ExtractCore(project,videoId,seconds,maximum,from,until,staging,false,-1);
  }
  public static int CountFrames(string project,string videoId,double seconds,int maximum,double from,double until){return ExtractCore(project,videoId,seconds,maximum,from,until,null,true,-1);}
  public static int ExtractWithProgress(string project,string videoId,double seconds,int maximum,double from,double until,string staging){
   Work.Report("IVAD_PROGRESS|统计实际抽帧总数|0|-1");int total=CountFrames(project,videoId,seconds,maximum,from,until);
   Work.Report("IVAD_PROGRESS|开始抽帧|0|"+total);
   int count=ExtractCore(project,videoId,seconds,maximum,from,until,staging,false,total);
   Work.Report("IVAD_PROGRESS|抽帧完成，已保存|"+count+"|"+total);return count;
  }
  static int ExtractCore(string project,string videoId,double seconds,int maximum,double from,double until,string staging,bool planOnly,int total){
   if(seconds<0.000001||Double.IsNaN(seconds)||Double.IsInfinity(seconds)||maximum<1||maximum>5000||from<0||Double.IsNaN(from)||Double.IsInfinity(from)||until<=from||Double.IsNaN(until)||Double.IsInfinity(until))throw new ArgumentException("抽帧范围/间隔/上限无效");
   var store=new Store(project);var video=store.Find(videoId);if(video.kind!="Video")throw new ArgumentException("非视频实体");
   string source=Rules.SafePath(project,video.Text("asset_path"));
   OK(MFStartup(0x20070,0));IntPtr attrs=IntPtr.Zero,reader=IntPtr.Zero,type=IntPtr.Zero,current=IntPtr.Zero;
   string stage=staging??Path.Combine(project,".frames-"+Guid.NewGuid().ToString("N"));if(!planOnly)Directory.CreateDirectory(stage);
   var pending=new List<Tuple<string,Dictionary<string,object>>>();
   var seen=new HashSet<long>(store.Data.entities.Where(e=>e.kind=="Frame"&&e.Text("video_id")==videoId).Select(e=>(long)e.Number("source_timestamp_100ns")));
   int count=0;
   try {
    OK(MFCreateAttributes(out attrs,2));Put32(attrs,"fb394f3d-ccf1-42ee-bbb3-f9b845d5681d",1);
    OK(MFCreateSourceReaderFromURL(source,attrs,out reader));
    OK(Fn<SelectStream>(reader,4)(reader,unchecked((int)0xFFFFFFFE),0));OK(Fn<SelectStream>(reader,4)(reader,VideoStream,1));
    OK(MFCreateMediaType(out type));PutGuid(type,"48eba18e-f8c9-4687-bf11-0a74c9f96a8f","73646976-0000-0010-8000-00aa00389b71");PutGuid(type,"f7e34c9a-42e8-4714-b74b-cb29d72c35e5","00000016-0000-0010-8000-00aa00389b71");
    OK(Fn<SetType>(reader,7)(reader,VideoStream,IntPtr.Zero,type));OK(Fn<GetMediaType>(reader,6)(reader,VideoStream,out current));
    var layout=ReadLayout(current);int width=layout.Width,height=layout.Height;
    double next=from*10000000;long index=0;var timer=System.Diagnostics.Stopwatch.StartNew();
    while(count<maximum){
     Work.Check();
     if(timer.Elapsed.TotalMinutes>5)throw new TimeoutException("抽帧达到5分钟上限；请缩小任务");
     int actual,flags;long stamp;IntPtr sample;OK(Fn<Read>(reader,9)(reader,VideoStream,0,out actual,out flags,out stamp,out sample));
     try{
      if((flags&2)!=0)break;
      if((flags&0x30)!=0){
       // HEVC may signal output renegotiation before its first decoded sample.
       // Accept compatible RGB32/stride updates, but never reinterpret changed dimensions.
       Marshal.Release(current);current=IntPtr.Zero;OK(Fn<GetMediaType>(reader,6)(reader,VideoStream,out current));
       var updated=ReadLayout(current);var subtypeKey=G("f7e34c9a-42e8-4714-b74b-cb29d72c35e5");Guid subtype;OK(Fn<GetGuid>(current,10)(current,ref subtypeKey,out subtype));
       if(updated.Width!=width||updated.Height!=height||subtype!=G("00000016-0000-0010-8000-00aa00389b71"))throw new InvalidDataException("视频可见尺寸或像素格式变化，停止抽帧："+width+"x"+height+" -> "+updated.Width+"x"+updated.Height+"; subtype="+subtype+"; decoded="+index);
       layout=updated;
      }
      if(sample==IntPtr.Zero)continue;index++;
      if(stamp/10000000.0>=until)break;
      if(index%100==0)Work.Report("解码PTS="+(stamp/10000000.0).ToString("F3")+"s；新增帧="+count);
      if(stamp<next||stamp<0)continue;
      next=(from+(Math.Floor((stamp/10000000.0-from)/seconds+1e-9)+1)*seconds)*10000000;
      if(!seen.Add(stamp))continue;
      if(planOnly){count++;Work.Report("IVAD_PROGRESS|统计实际抽帧总数|"+count+"|-1");continue;}
      IntPtr buffer;OK(Fn<Buffer>(sample,41)(sample,out buffer));
      try {IntPtr data;int max,length;OK(Fn<LockBuffer>(buffer,3)(buffer,out data,out max,out length));
       try {
        if(Math.Abs((long)layout.Stride)*layout.CodedHeight>length)throw new InvalidDataException("解码帧缓冲长度错误");
        byte[] pixels=new byte[checked(width*height*4)];
        for(int y=0;y<height;y++)Marshal.Copy(IntPtr.Add(data,(layout.Stride<0?layout.CodedHeight-1-layout.Y-y:layout.Y+y)*Math.Abs(layout.Stride)+layout.X*4),pixels,y*width*4,width*4);
        var bitmap=BitmapSource.Create(width,height,96,96,PixelFormats.Bgr32,null,pixels,width*4);
        string png=Path.Combine(stage,count+".png");var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using(var output=File.Create(png))encoder.Save(output);
        pending.Add(Tuple.Create(png,new Dictionary<string,object>{{"video_id",videoId},{"width",width},{"height",height},{"pts_us",stamp/10},{"source_timestamp_100ns",stamp},{"time_source","media_foundation_sample"},{"decode_index",index-1},{"state","unannotated"},{"sampling_interval_seconds",seconds},{"sampling_start_seconds",from},{"sampling_end_seconds",until}}));
        count++;Work.Report(total<0?"抽帧 "+count+"；上限="+maximum+"；PTS="+(stamp/10000000.0).ToString("F3")+"s":"IVAD_PROGRESS|正在抽帧|"+count+"|"+total);
       }finally{OK(Fn<UnlockBuffer>(buffer,4)(buffer));}
      }finally{Marshal.Release(buffer);}
     }finally{if(sample!=IntPtr.Zero)Marshal.Release(sample);}
    }
    if(index==0&&!store.Data.entities.Any(e=>e.kind=="Frame"&&e.Text("video_id")==videoId))throw new InvalidDataException("视频没有可解码帧，可能缺少Windows解码器");
    if(planOnly)return count;
    if(total>=0&&count!=total)throw new IOException("抽帧统计发生变化，未提交本次图片；请重试");
    if(total>=0)Work.Report("IVAD_PROGRESS|正在校验并保存图片|"+count+"|"+total);
    foreach(var item in pending){Work.Check();var asset=store.CopyAsset(item.Item1);item.Item2["asset_path"]=asset.path;var added=store.Add("Frame",item.Item2);store.Revise(added,"frame-extractor");}
    if(count>0)store.Save();return count;
   }catch{store.AbortAssets();throw;}finally{
    foreach(var p in new[]{current,type,reader,attrs})if(p!=IntPtr.Zero)Marshal.Release(p);
    MFShutdown();if(!planOnly&&Directory.Exists(stage))Directory.Delete(stage,true);
   }
  }
 }
}
