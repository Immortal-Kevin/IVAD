using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text;
using System.Windows.Forms;

internal static class Program
{
    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Length != 0)
        {
            try
            {
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
            throw new FileNotFoundException("Missing portable runtime: " + runtime +
                ". Extract the complete ZIP or add the matching GPU runtime.");

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

internal sealed class TrainerForm : Form
{
    private readonly TextBox source = new TextBox();
    private readonly TextBox output = new TextBox();
    private readonly TextBox weights = new TextBox();
    private readonly ComboBox model = new ComboBox();
    private readonly ComboBox device = new ComboBox();
    private readonly NumericUpDown size = Number(384, 64, 2048, 32);
    private readonly NumericUpDown batch = Number(1, 1, 512, 1);
    private readonly NumericUpDown epochs = Number(1, 1, 10000, 1);
    private readonly RichTextBox log = new RichTextBox();
    private readonly Button inspect = new Button { Text = "Import / validate IDS", AutoSize = true };
    private readonly Button start = new Button { Text = "Start training", AutoSize = true };
    private readonly Button cancel = new Button { Text = "Cancel", Enabled = false };
    private readonly Button open = new Button { Text = "Open output", AutoSize = true };
    private readonly Label status = new Label { Text = "Select an IDS full package.", AutoSize = true };
    private Process active;
    private bool cancelled;
    private string lastRun;

    internal TrainerForm()
    {
        Text = "IVAD Open Trainer v0.1";
        ClientSize = new Size(850, 620);
        MinimumSize = new Size(670, 480);
        Font = new Font("Segoe UI", 10);
        var grid = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(12), ColumnCount = 3 };
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        Controls.Add(grid);

        output.Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "IVAD Training");
        Configure(model, "YOLOv8n", "RF-DETR Nano");
        Configure(device, "CPU", "Intel XPU", "NVIDIA CUDA");
        model.SelectedIndexChanged += delegate { weights.Clear(); };
        Row(grid, "IDS full package", source, Browse(delegate { SelectFile(source, "IDS packages (*.ids)|*.ids"); }));
        Row(grid, "Output folder", output, Browse(delegate {
            using (var dialog = new FolderBrowserDialog())
                if (dialog.ShowDialog(this) == DialogResult.OK) output.Text = dialog.SelectedPath;
        }));
        Row(grid, "Trusted local weights (optional)", weights, Browse(delegate {
            SelectFile(weights, model.SelectedIndex == 0 ? "YOLO weights (*.pt)|*.pt" : "RF-DETR weights (*.pth)|*.pth");
        }));
        Row(grid, "Model", model, null);
        Row(grid, "Device", device, null);
        var settings = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, WrapContents = false };
        settings.Controls.AddRange(new Control[] { size, Field("Batch"), batch, Field("Epochs"), epochs });
        Row(grid, "Image size", settings, null);
        var buttons = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, WrapContents = false };
        buttons.Controls.AddRange(new Control[] { inspect, start, cancel, open });
        FullRow(grid, buttons, SizeType.AutoSize);
        FullRow(grid, status, SizeType.AutoSize);
        log.ReadOnly = true;
        log.WordWrap = false;
        log.Font = new Font("Consolas", 9);
        FullRow(grid, log, SizeType.Percent);

        inspect.Click += delegate { Run(false); };
        start.Click += delegate { Run(true); };
        cancel.Click += delegate { Stop(); };
        open.Click += delegate {
            try
            {
                var path = lastRun ?? Path.GetFullPath(output.Text);
                Directory.CreateDirectory(path);
                Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
            }
            catch (Exception error) { Append(error.Message); }
        };
    }

    private static NumericUpDown Number(int value, int min, int max, int increment)
    {
        return new NumericUpDown { Minimum = min, Maximum = max, Increment = increment, Value = value, Width = 70 };
    }

    private static Label Field(string text)
    {
        return new Label { Text = text, AutoSize = true, Anchor = AnchorStyles.Left };
    }

    private static void Configure(ComboBox box, params string[] items)
    {
        box.DropDownStyle = ComboBoxStyle.DropDownList;
        box.Items.AddRange(items);
        box.SelectedIndex = 0;
    }

    private static Button Browse(Action select)
    {
        var button = new Button { Text = "Browse...", AutoSize = true };
        button.Click += delegate { select(); };
        return button;
    }

    private void SelectFile(TextBox target, string filter)
    {
        using (var dialog = new OpenFileDialog { Filter = filter, CheckFileExists = true })
            if (dialog.ShowDialog(this) == DialogResult.OK) target.Text = dialog.FileName;
    }

    private static void Row(TableLayoutPanel grid, string label, Control control, Button button)
    {
        int row = grid.RowCount++;
        grid.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        control.Dock = DockStyle.Fill;
        grid.Controls.Add(Field(label), 0, row);
        grid.Controls.Add(control, 1, row);
        if (button != null) grid.Controls.Add(button, 2, row);
    }

    private static void FullRow(TableLayoutPanel grid, Control control, SizeType height)
    {
        int row = grid.RowCount++;
        grid.RowStyles.Add(new RowStyle(height, 100));
        control.Dock = DockStyle.Fill;
        grid.Controls.Add(control, 0, row);
        grid.SetColumnSpan(control, 3);
    }

    private void Run(bool train)
    {
        if (!File.Exists(source.Text) || (train && String.IsNullOrWhiteSpace(output.Text)))
        {
            status.Text = "Select an existing IDS package and an output folder.";
            return;
        }
        log.Clear();
        if (train) lastRun = null;
        try
        {
            var args = new List<string> { train ? "train" : "inspect", "--ids", Path.GetFullPath(source.Text) };
            if (train)
            {
                args.AddRange(new[] { "--output", Path.GetFullPath(output.Text),
                    "--model", model.SelectedIndex == 0 ? "yolo" : "rf",
                    "--device", new[] { "cpu", "xpu", "cuda" }[device.SelectedIndex],
                    "--size", ((int)size.Value).ToString(), "--batch", ((int)batch.Value).ToString(),
                    "--epochs", ((int)epochs.Value).ToString() });
                if (!String.IsNullOrWhiteSpace(weights.Text))
                    args.AddRange(new[] { "--weights", Path.GetFullPath(weights.Text) });
            }
            var process = new Process { StartInfo = Worker.StartInfo(args.ToArray()), EnableRaisingEvents = true };
            active = process;
            cancelled = false;
            process.OutputDataReceived += ReadLine;
            process.ErrorDataReceived += ReadLine;
            process.Exited += delegate {
                process.WaitForExit();
                int code = process.ExitCode;
                Post(delegate {
                    status.Text = cancelled ? "Cancelled." : code != 0 ? "Failed. See the log for the cause." :
                        train ? "Training completed. Open output to find the checkpoint." : "IDS validation completed.";
                    active = null;
                    process.Dispose();
                    Buttons(false);
                });
            };
            process.Start();
            process.BeginOutputReadLine();
            process.BeginErrorReadLine();
            status.Text = train ? "Training..." : "Validating IDS...";
            Buttons(true);
        }
        catch (Exception error)
        {
            if (active != null) active.Dispose();
            active = null;
            status.Text = "Unable to start.";
            Append(error.Message);
        }
    }

    private void ReadLine(object sender, DataReceivedEventArgs args)
    {
        if (args.Data != null) Post(delegate { Append(args.Data); });
    }

    private void Post(Action callback)
    {
        if (!IsHandleCreated || IsDisposed) return;
        try { BeginInvoke(callback); }
        catch (InvalidOperationException) { }
    }

    private void Append(string line)
    {
        if (line.StartsWith("OUTPUT ", StringComparison.Ordinal)) lastRun = line.Substring(7);
        log.AppendText(line + Environment.NewLine);
        log.SelectionStart = log.TextLength;
        log.ScrollToCaret();
    }

    private void Buttons(bool busy)
    {
        inspect.Enabled = start.Enabled = !busy;
        cancel.Enabled = busy;
    }

    private void Stop()
    {
        if (active == null || active.HasExited) return;
        cancelled = true;
        try { active.Kill(); }
        catch (InvalidOperationException) { }
    }

    protected override void OnFormClosing(FormClosingEventArgs args)
    {
        Stop();
        base.OnFormClosing(args);
    }
}
