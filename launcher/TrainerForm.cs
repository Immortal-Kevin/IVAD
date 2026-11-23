using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Windows.Forms;


internal sealed partial class TrainerForm : Form
{
    private static readonly string[] PageNames = { "IDS 选取与导入", "项目训练", "训练视频验证" };
    private static readonly string[] Models = { "yolo", "rf" };
    private static readonly string[] Devices = { "cpu", "xpu", "cuda" };
    private static readonly string[] ModelLabels = { "YOLOv8n", "RF-DETR Nano" };
    private static readonly string[] DeviceLabels = { "CPU", "Intel XPU", "NVIDIA CUDA" };
    private readonly Workspace workspace = new Workspace();
    private readonly ToolTip tooltips = new ToolTip { AutoPopDelay = 15000, InitialDelay = 300 };
    private readonly Dictionary<string, Dictionary<string, object>> verified =
        new Dictionary<string, Dictionary<string, object>>();
    private readonly WorkerJob importer;
    private readonly WorkerJob trainer;
    private readonly WorkerJob verifier;
    private readonly Panel pages = new Panel { Dock = DockStyle.Fill, Margin = new Padding(0) };
    private readonly Label context = Views.Single("");
    private readonly Control[] screens = new Control[3];
    private readonly Button[] nav = new Button[3];
    private readonly Label importState = Views.Single("请选择完整 IDS 包");
    private readonly Label importSummary = Views.Single("");
    private readonly Label importDetail = Views.Single("");
    private readonly ComboBox projectChoice = Views.Choice("项目预设", Workspace.Preset, Workspace.Custom);
    private readonly ListView classList = new ListView { Dock = DockStyle.Fill, View = View.Details,
        FullRowSelect = true, HeaderStyle = ColumnHeaderStyle.Nonclickable, BorderStyle = BorderStyle.FixedSingle };
    private readonly Button chooseIds = Views.Button("导入 IDS", true);
    private readonly Button recheckIds = Views.Button("重新校验");
    private readonly Button goTrain = Views.Button("进入项目训练", true);
    private PathView idsPath;
    private string candidate;
    private bool loading;
    private int page;
    private ProjectSettings Project { get { return workspace.Data.Projects[ProjectName]; } }
    private string ProjectName { get { return workspace.Data.Current; } }

    internal TrainerForm()
    {
        SuspendLayout();
        importer = new WorkerJob(this);
        trainer = new WorkerJob(this);
        verifier = new WorkerJob(this);
        Text = "IVAD Open Trainer v0.2.1";
        Font = new Font("Microsoft YaHei UI", 10);
        AutoScaleMode = AutoScaleMode.None;
        StartPosition = FormStartPosition.Manual;
        FitInitialWindow(Views.StartupScreen.WorkingArea);
        BackColor = Views.Canvas;
        ForeColor = Views.Ink;

        var layout = Views.Grid(2);
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        Controls.Add(layout);
        layout.Controls.Add(Sidebar(), 0, 0);

        var main = Views.Grid();
        main.Padding = Views.Pads(18, 14, 18, 16);
        var head = Views.ScrollBody();
        head.Dock = DockStyle.Fill;
        var productTitle = Views.Text("IVAD Open Trainer", 24, true);
        Views.Wrap(head, productTitle);
        Views.Row(head, productTitle);
        context.ForeColor = Views.Muted;
        Views.Wrap(head, context);
        Views.Row(head, context, 28);
        Views.Row(main, head);
        Views.Row(main, pages, -1);
        layout.Controls.Add(main, 1, 0);

        screens[0] = ImportPage();
        screens[1] = TrainingPage();
        screens[2] = VideoPage();
        foreach (var screen in screens) pages.Controls.Add(screen);
        LoadProject();
        Navigate(0);
        ResumeLayout(true);
        Shown += delegate {
            if (!String.IsNullOrEmpty(workspace.LoadError)) SetStatus(importState, workspace.LoadError, Views.Error);
            else if (!String.IsNullOrEmpty(Project.Ids)) Import(Project.Ids);
        };
    }

