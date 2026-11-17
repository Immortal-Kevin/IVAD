// SPDX-License-Identifier: Apache-2.0
// Minimal, self-authored test-only muxing; not a production media parser.
using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Collections.Generic;
static class FixtureContainers {
 static uint U(byte[] b,int p){return ((uint)b[p]<<24)|((uint)b[p+1]<<16)|((uint)b[p+2]<<8)|b[p+3];}
 static int Box(byte[] b,string path){int start=0,end=b.Length,found=-1;foreach(string name in path.Split('/')){found=-1;for(int p=start;p+8<=end;){int n=checked((int)U(b,p));if(n<8||p+n>end)throw new InvalidDataException("fixture atom size");if(Encoding.ASCII.GetString(b,p+4,4)==name){found=p;start=p+8;end=p+n;break;}p+=n;}if(found<0)throw new InvalidDataException("fixture atom missing "+name);}return found;}
 public static void Mov(string mp4,string mov){byte[] b=File.ReadAllBytes(mp4);int p=Box(b,"ftyp"),size=(int)U(b,p);if(size<20)throw new InvalidDataException("ftyp");var qt=Encoding.ASCII.GetBytes("qt  ");Array.Copy(qt,0,b,p+8,4);for(int i=p+16;i<p+size;i+=4)Array.Copy(qt,0,b,i,4);File.WriteAllBytes(mov,b);}
 static byte[] Cat(params byte[][] pieces){using(var ms=new MemoryStream()){foreach(var p in pieces)ms.Write(p,0,p.Length);return ms.ToArray();}}
 static byte[] BE(ulong number){var bytes=new List<byte>();do{bytes.Insert(0,(byte)(number&255));number>>=8;}while(number>0);return bytes.ToArray();}
 static byte[] Size(int length){int n=1;while((ulong)length>=((1UL<<(7*n))-1))n++;byte[] b=new byte[n];ulong v=(ulong)length|(1UL<<(7*n));for(int i=n-1;i>=0;i--){b[i]=(byte)(v&255);v>>=8;}return b;}
 static byte[] E(uint id,byte[] data){return Cat(BE(id),Size(data.Length),data);}
 static byte[] Number(uint id,ulong value){return E(id,BE(value));}
 static byte[] Text(uint id,string value){return E(id,Encoding.UTF8.GetBytes(value));}
 static byte[] Float(uint id,double value){byte[] b=BitConverter.GetBytes(value);if(BitConverter.IsLittleEndian)Array.Reverse(b);return E(id,b);}
 public static void Mkv(string mp4,string mkv){
  byte[] b=File.ReadAllBytes(mp4);const string table="moov/trak/mdia/minf/stbl/";int sz=Box(b,table+"stsz"),count=(int)U(b,sz+16);uint fixedSize=U(b,sz+12);int[] sizes=Enumerable.Range(0,count).Select(i=>fixedSize!=0?(int)fixedSize:(int)U(b,sz+20+i*4)).ToArray();
  int co=Box(b,table+"stco"),sc=Box(b,table+"stsc"),chunks=(int)U(b,co+12),entries=(int)U(b,sc+12),idx=0;var samples=new List<byte[]>();
  for(int chunk=1;chunk<=chunks;chunk++){int map=0;for(int i=0;i<entries;i++)if(U(b,sc+16+i*12)<=chunk)map=i;int n=(int)U(b,sc+20+map*12),offset=(int)U(b,co+12+chunk*4);for(int j=0;j<n;j++){samples.Add(b.Skip(offset).Take(sizes[idx]).ToArray());offset+=sizes[idx++];}}
  if(idx!=count)throw new InvalidDataException("fixture chunk mapping");
  int sd=Box(b,table+"stsd"),end=sd+(int)U(b,sd),avcc=-1;for(int p=sd+8;p+8<end;p++)if(Encoding.ASCII.GetString(b,p+4,4)=="avcC"){avcc=p;break;}if(avcc<0)throw new InvalidDataException("avcC missing");byte[] codec=b.Skip(avcc+8).Take((int)U(b,avcc)-8).ToArray();
  int mdhd=Box(b,"moov/trak/mdia/mdhd");if(b[mdhd+8]!=0)throw new InvalidDataException("fixture time version");uint scale=U(b,mdhd+20);int stts=Box(b,table+"stts");var times=new List<long>();long now=0;for(int i=0;i<U(b,stts+12);i++){uint n=U(b,stts+16+i*8),duration=U(b,stts+20+i*8);for(int j=0;j<n;j++){times.Add(now*1000/scale);now+=duration;}}
  var keys=new HashSet<int>();try{int ss=Box(b,table+"stss");for(int i=0;i<U(b,ss+12);i++)keys.Add((int)U(b,ss+16+i*4)-1);}catch(InvalidDataException){for(int i=0;i<count;i++)keys.Add(i);}
  byte[] header=E(0x1A45DFA3,Cat(Number(0x4286,1),Number(0x42F7,1),Number(0x42F2,4),Number(0x42F3,8),Text(0x4282,"matroska"),Number(0x4287,4),Number(0x4285,2)));
  byte[] info=E(0x1549A966,Cat(Number(0x2AD7B1,1000000),Float(0x4489,now*1000.0/scale),Text(0x4D80,"IVAD self-authored test mux"),Text(0x5741,"IVAD tests")));
  byte[] tracks=E(0x1654AE6B,E(0xAE,Cat(Number(0xD7,1),Number(0x73C5,1),Number(0x83,1),Number(0x9C,0),Text(0x86,"V_MPEG4/ISO/AVC"),E(0x63A2,codec),E(0xE0,Cat(Number(0xB0,64),Number(0xBA,48))))));
  var parts=new List<byte[]>{info,tracks};for(int i=0;i<count;i++)parts.Add(E(0x1F43B675,Cat(Number(0xE7,(ulong)times[i]),E(0xA3,Cat(new byte[]{0x81,0,0,(byte)(keys.Contains(i)?0x80:0)},samples[i])))));
  File.WriteAllBytes(mkv,Cat(header,E(0x18538067,Cat(parts.ToArray()))));
 }
}
