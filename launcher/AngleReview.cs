using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Windows.Forms;

internal sealed partial class TrainerForm
{
    private void OpenAngleReview()
    {
        if (verifier.Active)
        {
            SetStatus(videoStatus, "请先停止当前视频验证，再打开两点测角", Views.Muted);
            return;
        }
        if (!File.Exists(videoFile))
        {
            SetStatus(videoStatus, "请先选择 Day 或 Night 原片", Views.Error);
            return;
        }
        using (var review = new AngleReview(videoFile, Picture("依次点选刮板左、右连接点")))
            review.ShowDialog(this);
    }
}

internal sealed class AngleReview : Form
{
    private readonly string video;
    private readonly PictureBox picture;
    private readonly WorkerJob job;
    private readonly Timer timer = new Timer();
    private readonly TrackBar timeline = new TrackBar { Dock = DockStyle.Fill, TickStyle = TickStyle.None };
    private readonly NumericUpDown seek = new NumericUpDown { Width = 110, MinimumSize = new Size(110, 24),
        Minimum = 0, Maximum = 86400, DecimalPlaces = 3, TextAlign = HorizontalAlignment.Right };
    private readonly Button play = Views.Button("播放");
    private readonly Label result = Views.Single("");
    private readonly Label state = Views.Single("");
    private readonly string cache = Path.Combine(Path.GetTempPath(), "ivad-angle-" + Guid.NewGuid().ToString("N"));
    private readonly List<PointF[]> reference = new List<PointF[]>();
    private readonly HashSet<int> referenceFrames = new HashSet<int>();
    private string profile, loadedProfile;
    private double[] times = new double[0], toPlane, toPixel;
    private int width, height, start, total;
    private double fps;
    private PointF? left, right;
    private string finding;
    private bool loading, closePending;
    private const float BandTop = 240f / 544, BandBottom = 305f / 544;

    internal AngleReview(string video, PictureBox picture)
    {
        this.video = video;
        this.picture = picture;
        job = new WorkerJob(this);
        Text = Path.GetFileName(video) + " · 203 离线两点测角";
        AutoScaleMode = AutoScaleMode.None;
        Font = Views.UiFont(10);
        StartPosition = FormStartPosition.CenterParent;
        Rectangle work = Screen.FromPoint(Cursor.Position).WorkingArea;
        Size = new Size(Math.Min(1050, work.Width), Math.Min(725, work.Height));
        MinimumSize = new Size(Math.Min(830, work.Width), Math.Min(560, work.Height));
        WindowState = FormWindowState.Maximized;
        BackColor = Views.Canvas;
        profile = Environment.GetEnvironmentVariable("IVAD_ANGLE_PROFILE");
        if (!File.Exists(profile)) profile = null;

        var go = Views.Button("定位");
        var prev = Views.Button("上一帧");
        var next = Views.Button("下一帧");
        var choose = Views.Button("测角配置");
        var add = Views.Button("加入正常参考");
        var clear = Views.Button("清除点位");
        var invalid = Views.Button("无法测角");
        var fracture = Views.Button("登记疑似断裂");
        var save = Views.Button("保存证据");
        var layout = Views.Grid();
        layout.Padding = Views.Pads(12);
        Views.Row(layout, state, 29);
        Views.Row(layout, picture, -1);
        Views.Row(layout, result, 32);
        Views.Row(layout, timeline, 30);
        Views.Row(layout, Views.Actions(Views.Text("原片秒"), seek, go, play, prev, next, choose), 45);
        Views.Row(layout, Views.Actions(add, clear, invalid, fracture, save), 45);
        Controls.Add(layout);

        go.Click += delegate { LoadClip((double)seek.Value); };
        prev.Click += delegate { MoveFrame(-1); };
        next.Click += delegate { MoveFrame(1); };
        play.Click += delegate
        {
            if (timer.Enabled) StopPlaying();
            else if (times.Length > 0) { play.Text = "暂停"; timer.Start(); }
        };
        timer.Tick += delegate { MoveFrame(1); };
        timeline.ValueChanged += delegate { if (!loading) ShowFrame(); };
        picture.Paint += (sender, e) => DrawOverlay(e.Graphics, DisplayArea());
        picture.MouseClick += PointAt;
        clear.Click += delegate { ResetPoints(); };
        invalid.Click += delegate { Record("无法测角"); };
        fracture.Click += delegate { Record("无法测角 · 疑似断裂（待人工核验）"); };
        add.Click += delegate
        {
            if (!CanMeasure() || !referenceFrames.Add(start + timeline.Value)) return;
            reference.Add(new[] { left.Value, right.Value });
            ResetPoints();
        };
        choose.Click += delegate
        {
            StopPlaying();
            using (var picker = new OpenFileDialog { Filter = "测角配置 (*.json)|*.json", FileName = profile ?? "" })
                if (picker.ShowDialog(this) == DialogResult.OK)
                {
                    profile = picker.FileName;
                    LoadClip((double)seek.Value);
                }
        };
        save.Click += delegate { SaveEvidence(); };
        Shown += delegate { LoadClip(0); };
        FormClosing += (sender, e) =>
        {
            StopPlaying();
            if (job.Active) { closePending = true; e.Cancel = true; job.Stop(true); }
        };
        FormClosed += delegate
        {
            timer.Dispose();
            SwapImage(null);
            if (Directory.Exists(cache))
            {
                foreach (string file in Directory.EnumerateFiles(cache, "*.jpg")) File.Delete(file);
                Directory.Delete(cache);
            }
        };
    }

