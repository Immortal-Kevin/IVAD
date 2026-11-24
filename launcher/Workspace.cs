using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;
using System.Windows.Forms;

public sealed class ProjectSettings
{
    public string Ids { get; set; }
    public string Model { get; set; }
    public string Device { get; set; }
    public decimal Size { get; set; }
    public decimal Batch { get; set; }
    public decimal Epochs { get; set; }
    public string Output { get; set; }
    public string InitialWeights { get; set; }
    public List<string> SourceVideos { get; set; }
    public List<string> KnownSourceVideos { get; set; }
    public Dictionary<string, string> SourcePurposes { get; set; }
    public string DetectionSplit { get; set; }
    public bool AllowDiagnosticReuse { get; set; }
    public bool? AutoEarlyStop { get; set; }
    public string AnomalyRoi { get; set; }
    public Dictionary<string, string> Artifacts { get; set; }
    public string Video { get; set; }
    public string VideoWeights { get; set; }
    public string VideoModel { get; set; }
    public string VideoDevice { get; set; }
    public decimal VideoSize { get; set; }
    public decimal Confidence { get; set; }
    public decimal SampleRate { get; set; }
    public bool LocalVideoWeights { get; set; }
}

public sealed class Preferences
{
    public string Current { get; set; }
    public Dictionary<string, ProjectSettings> Projects { get; set; }
}

internal sealed class Workspace
{
    internal const string Preset = "刮板机机头";
    internal const string Custom = "自定义项目";
    internal static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
    private readonly string file;
    internal readonly Preferences Data;
    internal string LoadError { get; private set; }

    internal Workspace()
    {
        string configured = Environment.GetEnvironmentVariable("IVAD_TRAINER_CONFIG");
        file = String.IsNullOrWhiteSpace(configured) ?
            Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "IVAD Open Trainer", "projects.json") : Path.GetFullPath(configured);
        try
        {
            if (File.Exists(file)) Data = Json.Deserialize<Preferences>(File.ReadAllText(file));
        }
        catch (Exception error) { LoadError = error.Message; }
        if (Data == null) Data = new Preferences();
        if (Data.Projects == null) Data.Projects = new Dictionary<string, ProjectSettings>();
        foreach (string name in new[] { Preset, Custom })
            if (!Data.Projects.ContainsKey(name) || Data.Projects[name] == null)
                Data.Projects[name] = new ProjectSettings();
        if (Data.Current != Preset && Data.Current != Custom) Data.Current = Preset;
    }

    internal void Save()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(file));
        string temp = file + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            File.WriteAllText(temp, Json.Serialize(Data), new UTF8Encoding(false));
            if (File.Exists(file)) File.Replace(temp, file, null);
            else File.Move(temp, file);
        }
        finally { if (File.Exists(temp)) File.Delete(temp); }
    }

    internal static string Value(Dictionary<string, object> obj, string key)
    {
        object value;
        return obj != null && obj.TryGetValue(key, out value) ? Convert.ToString(value, CultureInfo.InvariantCulture) : "";
    }

    internal static Dictionary<string, object> Object(Dictionary<string, object> obj, string key)
    {
        object value;
        return obj != null && obj.TryGetValue(key, out value) ? value as Dictionary<string, object> : null;
    }

    internal static double Number(Dictionary<string, object> obj, string key)
    {
        double number;
        return Double.TryParse(Value(obj, key), NumberStyles.Float, CultureInfo.InvariantCulture, out number) ? number : 0;
    }
}

internal sealed class WorkerJob
{
    private readonly Control owner;
    private Process process;
    private bool cancelled;
    private string stopSignal;
    private Timer stopTimeout;
    internal bool Active { get { return process != null; } }

    internal WorkerJob(Control owner) { this.owner = owner; }

    internal void Start(string[] args, Action<string> log, Action<Dictionary<string, object>> message,
                        Action<int, bool> complete, string gracefulStop = null)
    {
        if (Active) throw new InvalidOperationException("当前任务仍在运行");
        var child = new Process { StartInfo = Worker.StartInfo(args) };
        cancelled = false;
        stopSignal = gracefulStop;
        child.OutputDataReceived += delegate(object sender, DataReceivedEventArgs line) {
            if (line.Data == null) return;
            Dispatch(delegate {
                if (!line.Data.StartsWith("EVENT ", StringComparison.Ordinal))
                {
                    log(line.Data);
                    return;
                }
                try { message(Workspace.Json.Deserialize<Dictionary<string, object>>(line.Data.Substring(6))); }
                catch (Exception error) { log("无法读取任务消息：" + error.Message); }
            });
        };
        child.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs line) {
            if (line.Data != null) Dispatch(delegate { log(line.Data); });
        };
        child.Exited += delegate {
            child.WaitForExit();
            int status = child.ExitCode;
            Dispatch(delegate {
                if (process != child) return;
                process = null;
                if (stopTimeout != null) { stopTimeout.Dispose(); stopTimeout = null; }
                child.Dispose();
                complete(status, cancelled);
            });
        };
        process = child;
        try
        {
            child.Start();
            child.BeginOutputReadLine();
            child.BeginErrorReadLine();
            child.EnableRaisingEvents = true;
        }
        catch
        {
            process = null;
            try { if (!child.HasExited) child.Kill(); }
            catch (InvalidOperationException) { }
            child.Dispose();
            throw;
        }
    }

    internal void Stop(bool force = false)
    {
        if (process == null || process.HasExited) return;
        cancelled = true;
        if (!force && stopSignal != null)
        {
            try
            {
                File.WriteAllText(stopSignal, "stop");
                if (stopTimeout != null) return;
                stopTimeout = new Timer { Interval = 10000 };
                stopTimeout.Tick += delegate {
                    stopTimeout.Stop();
                    if (process != null && !process.HasExited) process.Kill();
                };
                stopTimeout.Start();
                return;
            }
            catch (IOException) { }
            catch (UnauthorizedAccessException) { }
        }
        process.Kill();
    }

    private void Dispatch(Action callback)
    {
        if (!owner.IsHandleCreated || owner.IsDisposed) return;
        try { owner.BeginInvoke(callback); }
        catch (InvalidOperationException) { }
    }
}
