using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Text.RegularExpressions;
using System.Windows.Forms;


internal sealed partial class TrainerForm
{
    private readonly ComboBox trainModel = Views.Choice("模型", ModelLabels);
    private readonly ComboBox trainDevice = Views.Choice("设备", DeviceLabels);
    private readonly NumericUpDown trainSize = Views.Number("输入尺寸", 64, 2048, 384, 32);
    private readonly NumericUpDown trainBatch = Views.Number("Batch Size", 1, 512, 1, 1);
    private readonly NumericUpDown trainEpochs = Views.Number("Epochs", 1, 10000, 1, 1);
    private readonly Label trainProject = Views.Single("");
    private readonly Label trainStatus = Views.Single("任务状态   ·   就绪");
    private readonly Label actualDevice = Views.Single("实际设备   ·   —");
    private readonly Label epochStatus = Views.Single("Epoch   ·   —");
    private readonly ProgressBar progressBar = new ProgressBar { Dock = DockStyle.Fill, Margin = new Padding(0, 7, 7, 7) };
    private readonly RichTextBox trainLog = new RichTextBox { Dock = DockStyle.Fill, ReadOnly = true,
        BackColor = Color.FromArgb(245, 249, 253), BorderStyle = BorderStyle.None, DetectUrls = false };
    private readonly Button trainStart = Views.Button("开始训练", true);
    private readonly Button trainCancel = Views.Button("取消训练");
    private readonly Button exportModel = Views.Button("导出原生权重", true);
    private readonly Button openRun = Views.Button("打开权重目录");
    private readonly Dictionary<string, Label> metricLabels = new Dictionary<string, Label>();
    private static readonly Regex ConsoleCodes = new Regex(@"\x1b\[[0-9;?]*[a-zA-Z]", RegexOptions.Compiled);
    private PathView boundIds, outputPath, initialPath, artifactPath;
    private string trainingOutput, initialWeights;

    private Control TrainingPage()
    {
        var left = Views.ScrollBody();
        Views.Row(left, Views.Text("项目与配置", 16, true), 42);
        trainProject.Font = new Font(Font.FontFamily, 10, FontStyle.Bold);
        boundIds = new PathView("已绑定 IDS", tooltips);
        Views.Field(left, "项目名称", trainProject);
        Views.Field(left, "已绑定 IDS", boundIds);
        Views.Field(left, "模型", trainModel);
        Views.Field(left, "设备", trainDevice);
        Views.Field(left, "输入尺寸", trainSize);
        Views.Field(left, "Batch Size", trainBatch);
        Views.Field(left, "Epochs", trainEpochs);
        var browseOutput = Views.Button("选择");
        var browseInitial = Views.Button("选择");
        var clearInitial = Views.Button("清除初始权重");
        outputPath = new PathView("输出目录", tooltips, browseOutput);
        initialPath = new PathView("初始权重", tooltips, browseInitial);
        Views.Field(left, "输出目录", outputPath);
        Views.Field(left, "初始权重", initialPath);
        Views.Row(left, Views.Actions(clearInitial), 43);
        Views.Row(left, Views.Actions(trainStart), 48);
        browseOutput.Click += delegate {
            using (var dialog = new FolderBrowserDialog { SelectedPath = trainingOutput ?? "" })
                if (dialog.ShowDialog(this) == DialogResult.OK)
                {
                    trainingOutput = dialog.SelectedPath;
                    outputPath.ShowPath(trainingOutput);
                }
        };
        browseInitial.Click += delegate {
            string picked = Pick("选择可信的本地初始权重", WeightFilter(Key(Models, trainModel)));
            if (picked != null) { initialWeights = picked; initialPath.ShowPath(picked); }
        };
        clearInitial.Click += delegate { initialWeights = null; initialPath.ShowPath(null, "从头训练"); };
        trainModel.SelectedIndexChanged += delegate {
            if (loading) return;
            if (!String.IsNullOrEmpty(initialWeights) && !WeightSuffix(initialWeights, Key(Models, trainModel)))
            {
                initialWeights = null;
                initialPath.ShowPath(null, "从头训练");
            }
            RefreshArtifacts();
        };
        trainStart.Click += delegate { StartTraining(); };
        trainCancel.Enabled = false;
        trainCancel.Click += delegate {
            if (!trainer.Active) return;
            SetStatus(trainStatus, "任务状态   ·   正在停止", Views.Muted);
            trainCancel.Enabled = false;
            Stop(trainer, trainStatus);
        };

        var right = Views.Grid();
        Views.Row(right, Views.Text("训练监控", 16, true), 43);
        Views.Row(right, trainStatus, 32);
        Views.Row(right, actualDevice, 30);
        Views.Row(right, epochStatus, 30);
        var controls = Views.Grid(2);
        controls.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        controls.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        controls.Controls.Add(progressBar, 0, 0);
        controls.Controls.Add(trainCancel, 1, 0);
        Views.Row(right, controls, 42);

        var tabs = new TabControl { Dock = DockStyle.Fill, Margin = new Padding(0, 6, 0, 0) };
        var logs = new TabPage("实时日志") { BackColor = Color.White, Padding = new Padding(9) };
        trainLog.Font = new Font("Microsoft YaHei UI", 9);
        logs.Controls.Add(trainLog);
        tabs.TabPages.Add(logs);
        var metrics = new TabPage("训练指标") { BackColor = Color.White, Padding = new Padding(12), AutoScroll = true };
        var measured = Views.ScrollBody();
        string[] keys = { "loss", "map50", "map", "precision", "recall" };
        string[] labels = { "训练损失", "mAP@50", "mAP@50–95", "精确率", "召回率" };
        for (int i = 0; i < keys.Length; i++)
        {
            var value = Views.Single("暂无");
            metricLabels[keys[i]] = value;
            Views.Field(measured, labels[i], value);
        }
        metrics.Controls.Add(measured);
        tabs.TabPages.Add(metrics);
        var exports = new TabPage("模型导出") { BackColor = Color.White, Padding = new Padding(12) };
        var export = Views.ScrollBody();
        artifactPath = new PathView("已生成权重", tooltips);
        Views.Field(export, "已生成权重", artifactPath);
        Views.Row(export, Views.Actions(exportModel, openRun), 44);
        exports.Controls.Add(export);
        tabs.TabPages.Add(exports);
        exportModel.Click += delegate { Export(); };
        openRun.Click += delegate {
            string path = Artifact(Project, Key(Models, trainModel));
            if (path == null) return;
            try { Process.Start(new ProcessStartInfo(Path.GetDirectoryName(path)) { UseShellExecute = true }); }
            catch (Exception error) { SetStatus(trainStatus, "无法打开目录：" + error.Message, Views.Error); }
        };
        Views.Row(right, tabs, -1);
        return Views.Columns(Views.Card(left, true), Views.Card(right));
    }