    private void LoadClip(double seconds, bool keepPlaying = false)
    {
        if (job.Active) return;
        StopPlaying();
        state.Text = "正在定位原片";
        double[] pendingTimes = null;
        string error = null;
        var args = new List<string> { "angle-clip", "--video", video, "--preview", cache,
            "--at", seconds.ToString("R", CultureInfo.InvariantCulture) };
        if (profile != null) args.AddRange(new[] { "--angle-profile", profile });
        try
        {
            job.Start(args.ToArray(), line => { }, message =>
            {
                string kind = Workspace.Value(message, "kind");
                if (kind == "error") error = Workspace.Value(message, "value");
                if (kind != "angle_clip") return;
                start = (int)Workspace.Number(message, "start");
                total = (int)Workspace.Number(message, "total");
                width = (int)Workspace.Number(message, "width");
                height = (int)Workspace.Number(message, "height");
                fps = Workspace.Number(message, "fps");
                pendingTimes = Values(message, "times");
                toPlane = Values(message, "pixel_to_plane");
                toPixel = Values(message, "plane_to_pixel");
                if (profile != loadedProfile)
                {
                    reference.Clear();
                    referenceFrames.Clear();
                    foreach (object pair in Items(message, "reference"))
                    {
                        var points = ((IList)pair).Cast<IList>().Select(p =>
                            new PointF(Convert.ToSingle(p[0]), Convert.ToSingle(p[1]))).ToArray();
                        if (ValidPair(points)) reference.Add(points);
                    }
                    loadedProfile = profile;
                }
            }, (code, cancelled) =>
            {
                if (closePending) { Close(); return; }
                if (code != 0 || pendingTimes == null || pendingTimes.Length == 0)
                {
                    state.Text = "无法载入原片 · " + (error ?? "解码失败");
                    return;
                }
                times = pendingTimes;
                loading = true;
                timeline.Maximum = times.Length - 1;
                timeline.Value = 0;
                seek.Maximum = (decimal)((total - 1) / fps);
                timer.Interval = Math.Max(15, (int)Math.Round(1000 / fps));
                loading = false;
                ShowFrame();
                foreach (string path in Directory.EnumerateFiles(cache, "*.jpg"))
                {
                    int frame;
                    if (Int32.TryParse(Path.GetFileNameWithoutExtension(path), out frame) &&
                        (frame < start || frame >= start + times.Length)) File.Delete(path);
                }
                if (keepPlaying) { play.Text = "暂停"; timer.Start(); }
            });
        }
        catch (Exception ex) { state.Text = "无法启动测角回放 · " + ex.Message; }
    }

    private static IList Items(Dictionary<string, object> data, string key)
    {
        object value;
        return data.TryGetValue(key, out value) ? value as IList ?? new object[0] : new object[0];
    }

    private static double[] Values(Dictionary<string, object> data, string key)
    {
        return Items(data, key).Cast<object>().Select(Convert.ToDouble).ToArray();
    }

