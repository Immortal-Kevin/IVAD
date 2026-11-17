// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
using System.Text.RegularExpressions;
namespace Ivad.Annotator {
 internal static class AppDiagnostics {
  internal static string Redact(string text){
   text=Regex.Replace(text,@"(?i)([""']?(?:password|passwd|token|api[_-]?key|secret)[""']?\s*[:=]\s*)(?:""[^""\r\n]*""|'[^'\r\n]*'|[^\s,;]+)","$1<redacted>");
   text=Regex.Replace(text,@"(?i)Bearer\s+[A-Za-z0-9._~+/-]+","Bearer <redacted>");
   text=Regex.Replace(text,@"(?i)(?:[A-Z]:[\\/]|\\\\)[^\r\n""']+","<private-path>");
   return Regex.Replace(text,@"(?i)(?:rtsp|https?)://[^\s]+","<private-url>");
  }
  internal static void Write(string name,string text){
   text=Redact(text);
   foreach(string dir in new[]{Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"logs"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"IVAD Annotator","Logs")}){
    try{Directory.CreateDirectory(dir);File.AppendAllText(Path.Combine(dir,name),DateTime.UtcNow.ToString("o")+" "+text+Environment.NewLine);return;}catch(IOException){}catch(UnauthorizedAccessException){}
   }
  }
 }
}
