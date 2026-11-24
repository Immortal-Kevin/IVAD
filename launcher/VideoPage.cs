using System;
using System.Collections.Generic;
using System.Drawing;
using System.IO;
using System.Windows.Forms;


internal sealed partial class TrainerForm
{
    private readonly ComboBox videoModel = Views.Choice("验证模型", ModelLabels);
    private readonly ComboBox videoDevice = Views.Choice("推理设备", DeviceLabels);
    private readonly ComboBox weightSource = Views.Choice("权重来源", "当前项目产物", "本地权重");
    private readonly NumericUpDown videoSize = Views.Number("验证输入尺寸", 64, 2048, 384, 32);
    private readonly NumericUpDown confidence = Views.Number("置信度阈值", .01m, 1, .25m, .05m, 2);
    private readonly NumericUpDown sampleRate = Views.Number("每秒验证帧数上限", .1m, 60, 5, .5m, 1);
    private readonly Button videoStart = Views.Button("开始验证", true);
    private readonly Button videoStop = Views.Button("停止验证");
    private readonly Button savePreset = Views.Button("保存项目预设");
    private readonly Label sourceFps = Views.Single("源视频 FPS   —");
    private readonly Label targetFps = Views.Single("采样上限   —");
    private readonly Label measuredFps = Views.Single("实际推理 FPS   —");
    private readonly Label videoStatus = Views.Single("请选择权重与本地测试视频");
    private readonly Label videoCounts = Views.Single("已验证 — 帧    ·    累计检测 — 个");
    private readonly Label videoTimestamp = Views.Single("检测时间戳   ·   —");
    private readonly PictureBox detectionView = Picture("实际检测画面");
    private readonly PictureBox sourceView = Picture("源视频播放");
    private readonly Timer previewTimer = new Timer { Interval = 50 };
    private PathView videoFileView, videoWeightView;
    private string videoFile, videoWeights, previewFolder;
    private DateTime detectionUpdated, sourceUpdated;