    private void StopPlaying() { timer.Stop(); play.Text = "播放"; }

    private void MoveFrame(int step)
    {
        if (times.Length == 0 || job.Active) return;
        int next = timeline.Value + step;
        if (next >= 0 && next < times.Length) timeline.Value = next;
        else
        {
            bool keepPlaying = timer.Enabled;
            StopPlaying();
            int target = start + next;
            if (target >= 0 && target < total) LoadClip(target / fps, keepPlaying);
        }
    }

    private void ShowFrame()
    {
        if (times.Length == 0) return;
        int index = timeline.Value;
        using (var file = Image.FromFile(Path.Combine(cache, (start + index).ToString() + ".jpg")))
            SwapImage(new Bitmap(file));
        seek.Value = Math.Min(seek.Maximum, (decimal)times[index]);
        ResetPoints();
    }

    private void SwapImage(Image image)
    {
        Image old = picture.Image;
        picture.Image = image;
        if (old != null) old.Dispose();
    }

    private void ResetPoints()
    {
        left = right = null;
        finding = null;
        UpdateLabels();
    }

    private void Record(string value)
    {
        StopPlaying();
        left = right = null;
        finding = value;
        UpdateLabels();
    }

    private RectangleF DisplayArea()
    {
        if (picture.Image == null) return RectangleF.Empty;
        float scale = Math.Min((float)picture.Width / width, (float)picture.Height / height);
        return new RectangleF((picture.Width - width * scale) / 2, (picture.Height - height * scale) / 2,
            width * scale, height * scale);
    }

    private void PointAt(object sender, MouseEventArgs e)
    {
        if (job.Active || picture.Image == null) return;
        var area = DisplayArea();
        if (!area.Contains(e.Location)) return;
        StopPlaying();
        finding = null;
        var point = new PointF((e.X - area.X) * width / area.Width, (e.Y - area.Y) * height / area.Height);
        if (left.HasValue && !right.HasValue) right = point;
        else { left = point; right = null; }
        UpdateLabels();
    }

    private bool ValidPair(PointF[] p)
    {
        if (p.Length != 2 || p[0].X < 0 || p[0].X > width * .45 ||
            p[1].X < width * .55 || p[1].X >= width ||
            p.Any(point => point.Y < 0 || point.Y >= height)) return false;
        float y = (p[0].Y + p[1].Y) / 2;
        return y >= height * BandTop && y <= height * BandBottom;
    }

    private bool CanMeasure()
    {
        return left.HasValue && right.HasValue && ValidPair(new[] { left.Value, right.Value }) &&
            !Double.IsNaN(Direction(left.Value, right.Value));
    }

    private static PointF Project(PointF p, double[] matrix)
    {
        if (matrix == null || matrix.Length != 9) return p;
        double w = matrix[6] * p.X + matrix[7] * p.Y + matrix[8];
        if (Math.Abs(w) < 1e-10) return new PointF(Single.NaN, Single.NaN);
        return new PointF((float)((matrix[0] * p.X + matrix[1] * p.Y + matrix[2]) / w),
            (float)((matrix[3] * p.X + matrix[4] * p.Y + matrix[5]) / w));
    }

    private double Direction(PointF a, PointF b)
    {
        a = Project(a, toPlane);
        b = Project(b, toPlane);
        if (a == b) return Double.NaN;
        return Math.Atan2(b.Y - a.Y, b.X - a.X);
    }

    private double Reference()
    {
        double[] sample = reference.Select(p => Direction(p[0], p[1])).Where(a => !Double.IsNaN(a)).ToArray();
        if (sample.Length < 3) return Double.NaN;
        return Math.Atan2(sample.Average(a => Math.Sin(a)), sample.Average(a => Math.Cos(a)));
    }

    private string Caption()
    {
        string mode = toPlane != null && toPlane.Length == 9 ? "平面校正角度" : "图像角度 · 实际 5° 报警未启用";
        if (finding != null) return finding + "  |  " + mode;
        if (!left.HasValue || !right.HasValue) return "无法测角 · 暂停后点可见的左、右连接点  |  " + mode;
        if (!CanMeasure()) return "无法测角 · 点位顺序、测量带或投影不合格  |  " + mode;
        double theta = Direction(left.Value, right.Value);
        double baseline = Reference();
        double delta = Math.Atan2(Math.Sin(theta - baseline), Math.Cos(theta - baseline)) * 180 / Math.PI;
        return String.Format(CultureInfo.InvariantCulture, "{0}  |  实测 {1:+0.00;-0.00;0.00}°  |  {2}", mode,
            theta * 180 / Math.PI, Double.IsNaN(baseline) ? "待建立正常参考（至少 3 个）" :
            String.Format(CultureInfo.InvariantCulture, "偏差 {0:+0.00;-0.00;0.00}°", delta));
    }