    private void LoadTrainingFields()
    {
        SelectKey(Models, trainModel, Project.Model);
        SelectKey(Devices, trainDevice, Project.Device);
        SetNumber(trainSize, Project.Size, 384);
        SetNumber(trainBatch, Project.Batch, 1);
        SetNumber(trainEpochs, Project.Epochs, 1);
        trainingOutput = Project.Output ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "IVAD Training", ProjectName);
        initialWeights = Project.InitialWeights;
        outputPath.ShowPath(trainingOutput);
        initialPath.ShowPath(initialWeights, "从头训练");
    }

    private void StoreTrainingFields()
    {
        Project.Model = Key(Models, trainModel);
        Project.Device = Key(Devices, trainDevice);
        Project.Size = trainSize.Value;
        Project.Batch = trainBatch.Value;
        Project.Epochs = trainEpochs.Value;
        Project.Output = trainingOutput;
        Project.InitialWeights = initialWeights;
    }

    private static string WeightFilter(string model)
    { return model == "rf" ? "RF-DETR 权重 (*.pth)|*.pth" : "YOLOv8 权重 (*.pt)|*.pt"; }
    private static bool WeightSuffix(string file, string model)
    { return file != null && Path.GetExtension(file).Equals(model == "rf" ? ".pth" : ".pt", StringComparison.OrdinalIgnoreCase); }

    private void StartTraining()
    {
        if (trainer.Active) return;
        string project = ProjectName;
        StoreTrainingFields();
        if (!verified.ContainsKey(project) || !File.Exists(Project.Ids))
        { SetStatus(trainStatus, "请选择并校验存在的 IDS 文件", Views.Error); return; }
        if (Project.Size % 32 != 0)
        { SetStatus(trainStatus, "输入尺寸必须为 32 的倍数", Views.Error); return; }
        if (!String.IsNullOrEmpty(initialWeights) && (!WeightSuffix(initialWeights, Project.Model) || !File.Exists(initialWeights)))
        { SetStatus(trainStatus, "初始权重不存在或文件扩展名与模型不匹配", Views.Error); return; }
        string model = Project.Model;
        string failure = null;
        string checkpoint = null;
        var args = new List<string> { "train", "--ids", Project.Ids, "--model", model, "--device", Project.Device,
            "--size", DecimalArg(Project.Size), "--batch", DecimalArg(Project.Batch),
            "--epochs", DecimalArg(Project.Epochs), "--output", trainingOutput };
        if (!String.IsNullOrEmpty(initialWeights)) args.AddRange(new[] { "--weights", initialWeights });
        if (!SaveWorkspace(trainStatus)) return;
        progressBar.Value = 0;
        trainLog.Clear();
        ShowMetrics(null);
        actualDevice.Text = "实际设备   ·   正在检查";
        epochStatus.Text = "Epoch   ·   — / " + Project.Epochs;
        SetStatus(trainStatus, "任务状态   ·   正在检查设备", Views.Blue);
        try
        {
            trainer.Start(args.ToArray(), AppendLog, message => {
                string kind = Workspace.Value(message, "kind");
                if (kind == "stage") SetStatus(trainStatus, project + "  ·  " + Workspace.Value(message, "value"), Views.Blue);
                else if (kind == "device") actualDevice.Text = "实际设备   ·   " + Workspace.Value(message, "value") +
                    "   " + Workspace.Value(message, "hardware");
                else if (kind == "progress") ShowProgress(message);
                else if (kind == "metrics") ShowMetrics(Workspace.Object(message, "values"));
                else if (kind == "error") failure = Workspace.Value(message, "value");
                else if (kind == "checkpoint")
                {
                    checkpoint = Workspace.Value(message, "path");
                    ShowMetrics(Workspace.Object(message, "metrics"));
                }
            }, (code, cancelled) => {
                SetTrainingBusy(false);
                if (cancelled) SetStatus(trainStatus, project + "  ·  已取消", Views.Muted);
                else if (code != 0 || !File.Exists(checkpoint))
                    SetStatus(trainStatus, "训练失败：" + (failure ?? "未生成可用权重，退出码 " + code), Views.Error);
                else
                {
                    var resultProject = workspace.Data.Projects[project];
                    if (resultProject.Artifacts == null) resultProject.Artifacts = new Dictionary<string, string>();
                    resultProject.Artifacts[model] = checkpoint;
                    progressBar.Value = 100;
                    SetStatus(trainStatus, project + "  ·  训练完成", Views.Good);
                    SaveWorkspace(trainStatus);
                }
                RefreshArtifacts();
            });
            SetTrainingBusy(true);
        }
        catch (Exception error)
        {
            actualDevice.Text = "实际设备   ·   —";
            SetStatus(trainStatus, "无法启动训练：" + error.Message, Views.Error);
        }
    }

    private void SetTrainingBusy(bool busy)
    {
        trainCancel.Enabled = busy;
        trainStart.Enabled = !busy && verified.ContainsKey(ProjectName) && !importer.Active;
    }

    private void ShowProgress(Dictionary<string, object> message)
    {
        double total = Workspace.Number(message, "epochs");
        double epoch = Workspace.Number(message, "epoch");
        double batches = Workspace.Number(message, "batches");
        double batch = Workspace.Number(message, "batch");
        if (total > 0 && batches > 0)
            progressBar.Value = Math.Min(100, Math.Max(0, (int)(100 * (epoch - 1 + batch / batches) / total)));
        epochStatus.Text = String.Format("Epoch   ·   {0} / {1}      批次 {2} / {3}", epoch, total, batch, batches);
    }

    private void ShowMetrics(Dictionary<string, object> values)
    {
        foreach (var label in metricLabels)
        {
            string text = Workspace.Value(values, label.Key);
            label.Value.Text = String.IsNullOrEmpty(text) ? "暂无" : Workspace.Number(values, label.Key).ToString("0.0000");
        }
    }

    private void AppendLog(string line)
    {
        if (String.IsNullOrWhiteSpace(line)) return;
        if (trainLog.TextLength > 85000)
        {
            trainLog.Select(0, 30000);
            trainLog.SelectedText = "";
        }
        trainLog.AppendText(ConsoleCodes.Replace(line, "") + Environment.NewLine);
        trainLog.SelectionStart = trainLog.TextLength;
        trainLog.ScrollToCaret();
    }

    private void RefreshArtifacts()
    {
        string path = Artifact(Project, Key(Models, trainModel));
        artifactPath.ShowPath(path, "暂无可导出的权重");
        exportModel.Enabled = openRun.Enabled = path != null;
        RefreshVideoWeights();
    }

    private void Export()
    {
        string source = Artifact(Project, Key(Models, trainModel));
        if (source == null) return;
        using (var dialog = new SaveFileDialog { Title = "导出原生权重", Filter = WeightFilter(Key(Models, trainModel)),
            FileName = Path.GetFileName(source), OverwritePrompt = true, AddExtension = true })
        {
            if (dialog.ShowDialog(this) != DialogResult.OK) return;
            try
            {
                if (!String.Equals(source, dialog.FileName, StringComparison.OrdinalIgnoreCase))
                    File.Copy(source, dialog.FileName, true);
                SetStatus(trainStatus, "已导出  ·  " + Path.GetFileName(dialog.FileName), Views.Good);
            }
            catch (Exception error) { SetStatus(trainStatus, "导出失败：" + error.Message, Views.Error); }
        }
    }
}