    protected override void OnLoad(EventArgs e)
    {
        // Use the window's DPI after its handle is on the launch monitor.
        // Before then WinForms can measure against the primary display.
        SuspendLayout();
        AutoScaleDimensions = new SizeF(DeviceDpi, DeviceDpi);
        AutoScaleMode = AutoScaleMode.Dpi;
        ResumeLayout(true);
        base.OnLoad(e);
    }

    private void FitInitialWindow(Rectangle work)
    {
        SetWindowMinimum(work, Views.StartupDpi);
        int width = Math.Min(Views.Px(1170), Math.Max(MinimumSize.Width, work.Width - Views.Px(28)));
        int height = Math.Min(Views.Px(740), Math.Max(MinimumSize.Height, work.Height - Views.Px(24)));
        Bounds = new Rectangle(work.Left + (work.Width - width) / 2, work.Top + (work.Height - height) / 2,
                               width, height);
    }

    private void SetWindowMinimum(Rectangle work, int dpi)
    {
        MinimumSize = new Size(Math.Min(Views.Scale(610, dpi), work.Width),
                               Math.Min(Views.Scale(360, dpi), work.Height));
    }

    protected override void OnDpiChanged(DpiChangedEventArgs e)
    {
        SetWindowMinimum(Screen.FromRectangle(e.SuggestedRectangle).WorkingArea, e.DeviceDpiNew);
        base.OnDpiChanged(e);
    }

    private Control Sidebar()
    {
        var grid = Views.Grid();
        grid.BackColor = Views.Navy;
        grid.AutoSize = true;
        grid.MinimumSize = new Size(Views.Px(174), 0);
        grid.Padding = Views.Pads(12, 16, 12, 10);
        var brand = Views.Text("IVAD", 28, true);
        brand.ForeColor = Color.White;
        brand.Margin = Views.Pads(7, 2, 0, 0);
        var subtitle = Views.Text("OPEN TRAINER", 10);
        subtitle.ForeColor = Color.FromArgb(166, 200, 229);
        subtitle.Margin = Views.Pads(8, 0, 0, 6);
        Views.Row(grid, brand);
        Views.Row(grid, subtitle, 35);
        var directory = Views.Text("软件目录", 9);
        directory.ForeColor = subtitle.ForeColor;
        directory.Margin = Views.Pads(8, 0, 0, 0);
        Views.Row(grid, directory, 28);
        for (int i = 0; i < nav.Length; i++)
        {
            int index = i;
            var button = Views.Button(PageNames[i]);
            button.Dock = DockStyle.Fill;
            button.TextAlign = ContentAlignment.MiddleLeft;
            button.Padding = Views.Pads(8, 2, 8, 2);
            button.Margin = Views.Pads(0, 2, 0, 4);
            button.ForeColor = Color.White;
            button.FlatAppearance.BorderSize = 0;
            button.FlatAppearance.MouseOverBackColor = Color.FromArgb(38, 78, 117);
            button.Click += delegate { Navigate(index); };
            Views.Row(grid, button, 42);
            nav[i] = button;
        }
        Views.Row(grid, new Panel(), -1);
        var bottom = Views.Text("本地工作区   ·   v0.2.1", 9);
        bottom.ForeColor = subtitle.ForeColor;
        bottom.Margin = Views.Pads(7, 0, 0, 0);
        Views.Row(grid, bottom, 24);
        return grid;
    }

    private void Navigate(int index)
    {
        page = index;
        for (int i = 0; i < screens.Length; i++)
        {
            nav[i].BackColor = i == index ? Views.Blue : Views.Navy;
            screens[i].Visible = i == index;
        }
        screens[index].BringToFront();
        context.Text = ProjectName + "  /  " + PageNames[index];
        if (index == 1) RefreshArtifacts();
    }