    private void UpdateLabels()
    {
        if (times.Length == 0) return;
        state.Text = String.Format(CultureInfo.InvariantCulture, "{0}  |  原片 {1:0.000} s  |  帧 {2}  |  正常参考 {3} 个",
            Path.GetFileName(video), times[timeline.Value], start + timeline.Value, reference.Count);
        result.Text = Caption();
        picture.Invalidate();
    }

    private void DrawOverlay(Graphics g, RectangleF area)
    {
        if (area.IsEmpty) return;
        g.SmoothingMode = SmoothingMode.AntiAlias;
        g.SetClip(area);
        float hi = area.Y + area.Height * BandTop, lo = area.Y + area.Height * BandBottom;
        using (var backdrop = new SolidBrush(Color.FromArgb(22, Color.Gold)))
        using (var band = new Pen(Color.Gold, 1) { DashStyle = DashStyle.Dash })
        using (var measured = new Pen(Color.Turquoise, 3))
        using (var baseline = new Pen(Color.DeepSkyBlue, 2) { DashStyle = DashStyle.Dash })
        {
            g.FillRectangle(backdrop, area.X, hi, area.Width, lo - hi);
            g.DrawLine(band, area.X, hi, area.Right, hi);
            g.DrawLine(band, area.X, lo, area.Right, lo);
            Func<PointF, PointF> map = p => new PointF(area.X + area.Width * p.X / width, area.Y + area.Height * p.Y / height);
            double angle = Reference();
            if (!Double.IsNaN(angle))
            {
                var a = Project(CanMeasure() ? left.Value : new PointF(width * .3f, height * (BandTop + BandBottom) / 2), toPlane);
                var b = Project(CanMeasure() ? right.Value : new PointF(width * .7f, height * (BandTop + BandBottom) / 2), toPlane);
                float cx = (a.X + b.X) / 2, cy = (a.Y + b.Y) / 2;
                double length = Math.Sqrt(Math.Pow(a.X - b.X, 2) + Math.Pow(a.Y - b.Y, 2)) / 2;
                float dx = (float)(Math.Cos(angle) * length), dy = (float)(Math.Sin(angle) * length);
                var p = map(Project(new PointF(cx - dx, cy - dy), toPixel));
                var q = map(Project(new PointF(cx + dx, cy + dy), toPixel));
                if (!Single.IsNaN(p.X) && !Single.IsNaN(q.X)) g.DrawLine(baseline, p, q);
            }
            if (CanMeasure()) g.DrawLine(measured, map(left.Value), map(right.Value));
            foreach (var point in new[] { left, right })
                if (point.HasValue)
                {
                    var p = map(point.Value);
                    g.FillEllipse(Brushes.Turquoise, p.X - 4, p.Y - 4, 8, 8);
                }
        }
        g.ResetClip();
    }

    private void SaveEvidence()
    {
        if (picture.Image == null || job.Active) return;
        StopPlaying();
        using (var picker = new SaveFileDialog { Filter = "测角证据 (*.png)|*.png", FileName =
            Path.GetFileNameWithoutExtension(video) + "-" + (start + timeline.Value) + ".png" })
        {
            if (picker.ShowDialog(this) != DialogResult.OK) return;
            using (var image = new Bitmap(width, height + 54))
            using (var g = Graphics.FromImage(image))
            {
                g.Clear(Views.Navy);
                g.DrawImage(picture.Image, 0, 0, width, height);
                DrawOverlay(g, new RectangleF(0, 0, width, height));
                g.DrawString(state.Text, Font, Brushes.White, 7, height + 4);
                g.DrawString(Caption(), Font, Brushes.White, 7, height + 28);
                image.Save(picker.FileName, ImageFormat.Png);
            }
        }
    }
}
