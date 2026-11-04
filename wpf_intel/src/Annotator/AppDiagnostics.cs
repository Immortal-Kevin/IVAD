// SPDX-License-Identifier: Apache-2.0
using System;
using System.IO;
namespace Ivad.Annotator {
 internal static class AppDiagnostics {
  internal static void Write(string name,string text){
   foreach(string dir in new[]{Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"logs"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"IVAD Annotator","Logs")}){
    try{Directory.CreateDirectory(dir);File.AppendAllText(Path.Combine(dir,name),DateTime.UtcNow.ToString("o")+" "+text+Environment.NewLine);return;}catch(IOException){}catch(UnauthorizedAccessException){}
   }
  }
 }
}
