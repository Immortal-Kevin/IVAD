using System;
using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text.RegularExpressions;
using System.Windows.Forms;


internal sealed partial class TrainerForm
{
    private readonly ComboBox trainModel = Views.Choice("模型", ModelLabels);
    private static readonly string[] DetectionSplits = { "events", "frames" };
    private readonly ComboBox trainSplit = Views.Choice("检测拆分", "按事件分组", "按帧分层（Val / Test 各约 20% 正例）");
    private readonly Label splitHint = Views.Single("");
    private readonly CheckBox diagnosticReuse = new CheckBox { Text = "样本不足时允许复用训练图做诊断", AutoSize = true };
    private readonly Label validationSources = Views.Single("");
    private readonly ComboBox trainDevice = Views.Choice("设备", DeviceLabels);
    private readonly NumericUpDown trainSize = Views.Number("输入尺寸", 64, 2048, 384, 32);
    private readonly NumericUpDown trainBatch = Views.Number("Batch Size", 1, 512, 1, 1);
    private readonly NumericUpDown trainEpochs = Views.Number("Epochs", 1, 10000, 1, 1);
    private readonly CheckBox earlyStop = new CheckBox { Text = "自动早停", AutoSize = true, Checked = true };
    private readonly TextBox anomalyRoi = new TextBox { Text = "0, 0, 1, 1", Dock = DockStyle.Fill,
        AccessibleName = "异常检测 ROI，左、上、右、下归一化坐标" };
    private readonly Label trainProject = Views.Single("");
    private readonly Label trainStatus = Views.Single("任务状态   ·   就绪");
    private readonly Label splitStatus = Views.Single("自动拆分   ·   等待训练任务");
    private readonly Label earlyStopStatus = Views.Single("自动早停   ·   等待拆分");
    private readonly Label actualDevice = Views.Single("实际设备   ·   —");
    private readonly Label epochStatus = Views.Single("Epoch   ·   —");
    private readonly ProgressBar progressBar = new ProgressBar { Dock = DockStyle.Fill, Margin = Views.Pads(0, 5, 5, 5) };
    private readonly RichTextBox trainLog = new RichTextBox { Dock = DockStyle.Fill, ReadOnly = true,
        BackColor = Color.FromArgb(245, 249, 253), BorderStyle = BorderStyle.None, DetectUrls = false };
    private readonly Button trainStart = Views.Button("开始训练", true);
    private readonly Button planStart = Views.Button("预览拆分");
    private readonly Label sourceGate = Views.Single("");
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
        trainProject.Font = Views.UiFont(10, FontStyle.Bold);
        boundIds = new PathView("已绑定 IDS", tooltips);
        Views.Field(left, "项目名称", trainProject);
        Views.Field(left, "已绑定 IDS", boundIds);
        Views.Field(left, "模式与模型", trainModel);
        Views.Field(left, "检测拆分", trainSplit);
        Views.Wrap(left, splitHint);
        Views.Row(left, splitHint, 32);
        Views.Row(left, diagnosticReuse, 34);
        Views.Field(left, "设备", trainDevice);
        Views.Field(left, "输入尺寸", trainSize);
        Views.Field(left, "Batch Size", trainBatch);
        Views.Field(left, "Epochs", trainEpochs);
        Views.Row(left, earlyStop, 32);
        Views.Field(left, "异常 ROI（左,上,右,下）", anomalyRoi);
        tooltips.SetToolTip(anomalyRoi, "在 0–1 范围内输入左、上、右、下。默认 0,0,1,1 为全图，回放沿用已拟合的 ROI。");
        var browseOutput = Views.Button("选择");
        var browseInitial = Views.Button("选择");
        var clearInitial = Views.Button("清除初始权重");
        outputPath = new PathView("输出目录", tooltips, browseOutput);
        initialPath = new PathView("初始权重", tooltips, browseInitial);
        Views.Field(left, "输出目录", outputPath);
        Views.Field(left, "初始权重", initialPath);
        Views.Row(left, Views.Actions(clearInitial), 43);
        Views.Wrap(left, sourceGate);
        Views.Row(left, sourceGate, 37);
        Views.Row(left, Views.Actions(trainStart, planStart), 48);
        browseOutput.Click += delegate {
            using (var dialog = new FolderBrowserDialog { SelectedPath = trainingOutput ?? "" })
                if (dialog.ShowDialog(this) == DialogResult.OK)
                {
                    trainingOutput = dialog.SelectedPath;
                    outputPath.ShowPath(trainingOutput);
                }
        };
        browseInitial.Click += delegate {
            if (Key(Models, trainModel) == "anomaly") return;
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
            RefreshModeFields();
            RefreshArtifacts();
        };
        trainSplit.SelectedIndexChanged += delegate { if (!loading) RefreshModeFields(); };
        trainStart.Click += delegate { StartTraining(false); };
        planStart.Click += delegate { StartTraining(true); };
        trainCancel.Enabled = false;
        trainCancel.Click += delegate {
            if (!trainer.Active) return;
            SetStatus(trainStatus, "任务状态   ·   正在停止", Views.Muted);
            trainCancel.Enabled = false;
            Stop(trainer, trainStatus);
        };

