// SPDX-License-Identifier: Apache-2.0
// Self-authored fixture generator. Uses Windows OS encoder ABI, no bundled codec.
using System;
using System.IO;
using System.Runtime.InteropServices;
static class MediaFixtures {
 [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFStartup(int version,int flags);
 [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFShutdown();
 [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFCreateMediaType(out IntPtr value);
 [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFCreateMemoryBuffer(int size,out IntPtr value);
 [DllImport("mfplat.dll",ExactSpelling=true)] static extern int MFCreateSample(out IntPtr value);
 [DllImport("mfreadwrite.dll",CharSet=CharSet.Unicode,ExactSpelling=true)] static extern int MFCreateSinkWriterFromURL(string url,IntPtr stream,IntPtr attrs,out IntPtr writer);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Set32(IntPtr p,ref Guid key,int value);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Set64(IntPtr p,ref Guid key,long value);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int SetGuid(IntPtr p,ref Guid key,ref Guid value);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int AddStream(IntPtr p,IntPtr type,out int stream);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int InputType(IntPtr p,int stream,IntPtr type,IntPtr attrs);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Simple(IntPtr p);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Lock(IntPtr p,out IntPtr data,out int max,out int length);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int IntValue(IntPtr p,int value);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int LongValue(IntPtr p,long value);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Pointer(IntPtr p,IntPtr value);
 [UnmanagedFunctionPointer(CallingConvention.StdCall)] delegate int Sample(IntPtr p,int stream,IntPtr sample);
 static T Fn<T>(IntPtr p,int slot) where T:class{return Marshal.GetDelegateForFunctionPointer(Marshal.ReadIntPtr(Marshal.ReadIntPtr(p),slot*IntPtr.Size),typeof(T)) as T;}
 static void OK(int h){if(h<0)Marshal.ThrowExceptionForHR(h);}
 static void Put32(IntPtr p,string key,int value){var g=new Guid(key);OK(Fn<Set32>(p,21)(p,ref g,value));}
 static void Put64(IntPtr p,string key,long value){var g=new Guid(key);OK(Fn<Set64>(p,22)(p,ref g,value));}
 static void PutGuid(IntPtr p,string key,string value){var k=new Guid(key);var v=new Guid(value);OK(Fn<SetGuid>(p,24)(p,ref k,ref v));}
 static void Format(IntPtr p,string subtype,int fps,int width,int height){
  PutGuid(p,"48eba18e-f8c9-4687-bf11-0a74c9f96a8f","73646976-0000-0010-8000-00aa00389b71");PutGuid(p,"f7e34c9a-42e8-4714-b74b-cb29d72c35e5",subtype);
  Put64(p,"1652c33d-d6b2-4012-b834-72030849a37d",((long)width<<32)|(uint)height);Put64(p,"c459a2e8-3d2c-4e44-b132-fee5156c7bb0",((long)fps<<32)|1);
  Put64(p,"c6376a1e-8d0a-4027-be45-6d9a0ad39bb6",((long)1<<32)|1);Put32(p,"e2724bb8-e676-4806-b4b2-a8d6efb44ccd",2);
 }
 public static void Encode(string path,long[] timestamps,long finalDuration,bool hevc){Encode(path,timestamps,finalDuration,hevc,64,48);}
 public static void Encode(string path,long[] timestamps,long finalDuration,bool hevc,int width,int height){
  OK(MFStartup(0x20070,0));IntPtr writer=IntPtr.Zero,output=IntPtr.Zero,input=IntPtr.Zero;
  try{OK(MFCreateSinkWriterFromURL(path,IntPtr.Zero,IntPtr.Zero,out writer));OK(MFCreateMediaType(out output));Format(output,hevc?"43564548-0000-0010-8000-00aa00389b71":"34363248-0000-0010-8000-00aa00389b71",4,width,height);Put32(output,"20332624-fb0d-4d9e-bd0d-cbf6786c102e",width>64?2000000:200000);if(!hevc)Put32(output,"ad76a80b-2d5c-4e0b-b375-64e520137036",66);
   int stream;OK(Fn<AddStream>(writer,3)(writer,output,out stream));OK(MFCreateMediaType(out input));Format(input,"3231564e-0000-0010-8000-00aa00389b71",4,width,height);OK(Fn<InputType>(writer,4)(writer,stream,input,IntPtr.Zero));OK(Fn<Simple>(writer,5)(writer));
   byte[] pixels=new byte[width*height*3/2];for(int i=0;i<pixels.Length;i++)pixels[i]=(byte)(i<width*height?16+i%width%200:128);
   for(int f=0;f<timestamps.Length;f++){
    IntPtr buffer=IntPtr.Zero,sample=IntPtr.Zero;
    try{OK(MFCreateMemoryBuffer(pixels.Length,out buffer));IntPtr data;int max,len;OK(Fn<Lock>(buffer,3)(buffer,out data,out max,out len));try{for(int y=0;y<32;y++)for(int x=0;x<32;x++)pixels[y*width+x]=(byte)(16+(f*23+x)%200);Marshal.Copy(pixels,0,data,pixels.Length);}finally{OK(Fn<Simple>(buffer,4)(buffer));}
     OK(Fn<IntValue>(buffer,6)(buffer,pixels.Length));OK(MFCreateSample(out sample));OK(Fn<Pointer>(sample,42)(sample,buffer));OK(Fn<LongValue>(sample,36)(sample,timestamps[f]));OK(Fn<LongValue>(sample,38)(sample,f+1<timestamps.Length?timestamps[f+1]-timestamps[f]:finalDuration));OK(Fn<Sample>(writer,6)(writer,stream,sample));
    }finally{if(sample!=IntPtr.Zero)Marshal.Release(sample);if(buffer!=IntPtr.Zero)Marshal.Release(buffer);}
   }
   OK(Fn<Simple>(writer,11)(writer));
  }finally{foreach(var p in new[]{input,output,writer})if(p!=IntPtr.Zero)Marshal.Release(p);MFShutdown();}
 }
}