    private Control VideoPage()
    {
        var left = Views.ScrollBody();
        Views.Row(left, Views.Text("验证配置", 16, true), 42);
        var chooseWeights = Views.Button("选择");
        var chooseVideo = Views.Button("选择");
        videoFileView = new PathView("测试视频", tooltips, chooseVideo);
        videoWeightView = new PathView("验证权重", tooltips, chooseWeights);
        Views.Field(left, "模型", videoModel);
        Views.Field(left, "权重来源", weightSource);
        Views.Field(left, "检测权重", videoWeightView);
        Views.Field(left, "测试视频", videoFileView);
        Views.Field(left, "推理设备", videoDevice);
        Views.Field(left, "输入尺寸", videoSize);
        Views.Field(left, "置信度阈值", confidence);
        Views.Field(left, "每秒验证帧数上限", sampleRate);
        Views.Row(left, Views.Actions(savePreset), 45);
        Views.Row(left, Views.Actions(videoStart, videoStop), 47);
        var evaluateVal = Views.Button("评估留出 Val");
        var evaluateTest = Views.Button("评估留出 Test");
        Views.Row(left, Views.Actions(evaluateVal, evaluateTest), 45);
        evaluateVal.Click += delegate { EvaluateHoldout("valid"); };
        evaluateTest.Click += delegate { EvaluateHoldout("test"); };
        videoStop.Enabled = false;
        chooseWeights.Click += delegate {
            string value = Pick("选择可信的本地检测权重", WeightFilter(Key(Models, videoModel)));
            if (value == null) return;
            videoWeights = value;
            weightSource.SelectedIndex = 1;
            RefreshVideoWeights();
        };
        chooseVideo.Click += delegate {
            string path = Pick("选择本地测试视频", "视频文件 (*.mp4;*.mov;*.avi;*.wmv)|*.mp4;*.mov;*.avi;*.wmv|所有文件 (*.*)|*.*");
            if (path != null) { videoFile = path; videoFileView.ShowPath(path); }
        };
        videoModel.SelectedIndexChanged += delegate { if (!loading) RefreshVideoWeights(); };
        weightSource.SelectedIndexChanged += delegate { if (!loading) RefreshVideoWeights(); };
        savePreset.Click += delegate {
            StoreVideoFields();
            if (SaveWorkspace(videoStatus)) SetStatus(videoStatus, "已保存 " + ProjectName + " 的验证参数", Views.Good);
        };
        videoStart.Click += delegate { StartVideo(); };
        videoStop.Click += delegate {
            if (!verifier.Active) return;
            videoStop.Enabled = false;
            SetStatus(videoStatus, "正在停止视频验证", Views.Muted);
            Stop(verifier, videoStatus);
        };

        var right = Views.Grid();
        Views.Row(right, Views.Text("视频验证监控", 16, true), 43);
        Views.Wrap(right, videoStatus);
        Views.Row(right, videoStatus, 31);
        var fps = Views.Grid(3);
        for (int i = 0; i < 3; i++) fps.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100f / 3));
        int index = 0;
        foreach (Label item in new[] { sourceFps, targetFps, measuredFps })
        {
            item.BackColor = Views.Canvas;
            item.ForeColor = Views.Blue;
            item.Font = Views.UiFont(10, FontStyle.Bold);
            item.Padding = Views.Pads(6, 0, 0, 0);
            item.Margin = Views.Pads(0, 0, 5, 0);
            fps.Controls.Add(item, index++, 0);
        }
        Views.Row(right, fps, 37);
        Views.Row(right, videoCounts, 32);
        var annotated = Views.Grid();
        Views.Row(annotated, Views.Text("实际检测画面", 10, true), 28);
        Views.Row(annotated, detectionView, -1);
        var original = Views.Grid();
        Views.Row(original, Views.Text("源视频播放", 10, true), 28);
        Views.Row(original, sourceView, -1);
        Views.Row(right, Views.Columns(annotated, original, 74), -1);
        Views.Row(right, videoTimestamp, 32);
        previewTimer.Tick += delegate { ReadPreviews(); };
        return Views.PageColumns(Views.Card(left, true), Views.Card(right), 38);
    }

    private static PictureBox Picture(string name)
    {
        return new PictureBox { AccessibleName = name, Dock = DockStyle.Fill, BackColor = Views.Navy,
            SizeMode = PictureBoxSizeMode.Zoom, Margin = new Padding(0) };
    }

    private void LoadVideoFields()
    {
        SelectKey(Models, videoModel, Project.VideoModel);
        SelectKey(Devices, videoDevice, Project.VideoDevice);
        SetNumber(videoSize, Project.VideoSize, 384);
        SetNumber(confidence, Project.Confidence, .25m);
        SetNumber(sampleRate, Project.SampleRate, 5);
        weightSource.SelectedIndex = Project.LocalVideoWeights ? 1 : 0;
        videoFile = Project.Video;
        videoWeights = Project.VideoWeights;
        videoFileView.ShowPath(videoFile);
        RefreshVideoWeights();
    }

    private void StoreVideoFields()
    {
        Project.VideoModel = Key(Models, videoModel);
        Project.VideoDevice = Key(Devices, videoDevice);
        Project.VideoSize = videoSize.Value;
        Project.Confidence = confidence.Value;
        Project.SampleRate = sampleRate.Value;
        Project.Video = videoFile;
        Project.VideoWeights = videoWeights;
        Project.LocalVideoWeights = weightSource.SelectedIndex == 1;
    }

    private string SelectedVideoWeights()
    {
        return weightSource.SelectedIndex == 0 ? Artifact(Project, Key(Models, videoModel)) : videoWeights;
    }

    private void RefreshVideoWeights()
    {
        bool detection = Key(Models, videoModel) != "anomaly";
        videoDevice.Enabled = videoSize.Enabled = confidence.Enabled = detection;
        videoWeightView.ShowPath(SelectedVideoWeights(),
            weightSource.SelectedIndex == 0 ? "本项目暂无该模型权重" : "尚未选择权重");
    }

    private void StartVideo()
    {
        if (verifier.Active) return;
        string weight = SelectedVideoWeights();
        string model = Key(Models, videoModel);
        if (!File.Exists(videoFile))
        { SetStatus(videoStatus, "视频文件无法访问：请选择存在的本地测试视频", Views.Error); return; }
        if (!File.Exists(weight) || !WeightSuffix(weight, model))
        { SetStatus(videoStatus, "权重加载失败：请选择与模型匹配的本地权重或项目产物", Views.Error); return; }
        if (model != "anomaly" && videoSize.Value % 32 != 0)
        { SetStatus(videoStatus, "推理输入尺寸必须为 32 的倍数", Views.Error); return; }
        StoreVideoFields();
        ClearPreviews();
        previewFolder = Path.Combine(Path.GetTempPath(), "ivad-preview-" + Guid.NewGuid().ToString("N"));
        string stopFile = Path.Combine(previewFolder, "stop");
        var args = new[] { "video", "--model", model, "--device", model == "anomaly" ? "cpu" : Key(Devices, videoDevice),
            "--weights", weight, "--video", videoFile, "--size", model == "anomaly" ? "384" : DecimalArg(videoSize.Value),
            "--confidence", DecimalArg(confidence.Value), "--sample-fps", DecimalArg(sampleRate.Value),
            "--preview", previewFolder, "--stop-file", stopFile };
        sourceFps.Text = "源视频 FPS   —";
        targetFps.Text = "采样上限   " + sampleRate.Value.ToString("0.0");
        measuredFps.Text = "实际推理 FPS   —";
        videoCounts.Text = "已验证 — 帧    ·    累计检测 — 个";
        videoTimestamp.Text = "检测时间戳   ·   —";
        string failure = null;
        string hardware = "";
        string project = ProjectName;
        bool completed = false;
        SetStatus(videoStatus, "正在探测源视频并解码首帧", Views.Blue);
        try
        {
            Directory.CreateDirectory(previewFolder);
            verifier.Start(args, delegate { }, message => {
                string kind = Workspace.Value(message, "kind");
                if (kind == "stage")
                    SetStatus(videoStatus, project + "  ·  " + Workspace.Value(message, "value") + hardware, Views.Blue);
                else if (kind == "device") hardware = "  ·  " + Workspace.Value(message, "hardware");
                else if (kind == "video_probe")
                {
                    sourceFps.Text = String.Format("源视频 FPS   {0:0.0}", Workspace.Number(message, "source_fps"));
                    tooltips.SetToolTip(sourceFps, String.Format("{0} · {1}×{2} · {3}", Workspace.Value(message, "backend"),
                        Workspace.Value(message, "width"), Workspace.Value(message, "height"), Workspace.Value(message, "codec_fourcc")));
                    ReadPreviews();
                }
                else if (kind == "video" || kind == "video_result")
                {
                    ShowVideoMetrics(message);
                    if (kind == "video_result") completed = true;
                }
                else if (kind == "error") failure = Workspace.Value(message, "value");
            }, (code, cancelled) => {
                previewTimer.Stop();
                ReadPreviews();
                videoStart.Enabled = true;
                videoStop.Enabled = false;
                if (cancelled) SetStatus(videoStatus, project + "  ·  已停止验证", Views.Muted);
                else if (code == 0 && completed) SetStatus(videoStatus, project + "  ·  视频验证完成" + hardware, Views.Good);
                else SetStatus(videoStatus, "视频验证失败：" + (failure ?? "进程退出 " + code), Views.Error);
            }, stopFile);
            videoStart.Enabled = false;
            videoStop.Enabled = true;
            previewTimer.Start();
        }
        catch (Exception error) { SetStatus(videoStatus, "无法启动视频验证：" + error.Message, Views.Error); }
    }

    private void EvaluateHoldout(string side)
    {
        if (verifier.Active) return;
        string model = Key(Models, videoModel);
        string chosen = SelectedVideoWeights();
        string artifact = Artifact(Project, model);
        if (model == "anomaly" || !File.Exists(chosen) || !WeightSuffix(chosen, model) || artifact == null || !File.Exists(Project.Ids))
        { SetStatus(videoStatus, "请先完成有框检测训练，并选择检测权重和固定置信度阈值", Views.Error); return; }
        var directory = new DirectoryInfo(Path.GetDirectoryName(artifact));
        string manifest = null;
        for (int depth = 0; depth < 4 && directory != null; depth++, directory = directory.Parent)
        {
            string path = Path.Combine(directory.FullName, "split-manifest.json");
            if (File.Exists(path)) { manifest = path; break; }
        }
        if (manifest == null) { SetStatus(videoStatus, "本项目权重没有关联三套拆分清单", Views.Error); return; }
        string label = side == "test" ? "Test" : "Val";
        var args = new[] { "evaluate", "--ids", Project.Ids, "--manifest", manifest, "--evaluation-set", side,
            "--model", model, "--device", Key(Devices, videoDevice), "--weights", chosen,
            "--size", DecimalArg(videoSize.Value), "--confidence", DecimalArg(confidence.Value) };
        string failure = null, summary = null, report = null;
        try
        {
            verifier.Start(args, delegate { }, message => {
                string kind = Workspace.Value(message, "kind");
                if (kind == "evaluation")
                {
                    string map = Workspace.Value(message, "map"), recall = Workspace.Value(message, "recall");
                    summary = label + " · mAP " + (map == "" ? "不可计算" : map) + " · 召回 " +
                        (recall == "" ? "不可计算" : recall) + " · 正常误报框 " + Workspace.Value(message, "false_positive_boxes");
                    report = Workspace.Value(message, "path");
                }
                else if (kind == "error") failure = Workspace.Value(message, "value");
            }, (code, cancelled) => {
                videoStart.Enabled = true;
                videoStop.Enabled = false;
                bool ok = code == 0 && summary != null;
                SetStatus(videoStatus, cancelled ? "评估已取消" : ok ? summary : "评估失败 · " + (failure ?? "退出 " + code),
                    cancelled ? Views.Muted : ok ? Views.Good : Views.Error);
                if (ok) tooltips.SetToolTip(videoStatus, summary + Environment.NewLine + report);
            });
            videoStart.Enabled = false;
            videoStop.Enabled = true;
            SetStatus(videoStatus, "正在使用已选权重及阈值评估留出 " + label, Views.Blue);
        }
        catch (Exception error) { SetStatus(videoStatus, "无法启动评估 · " + error.Message, Views.Error); }
    }

    private void ShowVideoMetrics(Dictionary<string, object> metrics)
    {
        sourceFps.Text = String.Format("源视频 FPS   {0:0.0}", Workspace.Number(metrics, "source_fps"));
        targetFps.Text = String.Format("采样上限   {0:0.0}", Workspace.Number(metrics, "limit"));
        measuredFps.Text = String.IsNullOrEmpty(Workspace.Value(metrics, "actual_fps")) ? "实际推理 FPS   暂无" :
            String.Format("实际推理 FPS   {0:0.00}", Workspace.Number(metrics, "actual_fps"));
        videoCounts.Text = String.Format("已验证 {0} 帧    ·    累计检测 {1} 个    ·    解码 {2} 帧",
            Workspace.Number(metrics, "processed"), Workspace.Number(metrics, "detections"),
            Workspace.Number(metrics, "decoded"));
        double timestamp = Workspace.Number(metrics, "timestamp");
        if (timestamp >= 0) videoTimestamp.Text = String.Format("检测时间戳   ·   {0:0.000} s", timestamp);
    }

    private void ReadPreviews()
    {
        if (previewFolder == null) return;
        ReadPreview(detectionView, Path.Combine(previewFolder, "detected.jpg"), ref detectionUpdated);
        ReadPreview(sourceView, Path.Combine(previewFolder, "source.jpg"), ref sourceUpdated);
    }

    private static void ReadPreview(PictureBox panel, string path, ref DateTime old)
    {
        try
        {
            var stamp = File.GetLastWriteTimeUtc(path);
            if (stamp <= old || !File.Exists(path)) return;
            using (var input = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            using (var decoded = Image.FromStream(input))
            {
                var image = new Bitmap(decoded);
                var previous = panel.Image;
                panel.Image = image;
                if (previous != null) previous.Dispose();
            }
            old = stamp;
        }
        catch (IOException) { }
        catch (ArgumentException) { }
    }

    private void ClearPreviews()
    {
        foreach (var panel in new[] { sourceView, detectionView })
        {
            if (panel.Image == null) continue;
            panel.Image.Dispose();
            panel.Image = null;
        }
        sourceUpdated = detectionUpdated = DateTime.MinValue;
        if (previewFolder == null || !Directory.Exists(previewFolder)) return;
        try
        {
            foreach (string name in new[] { "source.jpg", "detected.jpg", "source.tmp", "detected.tmp", "stop" })
                File.Delete(Path.Combine(previewFolder, name));
            Directory.Delete(previewFolder);
        }
        catch (IOException) { }
        catch (UnauthorizedAccessException) { }
    }
}
