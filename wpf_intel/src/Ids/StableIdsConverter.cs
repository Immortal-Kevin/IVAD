// SPDX-License-Identifier: Apache-2.0
using System;
using System.Collections;
using System.Collections.Generic;
using System.Web.Script.Serialization;
namespace Ivad.Ids {
 // .NET Framework reflection property caches can reorder properties after a named lookup.
 // Preserve the established IDS 1.0 declaration order explicitly, including nested entities.
 public sealed class StableIdsConverter:JavaScriptConverter {
  public override IEnumerable<Type> SupportedTypes {get{return new[]{typeof(Entity),typeof(Asset),typeof(Document),typeof(Envelope)};}}
  public override IDictionary<string,object> Serialize(object value,JavaScriptSerializer serializer){
   var d=new Dictionary<string,object>();var e=value as Entity;if(e!=null){d.Add("id",e.id);d.Add("kind",e.kind);d.Add("revision",e.revision);d.Add("data",e.data);return d;}
   var a=value as Asset;if(a!=null){d.Add("path",a.path);d.Add("sha256",a.sha256);d.Add("bytes",a.bytes);return d;}
   var doc=value as Document;if(doc!=null){d.Add("schema",doc.schema);d.Add("project_id",doc.project_id);d.Add("sequence",doc.sequence);d.Add("entities",doc.entities);d.Add("assets",doc.assets);return d;}
   var env=(Envelope)value;d.Add("format",env.format);d.Add("mode",env.mode);d.Add("base_sha256",env.base_sha256);d.Add("target_sha256",env.target_sha256);d.Add("included_assets",env.included_assets);return d;
  }
  static object Get(IDictionary<string,object> d,string key){object v;return d.TryGetValue(key,out v)?v:null;}
  public override object Deserialize(IDictionary<string,object> d,Type type,JavaScriptSerializer s){
   if(type==typeof(Entity))return new Entity{id=(string)Get(d,"id"),kind=(string)Get(d,"kind"),revision=Convert.ToInt32(Get(d,"revision")),data=Get(d,"data") as Dictionary<string,object>};
   if(type==typeof(Asset))return new Asset{path=(string)Get(d,"path"),sha256=(string)Get(d,"sha256"),bytes=Convert.ToInt64(Get(d,"bytes"))};
   if(type==typeof(Document)){var doc=new Document{schema=(string)Get(d,"schema"),project_id=(string)Get(d,"project_id"),sequence=Convert.ToInt64(Get(d,"sequence"))};var es=Get(d,"entities") as IEnumerable;var assets=Get(d,"assets") as IEnumerable;if(es==null||assets==null)throw new System.IO.InvalidDataException("IDS实体/资产集合缺失");foreach(var item in es)doc.entities.Add(s.ConvertToType<Entity>(item));foreach(var item in assets)doc.assets.Add(s.ConvertToType<Asset>(item));return doc;}
   var env=new Envelope{format=(string)Get(d,"format"),mode=(string)Get(d,"mode"),base_sha256=(string)Get(d,"base_sha256"),target_sha256=(string)Get(d,"target_sha256")};var paths=Get(d,"included_assets") as IEnumerable;if(paths!=null){env.included_assets=new List<string>();foreach(var p in paths)env.included_assets.Add((string)p);}return env;
  }
 }
}
