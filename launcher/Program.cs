using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.Versioning;
using System.Text;
using System.Windows.Forms;

[assembly: TargetFramework(".NETFramework,Version=v4.8")]

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length != 0)
        {
            try
            {
                Console.SetOut(new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)) { AutoFlush = true });
                Console.SetError(new StreamWriter(Console.OpenStandardError(), new UTF8Encoding(false)) { AutoFlush = true });
                using (var process = Process.Start(Worker.StartInfo(args)))
                {
                    process.OutputDataReceived += delegate(object sender, DataReceivedEventArgs line) {
                        if (line.Data != null) Console.Out.WriteLine(line.Data);
                    };
                    process.ErrorDataReceived += delegate(object sender, DataReceivedEventArgs line) {
                        if (line.Data != null) Console.Error.WriteLine(line.Data);
                    };
                    process.BeginOutputReadLine();
                    process.BeginErrorReadLine();
                    process.WaitForExit();
                    return process.ExitCode;
                }
            }
            catch (Exception error)
            {
                Console.Error.WriteLine(error.Message);
                return 1;
            }
        }

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Views.Initialize(Screen.FromPoint(Cursor.Position));
        Application.Run(new TrainerForm());
        return 0;
    }
}

internal static class Worker
{
    internal static ProcessStartInfo StartInfo(string[] args)
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
        string device = "cpu";
        int position = Array.IndexOf(args, "--device");
        if (position >= 0 && position + 1 < args.Length)
            device = args[position + 1];
        string runtime = device == "xpu" || device == "cuda" ? "runtime-" + device : "runtime";
        string executable = Path.Combine(root, runtime, "python.exe");
        if (!File.Exists(executable))
            throw new FileNotFoundException("缺少便携运行时：" + runtime +
                "。请完整解压 ZIP，或安装对应的 GPU 运行时。");

        var command = new List<string> {
            "-B", "-u", "-c",
            "import os,runpy,sys; sys.path.insert(0,os.path.dirname(sys.argv[1])); " +
            "sys.argv.pop(0); runpy.run_path(sys.argv[0],run_name='__main__')",
            Path.Combine(root, "trainer", "worker.py")
        };
        command.AddRange(args);
        var info = new ProcessStartInfo(executable, String.Join(" ", command.ConvertAll(Quote).ToArray()));
        info.UseShellExecute = false;
        info.CreateNoWindow = true;
        info.WorkingDirectory = root;
        info.EnvironmentVariables["PYTHONUTF8"] = "1";
        info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        info.EnvironmentVariables.Remove("PYTHONPATH");
        info.EnvironmentVariables.Remove("PYTHONHOME");
        info.RedirectStandardOutput = true;
        info.RedirectStandardError = true;
        info.StandardOutputEncoding = Encoding.UTF8;
        info.StandardErrorEncoding = Encoding.UTF8;
        return info;
    }

    private static string Quote(string value)
    {
        var result = new StringBuilder("\"");
        int slashes = 0;
        foreach (char ch in value)
        {
            if (ch == '\\')
            {
                slashes++;
                continue;
            }
            result.Append('\\', ch == '"' ? 2 * slashes + 1 : slashes);
            result.Append(ch);
            slashes = 0;
        }
        result.Append('\\', 2 * slashes);
        return result.Append('"').ToString();
    }
}