    private Control ImportPage()
    {
        var left = Views.ScrollBody();
        Views.Row(left, Views.Text("项目与 IDS", 16, true), 42);
        Views.Field(left, "项目预设", projectChoice);
        idsPath = new PathView("IDS 文件", tooltips);
        Views.Field(left, "IDS 文件", idsPath);
        Views.Row(left, Views.Actions(chooseIds, recheckIds), 48);
        Views.Wrap(left, importState);
        Views.Row(left, importState, 38);
        Views.Row(left, Views.Actions(goTrain), 48);
        projectChoice.SelectedIndexChanged += delegate {
            if (loading) return;
            StoreProject();
            workspace.Data.Current = Convert.ToString(projectChoice.SelectedItem);
            LoadProject();
            SaveWorkspace(importState);
            if (!verified.ContainsKey(ProjectName) && !String.IsNullOrEmpty(Project.Ids)) Import(Project.Ids);
        };
        chooseIds.Click += delegate {
            string path = Pick("选择 IDS 完整包", "IVAD IDS 包 (*.ids)|*.ids");
            if (path != null) Import(path);
        };
        recheckIds.Click += delegate {
            if (!String.IsNullOrEmpty(candidate)) Import(candidate);
        };
        goTrain.Click += delegate { Navigate(1); };

        var right = Views.Grid();
        Views.Row(right, Views.Text("导入统计", 16, true), 43);
        importSummary.ForeColor = Views.Blue;
        importSummary.Font = new Font(Font.FontFamily, 12, FontStyle.Bold);
        Views.Wrap(right, importSummary);
        Views.Row(right, importSummary, 41);
        importDetail.ForeColor = Views.Muted;
        Views.Wrap(right, importDetail);
        Views.Row(right, importDetail, 35);
        classList.Columns.Add("类别", Views.Px(215));
        classList.Columns.Add("有效标注", Views.Px(104));
        classList.Columns.Add("IDS 类别 ID", Views.Px(285));
        classList.Resize += delegate {
            int w = classList.ClientSize.Width;
            int dpi = classList.DeviceDpi;
            if (w > Views.Scale(48, dpi))
            {
                classList.Columns[0].Width = w * 36 / 100;
                classList.Columns[1].Width = Math.Max(Views.Scale(86, dpi), w * 17 / 100);
                classList.Columns[2].Width = Math.Max(Views.Scale(95, dpi),
                    w - classList.Columns[0].Width - classList.Columns[1].Width - Views.Scale(6, dpi));
            }
        };
        Views.Row(right, classList, -1);
        return Views.PageColumns(Views.Card(left, true), Views.Card(right), 38);
    }

    private void LoadProject()
    {
        loading = true;
        projectChoice.SelectedItem = ProjectName;
        candidate = Project.Ids;
        idsPath.ShowPath(candidate, "尚未绑定 IDS");
        SetStatus(importState, String.IsNullOrEmpty(candidate) ? "请选择完整 IDS 包" : "等待校验已绑定文件", Views.Muted);
        LoadTrainingFields();
        LoadVideoFields();
        RefreshImport();
        RefreshArtifacts();
        context.Text = ProjectName + "  /  " + PageNames[page];
        loading = false;
    }

    private void StoreProject()
    {
        StoreTrainingFields();
        StoreVideoFields();
    }

    private bool SaveWorkspace(Label state)
    {
        try { workspace.Save(); return true; }
        catch (Exception error)
        {
            SetStatus(state, "保存本地配置失败：" + error.Message, Views.Error);
            return false;
        }
    }

