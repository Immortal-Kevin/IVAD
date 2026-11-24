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
    private static readonly string[] Models = { "yolo", "rf", "anomaly" };
    private static readonly string[] Devices = { "cpu", "xpu", "cuda" };
    private static readonly string[] ModelLabels = { "有框目标检测 · YOLOv8n", "有框目标检测 · RF-DETR Nano", "正常样本异常检测" };
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
    private readonly ListView sourceList = new ListView { Dock = DockStyle.Fill, View = View.Details,
        CheckBoxes = true, FullRowSelect = true, AccessibleName = "源视频",
        HeaderStyle = ColumnHeaderStyle.Nonclickable, BorderStyle = BorderStyle.FixedSingle };
    private const int PurposeColumn = 4;
    private const string TestOnly = "test_only";
    private readonly Label sourceTotals = Views.Single("");
    private readonly Button batchTest = Views.Button("勾选项设为仅测试");
    private readonly Button batchAuto = Views.Button("勾选项参与自动拆分");
    private readonly Button chooseIds = Views.Button("导入 IDS", true);
    private readonly Button recheckIds = Views.Button("重新校验");
    private readonly Button goTrain = Views.Button("进入项目训练", true);
    private PathView idsPath;
    private string candidate;
    private bool loading;
    private bool loadingSources;
    private int page;
    private ProjectSettings Project { get { return workspace.Data.Projects[ProjectName]; } }
    private string ProjectName { get { return workspace.Data.Current; } }

    internal TrainerForm()
    {
        SuspendLayout();
        importer = new WorkerJob(this);
        trainer = new WorkerJob(this);
        verifier = new WorkerJob(this);
        Text = "IVAD Open Trainer v0.2.9";
        Font = Views.UiFont(10);
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
        var bottom = Views.Text("本地工作区   ·   v0.2.9", 9);
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
        importSummary.Font = Views.UiFont(12, FontStyle.Bold);
        Views.Wrap(right, importSummary);
        Views.Row(right, importSummary, 41);
        importDetail.ForeColor = Views.Muted;
        Views.Wrap(right, importDetail);
        Views.Row(right, importDetail, 35);
        Views.Row(right, Views.Text("源视频", 12, true), 31);
        sourceList.Columns.Add("文件名", Views.Px(235));
        sourceList.Columns.Add("总图数", Views.Px(78));
        sourceList.Columns.Add("正例图数", Views.Px(88));
        sourceList.Columns.Add("有效框数", Views.Px(88));
        sourceList.Columns.Add("用途 ▾", Views.Px(125));
        sourceList.Resize += delegate {
            int nameWidth = sourceList.ClientSize.Width - Views.Scale(385, sourceList.DeviceDpi);
            sourceList.Columns[0].Width = Math.Max(Views.Scale(112, sourceList.DeviceDpi), nameWidth);
        };
        sourceList.ItemChecked += delegate(object sender, ItemCheckedEventArgs e) {
            if (loadingSources) return;
            string id = (string)e.Item.Tag;
            Project.SourceVideos.Remove(id);
            if (e.Item.Checked)
            {
                ConfirmSource(id);
                Project.SourceVideos.Add(id);
            }
            e.Item.SubItems[PurposeColumn].Text = PurposeText(id);
            RefreshSourceActions();
            SaveWorkspace(importState);
        };
        var purposeMenu = new ContextMenuStrip();
        ListViewItem editingSource = null;
        purposeMenu.Items.Add("参与自动拆分", null, delegate { if (editingSource != null) SetPurposes(new[] { editingSource }, false); });
        purposeMenu.Items.Add("仅测试", null, delegate { if (editingSource != null) SetPurposes(new[] { editingSource }, true); });
        sourceList.MouseClick += delegate(object sender, MouseEventArgs e) {
            var hit = sourceList.HitTest(e.Location);
            if (hit.Item == null || (e.Button != MouseButtons.Right && hit.SubItem != hit.Item.SubItems[PurposeColumn])) return;
            editingSource = hit.Item;
            purposeMenu.Show(sourceList, e.Location);
        };
        sourceList.KeyDown += delegate(object sender, KeyEventArgs e) {
            if (e.KeyCode != Keys.F2 || sourceList.FocusedItem == null) return;
            editingSource = sourceList.FocusedItem;
            purposeMenu.Show(sourceList, editingSource.SubItems[PurposeColumn].Bounds.Location);
            e.Handled = true;
        };
        batchTest.Click += delegate { SetPurposes(sourceList.CheckedItems, true); };
        batchAuto.Click += delegate { SetPurposes(sourceList.CheckedItems, false); };
        Views.Row(right, sourceList, 145);
        Views.Row(right, Views.Actions(batchTest, batchAuto), 44);
        Views.Wrap(right, sourceTotals);
        Views.Row(right, sourceTotals, 57);
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
        chooseIds.Enabled = projectChoice.Enabled = !importer.Active;
        recheckIds.Enabled = !importer.Active && !String.IsNullOrEmpty(candidate);
        boundIds.ShowPath(ready ? Project.Ids : null, "尚无已校验 IDS");
        trainProject.Text = ProjectName;
        classList.Items.Clear();
        RefreshSources(data);
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

    private void RefreshSources(Dictionary<string, object> data)
    {
        loadingSources = true;
        sourceList.BeginUpdate();
        try
        {
            sourceList.Items.Clear();
            var videos = data == null ? null : data["videos"] as IList;
            if (videos == null) return;
            foreach (var item in videos)
            {
                var video = item as Dictionary<string, object>;
                string id = Workspace.Value(video, "id");
                var row = new ListViewItem(new[] { Workspace.Value(video, "name"), Workspace.Value(video, "images"),
                    Workspace.Value(video, "positive"), Workspace.Value(video, "boxes"), PurposeText(id) }) { Tag = id };
                sourceList.Items.Add(row);
                row.Checked = Project.SourceVideos.Contains(id) && Project.KnownSourceVideos.Contains(id);
            }
        }
        finally
        {
            sourceList.EndUpdate();
            loadingSources = false;
            RefreshSourceActions();
        }
    }

    private List<string> CheckedSources()
    {
        var selected = new List<string>();
        foreach (ListViewItem item in sourceList.CheckedItems) selected.Add((string)item.Tag);
        return selected;
    }

    private bool IsTestOnly(string id)
    {
        string purpose;
        return Project.SourcePurposes != null && Project.SourcePurposes.TryGetValue(id, out purpose) && purpose == TestOnly;
    }

    private string PurposeText(string id)
    {
        if (Project.KnownSourceVideos == null || !Project.KnownSourceVideos.Contains(id)) return "待确认";
        return IsTestOnly(id) ? "仅测试" : "参与自动拆分";
    }

    private void ConfirmSource(string id)
    {
        if (!Project.KnownSourceVideos.Contains(id)) Project.KnownSourceVideos.Add(id);
    }

    private void SetPurposes(IEnumerable rows, bool testOnly)
    {
        foreach (ListViewItem row in rows)
        {
            string id = (string)row.Tag;
            ConfirmSource(id);
            if (testOnly) Project.SourcePurposes[id] = TestOnly;
            else Project.SourcePurposes.Remove(id);
            row.SubItems[PurposeColumn].Text = PurposeText(id);
        }
        RefreshSourceActions();
        SaveWorkspace(importState);
    }

    private void RefreshSourceActions()
    {
        bool ready = verified.ContainsKey(ProjectName) && !importer.Active;
        sourceList.Enabled = ready && !trainer.Active;
        goTrain.Enabled = ready && sourceList.CheckedItems.Count != 0;
        batchTest.Enabled = batchAuto.Enabled = goTrain.Enabled && !trainer.Active;
        var current = new HashSet<string>();
        int autoImages = 0, autoPositive = 0, testImages = 0, testPositive = 0, autoSources = 0, pending = 0;
        foreach (ListViewItem row in sourceList.Items)
        {
            string id = (string)row.Tag;
            current.Add(id);
            if (!Project.KnownSourceVideos.Contains(id)) pending++;
            if (!row.Checked) continue;
            int images = Int32.Parse(row.SubItems[1].Text, CultureInfo.InvariantCulture);
            int positive = Int32.Parse(row.SubItems[2].Text, CultureInfo.InvariantCulture);
            if (IsTestOnly(id)) { testImages += images; testPositive += positive; }
            else { autoImages += images; autoPositive += positive; autoSources++; }
        }
        int missing = ready ? Project.KnownSourceVideos.FindAll(id => !current.Contains(id)).Count : 0;
        sourceTotals.Text = !ready ? "" : String.Format("自动拆分 {0} 图 / {1} 正例   ·   仅测试 {2} 图 / {3} 正例",
            autoImages, autoPositive, testImages, testPositive) + (pending + missing == 0 ? "" :
            String.Format("\n待确认：新源 {0} 个，当前 IDS 无法匹配的旧源 {1} 个", pending, missing));
        trainStart.Enabled = planStart.Enabled = ready && autoSources > 0 && !trainer.Active;
        sourceGate.Text = goTrain.Enabled && autoSources == 0 ? "只有仅测试源，请勾选至少一个参与自动拆分的源视频。" : "";
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
                    var settings = workspace.Data.Projects[project];
                    InitializeSources(settings, path, (IList)data["videos"]);
                    settings.Ids = path;
                }
                RefreshImport();
                if (code == 0 && data != null) SaveWorkspace(importState);
                else SetStatus(importState, "校验失败：" + (failure ?? "读取进程退出 " + code), Views.Error);
            });
            RefreshImport();
        }
        catch (Exception error) { SetStatus(importState, "无法启动校验：" + error.Message, Views.Error); }
    }

    private static void InitializeSources(ProjectSettings settings, string path, IList videos)
    {
        if (settings.SourcePurposes == null) settings.SourcePurposes = new Dictionary<string, string>();
        if (settings.KnownSourceVideos == null)
        {
            bool sameIds = String.IsNullOrEmpty(settings.Ids) || String.Equals(settings.Ids, path, StringComparison.OrdinalIgnoreCase);
            var ids = new List<string>();
            foreach (var video in videos) ids.Add(Workspace.Value(video as Dictionary<string, object>, "id"));
            settings.KnownSourceVideos = sameIds ? ids : new List<string>(settings.SourceVideos ?? new List<string>());
        }
        if (settings.SourceVideos == null) settings.SourceVideos = new List<string>(settings.KnownSourceVideos);
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
        foreach (var job in new[] { importer, trainer, verifier }) Stop(job, importState, true);
        previewTimer.Stop();
        ClearPreviews();
        previewTimer.Dispose();
        base.OnFormClosing(args);
    }

    private static void Stop(WorkerJob job, Label status, bool force = false)
    {
        try { job.Stop(force); }
        catch (Exception error) { SetStatus(status, "无法停止进程：" + error.Message, Views.Error); }
    }
}