        var right = Views.Grid();
        Views.Row(right, Views.Text("训练监控", 16, true), 43);
        Views.Wrap(right, trainStatus);
        Views.Row(right, trainStatus, 32);
        Views.Wrap(right, splitStatus);
        Views.Row(right, splitStatus, 30);
        Views.Wrap(right, earlyStopStatus);
        Views.Row(right, earlyStopStatus, 30);
        Views.Row(right, actualDevice, 30);
        Views.Row(right, epochStatus, 30);
        var controls = Views.Grid(2);
        controls.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        controls.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        controls.Controls.Add(progressBar, 0, 0);
        controls.Controls.Add(trainCancel, 1, 0);
        Views.Row(right, controls, 42);

        var tabs = new TabControl { Dock = DockStyle.Fill, Margin = Views.Pads(0, 6, 0, 0) };
        var logs = new TabPage("实时日志") { BackColor = Color.White, Padding = Views.Pads(9) };
        trainLog.Font = Views.UiFont(9);
        logs.Controls.Add(trainLog);
        tabs.TabPages.Add(logs);
        var metrics = new TabPage("训练指标") { BackColor = Color.White, Padding = Views.Pads(12), AutoScroll = true };
        var measured = Views.ScrollBody();
        string[] keys = { "loss", "map50", "map", "precision", "recall" };
        string[] labels = { "训练损失", "mAP@50", "mAP@50–95", "精确率", "召回率" };
        for (int i = 0; i < keys.Length; i++)
        {
            var value = Views.Single("暂无");
            metricLabels[keys[i]] = value;
            Views.Field(measured, labels[i], value);
        }
        Views.Wrap(measured, validationSources);
        Views.Row(measured, validationSources, 112);
        metrics.Controls.Add(measured);
        tabs.TabPages.Add(metrics);
        var exports = new TabPage("模型导出") { BackColor = Color.White, Padding = Views.Pads(12) };
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
        return Views.PageColumns(Views.Card(left, true), Views.Card(right));
    }

    private void LoadTrainingFields()
    {
        SelectKey(Models, trainModel, Project.Model);
        SelectKey(DetectionSplits, trainSplit, Project.DetectionSplit);
        diagnosticReuse.Checked = Project.AllowDiagnosticReuse;
        SelectKey(Devices, trainDevice, Project.Device);
        SetNumber(trainSize, Project.Size, 384);
        SetNumber(trainBatch, Project.Batch, 1);
        SetNumber(trainEpochs, Project.Epochs, ProjectName == Workspace.Preset ? 3 : 1);
        earlyStop.Checked = Project.AutoEarlyStop ?? true;
        anomalyRoi.Text = Project.AnomalyRoi ?? "0, 0, 1, 1";
        RefreshModeFields();
        trainingOutput = Project.Output ?? Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "IVAD Training", ProjectName);
        initialWeights = Project.InitialWeights;
        outputPath.ShowPath(trainingOutput);
        initialPath.ShowPath(initialWeights, "从头训练");
    }

    private void StoreTrainingFields()
    {
        Project.Model = Key(Models, trainModel);
        Project.DetectionSplit = Key(DetectionSplits, trainSplit);
        Project.AllowDiagnosticReuse = diagnosticReuse.Checked;
        Project.Device = Key(Devices, trainDevice);
        Project.Size = trainSize.Value;
        Project.Batch = trainBatch.Value;
        Project.Epochs = trainEpochs.Value;
        Project.Output = trainingOutput;
        Project.InitialWeights = initialWeights;
        Project.AutoEarlyStop = earlyStop.Checked;
        Project.AnomalyRoi = anomalyRoi.Text;
    }

    private void RefreshModeFields()
    {
        string model = Key(Models, trainModel);
        bool detection = model != "anomaly";
        trainDevice.Enabled = trainSize.Enabled = trainBatch.Enabled = trainEpochs.Enabled = detection;
        trainSplit.Enabled = detection;
        diagnosticReuse.Enabled = detection && Key(DetectionSplits, trainSplit) == "frames";
        splitHint.Text = detection && Key(DetectionSplits, trainSplit) == "frames" ?
            "同源帧评估 · 同一事件的不同帧可跨集合" : "";
        anomalyRoi.Enabled = !detection;
        earlyStop.Enabled = model == "rf";
    }

    private static string WeightFilter(string model)
    { return model == "anomaly" ? "正常模型 (*.npz)|*.npz" : model == "rf" ? "RF-DETR 权重 (*.pth)|*.pth" : "YOLOv8 权重 (*.pt)|*.pt"; }
    private static bool WeightSuffix(string file, string model)
    { return file != null && Path.GetExtension(file).Equals(model == "anomaly" ? ".npz" : model == "rf" ? ".pth" : ".pt", StringComparison.OrdinalIgnoreCase); }

    private void StartTraining(bool planOnly)
    {
        if (trainer.Active) return;
        string project = ProjectName;
        StoreTrainingFields();
        if (!verified.ContainsKey(project) || !File.Exists(Project.Ids))
        { SetStatus(trainStatus, "请选择并校验存在的 IDS 文件", Views.Error); return; }
        var sources = CheckedSources();
        if (sources.Count == 0)
        { SetStatus(trainStatus, "请至少选择一个源视频", Views.Error); return; }
        if (sources.TrueForAll(IsTestOnly))
        { SetStatus(trainStatus, "只有仅测试源，请勾选至少一个参与自动拆分的源视频。", Views.Error); return; }
        string model = Project.Model;
        bool detection = model != "anomaly";
        if (!planOnly && detection && Project.Size % 32 != 0)
        { SetStatus(trainStatus, "输入尺寸必须为 32 的倍数", Views.Error); return; }
        if (!planOnly && detection && !String.IsNullOrEmpty(initialWeights) && (!WeightSuffix(initialWeights, model) || !File.Exists(initialWeights)))
        { SetStatus(trainStatus, "初始权重不存在或文件扩展名与模型不匹配", Views.Error); return; }
        string failure = null;
        string checkpoint = null;
        string manifest = null;
        bool stoppedEarly = false;
        var args = new List<string> { planOnly ? "plan" : "train", "--ids", Project.Ids, "--model", model, "--output", trainingOutput };
        if (detection) args.AddRange(new[] { "--split-strategy", Project.DetectionSplit });
        if (detection && Project.DetectionSplit == "frames" && Project.AllowDiagnosticReuse) args.Add("--allow-diagnostic-reuse");
        if (!planOnly && detection)
            args.AddRange(new[] { "--device", Project.Device, "--size", DecimalArg(Project.Size), "--batch",
                DecimalArg(Project.Batch), "--epochs", DecimalArg(Project.Epochs) });
        else if (!planOnly)
        {
            string[] coordinates = anomalyRoi.Text.Split(',');
            if (coordinates.Length != 4)
            { SetStatus(trainStatus, "请输入四个逗号分隔的 ROI 坐标", Views.Error); return; }
            args.Add("--roi");
            foreach (string coordinate in coordinates)
            {
                decimal value;
                if (!Decimal.TryParse(coordinate.Trim(), NumberStyles.AllowDecimalPoint, CultureInfo.InvariantCulture, out value))
                { SetStatus(trainStatus, "ROI 坐标应使用 0 到 1 的小数", Views.Error); return; }
                args.Add(DecimalArg(value));
            }
        }
        foreach (string source in sources)
        {
            args.AddRange(new[] { "--source-video", source });
            if (IsTestOnly(source)) args.AddRange(new[] { "--test-only-video", source });
        }
        if (!earlyStop.Checked) args.Add("--no-early-stop");
        if (!planOnly && detection && !String.IsNullOrEmpty(initialWeights)) args.AddRange(new[] { "--weights", initialWeights });
        if (!SaveWorkspace(trainStatus)) return;
        progressBar.Value = 0;
        trainLog.Clear();
        ShowMetrics(null);
        validationSources.Text = "";
        SetStatus(splitStatus, "自动拆分   ·   正在分析 IDS", Views.Muted);
        tooltips.SetToolTip(splitStatus, "");
        SetStatus(earlyStopStatus, "自动早停   ·   等待拆分", Views.Muted);
        actualDevice.Text = planOnly ? "仅生成拆分清单" : "实际设备   ·   正在检查";
        epochStatus.Text = planOnly ? "" : "Epoch   ·   — / " + Project.Epochs;
        SetStatus(trainStatus, planOnly ? "正在预览拆分" : "任务状态   ·   正在检查设备", Views.Blue);
        try
        {
            trainer.Start(args.ToArray(), AppendLog, message => {
                string kind = Workspace.Value(message, "kind");
                if (kind == "stage") SetStatus(trainStatus, project + "  ·  " + Workspace.Value(message, "value"), Views.Blue);
                else if (kind == "device") actualDevice.Text = "实际设备   ·   " + Workspace.Value(message, "value") +
                    "   " + Workspace.Value(message, "hardware");
                else if (kind == "split")
                {
                    manifest = Workspace.Value(message, "path");
                    SetStatus(splitStatus, "自动拆分   ·   " + Workspace.Value(message, "mode") +
                        "   ·   " + Workspace.Value(message, "validation_summary") + "   ·   复用 " +
                        Workspace.Value(message, "reused") + " 张", Views.Blue);
                    tooltips.SetToolTip(splitStatus, Workspace.Value(message, "detail"));
                    SetStatus(earlyStopStatus, detection ? "自动早停   ·   " + Workspace.Value(message, "early_stop_status") : "阈值仅由独立正常 Val 校准", Views.Blue);
                }
                else if (kind == "progress") ShowProgress(message);
                else if (kind == "metrics") ShowMetrics(Workspace.Object(message, "values"));
                else if (kind == "evaluation")
                {
                    var diag = Workspace.Object(message, "diagnostic_metrics");
                    string title = diag == null ? "Val · 已保存权重" : "Val · 训练内诊断 mAP@50 " +
                        FormatMetric(diag, "map50") + " · mAP@50–95 " + FormatMetric(diag, "map");
                    validationSources.Text = title + " · 阈值 " + Workspace.Value(message, "threshold") +
                        Environment.NewLine + SourceHits(message);
                    tooltips.SetToolTip(validationSources, validationSources.Text);
                }
                else if (kind == "source_evaluation_error")
                    validationSources.Text = "Val 来源评估失败 · " + Workspace.Value(message, "value");
                else if (kind == "error") failure = Workspace.Value(message, "value");
                else if (kind == "checkpoint")
                {
                    checkpoint = Workspace.Value(message, "path");
                    var stop = Workspace.Object(message, "early_stop");
                    stoppedEarly = stop != null;
                    if (stoppedEarly) SetStatus(earlyStopStatus, Workspace.Value(stop, "reason"), Views.Good);
                    ShowMetrics(Workspace.Object(message, "metrics"));
                }
            }, (code, cancelled) => {
                SetTrainingBusy(false);
                if (cancelled) SetStatus(trainStatus, project + "  ·  已取消", Views.Muted);
                else if (planOnly)
                {
                    bool ok = code == 0 && File.Exists(manifest);
                    SetStatus(trainStatus, ok ? "拆分预览完成 · 清单已保存" : "拆分预览失败：" + (failure ?? "清单未生成"),
                        ok ? Views.Good : Views.Error);
                    if (ok) progressBar.Value = 100;
                }
                else if (code != 0 || !File.Exists(checkpoint))
                    SetStatus(trainStatus, "训练失败：" + (failure ?? "未生成可用权重，退出码 " + code), Views.Error);
                else
                {
                    var resultProject = workspace.Data.Projects[project];
                    if (resultProject.Artifacts == null) resultProject.Artifacts = new Dictionary<string, string>();
                    resultProject.Artifacts[model] = checkpoint;
                    progressBar.Value = 100;
                    SetStatus(trainStatus, project + "  ·  训练完成" + (stoppedEarly ? " · 自动早停" : ""), Views.Good);
                    SaveWorkspace(trainStatus);
                }
                RefreshArtifacts();
            });
            SetTrainingBusy(true);
        }
        catch (Exception error)
        {
            actualDevice.Text = "实际设备   ·   —";
            SetStatus(trainStatus, (planOnly ? "无法预览拆分：" : "无法启动训练：") + error.Message, Views.Error);
        }
    }

    private void SetTrainingBusy(bool busy)
    {
        trainCancel.Enabled = busy;
        RefreshSourceActions();
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
            bool validationMetric = label.Key == "map" || label.Key == "map50" || label.Key == "recall";
            label.Value.Text = validationMetric && values != null ? FormatMetric(values, label.Key) :
                String.IsNullOrEmpty(text) ? "暂无" : Workspace.Number(values, label.Key).ToString("0.0000");
        }
    }

    private static string FormatMetric(Dictionary<string, object> values, string key)
    {
        double value;
        if (!Double.TryParse(Workspace.Value(values, key), NumberStyles.Float, CultureInfo.InvariantCulture, out value)
            || Double.IsNaN(value) || Double.IsInfinity(value)) return "不可计算";
        return value.ToString(value == 0 ? "0" : Math.Abs(value) < 0.0001 ? "0.###E+0" : "0.0000",
            CultureInfo.InvariantCulture);
    }

    private static string SourceHits(Dictionary<string, object> values)
    {
        object raw;
        if (!values.TryGetValue("sources", out raw)) return "";
        var lines = new List<string>();
        foreach (object item in raw as IList ?? new object[0])
        {
            var source = item as Dictionary<string, object>;
            if (Workspace.Number(source, "images") == 0) continue;
            string count = Workspace.Value(source, "positive_images");
            lines.Add(Workspace.Value(source, "name") + " · 正例命中 " + (count == "0" ? "无正例" :
                Workspace.Value(source, "positive_hits") + "/" + count) + " · 复用 " + Workspace.Value(source, "reused") + " 张");
        }
        return String.Join(Environment.NewLine, lines.ToArray());
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