    private void RefreshImport()
    {
        Dictionary<string, object> data;
        bool ready = verified.TryGetValue(ProjectName, out data);
        goTrain.Enabled = ready && !importer.Active;
        chooseIds.Enabled = projectChoice.Enabled = !importer.Active;
        recheckIds.Enabled = !importer.Active && !String.IsNullOrEmpty(candidate);
        trainStart.Enabled = ready && !trainer.Active && !importer.Active;
        boundIds.ShowPath(ready ? Project.Ids : null, "尚无已校验 IDS");
        trainProject.Text = ProjectName;
        classList.Items.Clear();
        if (!ready)
        {
            importSummary.Text = "图像 —      类别 —      标注 —";
            importDetail.Text = "校验完整包后显示统计";
            return;
        }
        var classes = data["classes"] as IList ?? new object[0];
        var states = Workspace.Object(data, "states");
        importSummary.Text = String.Format("{0} 张图像     {1} 个类别     {2} 条标注",
            Workspace.Value(data, "images"), classes.Count, Workspace.Value(data, "annotations"));
        importDetail.Text = String.Format("正常 {0}   ·   异常 {1}   ·   可训练 {2}",
            Workspace.Number(states, "normal"), Workspace.Number(states, "abnormal"), Workspace.Value(data, "eligible"));
        foreach (object item in classes)
        {
            var row = item as Dictionary<string, object>;
            classList.Items.Add(new ListViewItem(new[] { Workspace.Value(row, "name"),
                Workspace.Value(row, "annotations"), Workspace.Value(row, "id") }));
        }
        SetStatus(importState, "校验通过  ·  IDS 完整包", Views.Good);
    }

    private void Import(string path)
    {
        if (importer.Active) return;
        string project = ProjectName;
        candidate = path;
        verified.Remove(project);
        idsPath.ShowPath(path);
        RefreshImport();
        SetStatus(importState, "正在校验清单、资产和标注…", Views.Blue);
        Dictionary<string, object> data = null;
        string failure = null;
        try
        {
            importer.Start(new[] { "inspect", "--ids", path }, delegate { }, message => {
                if (Workspace.Value(message, "kind") == "ids") data = Workspace.Object(message, "summary");
                if (Workspace.Value(message, "kind") == "error") failure = Workspace.Value(message, "value");
            }, (code, cancelled) => {
                if (code == 0 && data != null)
                {
                    verified[project] = data;
                    workspace.Data.Projects[project].Ids = path;
                }
                RefreshImport();
                if (code == 0 && data != null) SaveWorkspace(importState);
                else SetStatus(importState, "校验失败：" + (failure ?? "读取进程退出 " + code), Views.Error);
            });
            RefreshImport();
        }
        catch (Exception error) { SetStatus(importState, "无法启动校验：" + error.Message, Views.Error); }
    }

    private static void SetStatus(Label label, string message, Color color)
    {
        label.Text = message;
        label.ForeColor = color;
        var form = label.FindForm() as TrainerForm;
        if (form != null) form.tooltips.SetToolTip(label, message);
    }

    private string Pick(string title, string filter)
    {
        using (var dialog = new OpenFileDialog { Title = title, Filter = filter, CheckFileExists = true })
            return dialog.ShowDialog(this) == DialogResult.OK ? dialog.FileName : null;
    }

    private static string DecimalArg(decimal value) { return value.ToString(CultureInfo.InvariantCulture); }
    private static string Key(string[] keys, ComboBox choice) { return keys[Math.Max(0, choice.SelectedIndex)]; }
    private static void SelectKey(string[] keys, ComboBox choice, string value)
    { choice.SelectedIndex = Math.Max(0, Array.IndexOf(keys, value)); }
    private static void SetNumber(NumericUpDown field, decimal value, decimal fallback)
    { field.Value = value >= field.Minimum && value <= field.Maximum ? value : fallback; }
    private static string Artifact(ProjectSettings project, string model)
    {
        string path;
        return project.Artifacts != null && project.Artifacts.TryGetValue(model, out path) && File.Exists(path) ?
            path : null;
    }

    protected override void OnFormClosing(FormClosingEventArgs args)
    {
        StoreProject();
        SaveWorkspace(importState);
        foreach (var job in new[] { importer, trainer, verifier }) Stop(job, importState);
        previewTimer.Stop();
        ClearPreviews();
        previewTimer.Dispose();
        base.OnFormClosing(args);
    }

    private static void Stop(WorkerJob job, Label status)
    {
        try { job.Stop(); }
        catch (Exception error) { SetStatus(status, "无法停止进程：" + error.Message, Views.Error); }
    }
}
