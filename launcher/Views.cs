using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

internal static class Views
{
    internal static readonly Color Navy = Color.FromArgb(19, 40, 62);
    internal static readonly Color Blue = Color.FromArgb(32, 97, 166);
    internal static readonly Color Canvas = Color.FromArgb(233, 240, 247);
    internal static readonly Color Line = Color.FromArgb(198, 213, 229);
    internal static readonly Color Ink = Color.FromArgb(28, 52, 74);
    internal static readonly Color Muted = Color.FromArgb(77, 102, 128);
    internal static readonly Color Good = Color.FromArgb(17, 110, 87);
    internal static readonly Color Error = Color.FromArgb(166, 48, 52);
    private static Screen startupScreen;
    private static int startupDpi = 96;

    [DllImport("user32.dll")]
    private static extern IntPtr MonitorFromPoint(Point point, uint flags);

    [DllImport("shcore.dll")]
    private static extern int GetDpiForMonitor(IntPtr monitor, int type, out uint x, out uint y);

    internal static Screen StartupScreen
    {
        get
        {
            if (startupScreen == null) Initialize(Screen.FromPoint(Cursor.Position));
            return startupScreen;
        }
    }

    internal static int StartupDpi { get { var screen = StartupScreen; return startupDpi; } }

    internal static void Initialize(Screen screen)
    {
        startupScreen = screen;
        Rectangle bounds = screen.Bounds;
        var point = new Point(bounds.Left + bounds.Width / 2, bounds.Top + bounds.Height / 2);
        uint x, y;
        startupDpi = GetDpiForMonitor(MonitorFromPoint(point, 2), 0, out x, out y) == 0 && x > 0 ? (int)x : 96;
    }

    internal static int Px(int logical) { return Scale(logical, StartupDpi); }
    internal static int Scale(int logical, int dpi) { return (logical * dpi + 48) / 96; }
    internal static Padding Pads(int left, int top, int right, int bottom)
    { return new Padding(Px(left), Px(top), Px(right), Px(bottom)); }
    internal static Padding Pads(int all) { return Pads(all, all, all, all); }

    internal static Label Text(string value, float size = 10, bool bold = false)
    {
        return new Label { Text = value, AutoSize = true, ForeColor = Ink,
            Font = new Font("Microsoft YaHei UI", size, bold ? FontStyle.Bold : FontStyle.Regular),
            Margin = Pads(0, 0, 0, 5), TextAlign = ContentAlignment.MiddleLeft };
    }

    internal static Label Single(string value, int height = 30)
    {
        var label = Text(value);
        label.AutoSize = false;
        label.AutoEllipsis = true;
        label.Height = Px(height);
        label.Dock = DockStyle.Fill;
        return label;
    }

    internal static Button Button(string text, bool primary = false)
    {
        var button = new Button { Text = text, AutoSize = true,
            MinimumSize = new Size(Px(80), Px(32)), FlatStyle = FlatStyle.Flat,
            BackColor = primary ? Blue : Color.White, ForeColor = primary ? Color.White : Ink,
            Padding = Pads(6, 2, 6, 2), Margin = Pads(0, 0, 7, 3),
            Cursor = Cursors.Hand, UseVisualStyleBackColor = false };
        button.FlatAppearance.BorderColor = primary ? Blue : Line;
        return button;
    }

    internal static TableLayoutPanel Grid(int columns = 1)
    {
        var grid = new TableLayoutPanel { Dock = DockStyle.Fill, ColumnCount = columns, Margin = new Padding(0) };
        return grid;
    }

    internal static void Row(TableLayoutPanel grid, Control control, int height = 0)
    {
        int index = grid.RowCount++;
        bool measuredGrid = height > 0 && control is TableLayoutPanel;
        if (height > 0 && !measuredGrid)
            control.MinimumSize = new Size(control.MinimumSize.Width, Math.Max(control.MinimumSize.Height, Px(height)));
        grid.RowStyles.Add(height == -1 ? new RowStyle(SizeType.Percent, 100) :
            measuredGrid ? new RowStyle(SizeType.Absolute, Px(height)) : new RowStyle(SizeType.AutoSize));
        grid.Controls.Add(control, 0, index);
        grid.SetColumnSpan(control, grid.ColumnCount);
    }

    internal static void Wrap(TableLayoutPanel grid, Label label)
    {
        label.AutoSize = true;
        label.Dock = DockStyle.Top;
        grid.ClientSizeChanged += delegate {
            int width = grid.ClientSize.Width - grid.Padding.Horizontal - label.Margin.Horizontal;
            if (width > 0 && width != label.MaximumSize.Width) label.MaximumSize = new Size(width, 0);
        };
    }

    internal static TableLayoutPanel ScrollBody()
    {
        var grid = Grid();
        grid.AutoSize = true;
        grid.AutoSizeMode = AutoSizeMode.GrowAndShrink;
        grid.Dock = DockStyle.Top;
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        return grid;
    }

    internal static Panel Card(Control body, bool scroll = false)
    {
        var card = new Panel { Dock = DockStyle.Fill, BackColor = Color.White, Margin = new Padding(0),
            Padding = Pads(14), AutoScroll = scroll };
        card.Paint += delegate(object sender, PaintEventArgs e) {
            using (var pen = new Pen(Line)) e.Graphics.DrawRectangle(pen, 0, 0, card.Width - 1, card.Height - 1);
        };
        card.Controls.Add(body);
        return card;
    }

    internal static TableLayoutPanel Columns(Control left, Control right, int leftPercent = 38)
    {
        var grid = Grid(3);
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, leftPercent));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Px(12)));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100 - leftPercent));
        grid.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        grid.Controls.Add(left, 0, 0);
        grid.Controls.Add(right, 2, 0);
        return grid;
    }

    internal static Control PageColumns(Control left, Control right, int leftPercent = 38)
    {
        var viewport = new Panel { Dock = DockStyle.Fill, AutoScroll = true, Margin = new Padding(0) };
        var grid = Grid();
        grid.Dock = DockStyle.None;
        grid.Anchor = AnchorStyles.Top | AnchorStyles.Left;
        viewport.Controls.Add(grid);
        grid.Controls.Add(left, 0, 0);
        grid.Controls.Add(right, 0, 1);
        bool? stacked = null;

        EventHandler fit = delegate {
            int dpi = viewport.DeviceDpi;
            int width = viewport.ClientSize.Width + (viewport.VerticalScroll.Visible ? SystemInformation.VerticalScrollBarWidth : 0);
            int height = viewport.ClientSize.Height;
            if (width <= 0 || height <= 0) return;
            bool narrow = width < Scale(730, dpi);
            int gap = Scale(12, dpi);
            int rightMinimum = Scale(385, dpi);
            int leftMinimum = 0;
            if (narrow && left.Controls.Count > 0)
            {
                var cardBody = left.Controls[0];
                leftMinimum = cardBody.GetPreferredSize(new Size(Math.Max(1, width - left.Padding.Horizontal), 0)).Height +
                              left.Padding.Vertical + Scale(12, dpi);
            }
            int needed = narrow ? Math.Max(Scale(235, dpi), leftMinimum) + gap + rightMinimum : rightMinimum;
            int canvasWidth = Math.Max(Scale(315, dpi), width - (needed > height ? SystemInformation.VerticalScrollBarWidth : 0));
            int canvasHeight = Math.Max(height, needed);

            grid.SuspendLayout();
            if (stacked != narrow)
            {
                grid.ColumnStyles.Clear();
                grid.RowStyles.Clear();
                grid.ColumnCount = narrow ? 1 : 3;
                grid.RowCount = narrow ? 3 : 1;
                grid.SetCellPosition(left, new TableLayoutPanelCellPosition(0, 0));
                grid.SetCellPosition(right, new TableLayoutPanelCellPosition(narrow ? 0 : 2, narrow ? 2 : 0));
                if (narrow)
                {
                    grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
                    grid.RowStyles.Add(new RowStyle(SizeType.Absolute));
                    grid.RowStyles.Add(new RowStyle(SizeType.Absolute));
                }
                else
                {
                    grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, leftPercent));
                    grid.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute));
                    grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100 - leftPercent));
                }
                grid.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
                stacked = narrow;
            }
            if (narrow)
            {
                grid.RowStyles[0].Height = needed - gap - rightMinimum;
                grid.RowStyles[1].Height = gap;
            }
            else grid.ColumnStyles[1].Width = gap;
            grid.Size = new Size(canvasWidth, canvasHeight);
            grid.ResumeLayout();
        };
        viewport.ClientSizeChanged += fit;
        viewport.VisibleChanged += fit;
        return viewport;
    }

    internal static ComboBox Choice(string label, params string[] options)
    {
        var box = new ComboBox { AccessibleName = label, Dock = DockStyle.Fill,
            DropDownStyle = ComboBoxStyle.DropDownList, Margin = Pads(0, 1, 0, 3) };
        box.Items.AddRange(options);
        box.SelectedIndex = 0;
        return box;
    }

    internal static NumericUpDown Number(string label, decimal min, decimal max, decimal value, decimal step,
                                          int decimals = 0)
    {
        return new NumericUpDown { AccessibleName = label, Dock = DockStyle.Fill, Minimum = min, Maximum = max,
            Value = value, Increment = step, DecimalPlaces = decimals, Margin = Pads(0, 2, 0, 3) };
    }

    internal static void Field(TableLayoutPanel grid, string name, Control input)
    {
        var row = Grid(2);
        row.RowCount = 1;
        row.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, Px(126)));
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        var title = Single(name);
        row.Controls.Add(title, 0, 0);
        row.Controls.Add(input, 1, 0);
        int titleHeight = title.GetPreferredSize(Size.Empty).Height + title.Margin.Vertical;
        int inputHeight = input.GetPreferredSize(Size.Empty).Height + input.Margin.Vertical;
        int measured = Math.Max(Px(38), Math.Max(titleHeight, input is PathView ? 0 : inputHeight));
        int index = grid.RowCount++;
        grid.RowStyles.Add(new RowStyle(SizeType.Absolute, measured));
        grid.Controls.Add(row, 0, index);
        grid.SetColumnSpan(row, grid.ColumnCount);
    }

    internal static FlowLayoutPanel Actions(params Control[] children)
    {
        var row = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, WrapContents = true,
            Margin = new Padding(0), Padding = Pads(0, 4, 0, 0) };
        row.Controls.AddRange(children);
        return row;
    }
}

internal sealed class PathView : TableLayoutPanel
{
    private readonly Label title;
    private readonly ToolTip tooltip;

    internal PathView(string name, ToolTip tooltip, Button picker = null)
    {
        this.tooltip = tooltip;
        AccessibleName = name;
        Dock = DockStyle.Fill;
        Margin = Views.Pads(0, 1, 0, 3);
        ColumnCount = picker == null ? 1 : 2;
        RowCount = 1;
        RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        title = Views.Single("未选择", 32);
        title.AccessibleName = name;
        title.BackColor = Views.Canvas;
        title.Padding = Views.Pads(7, 0, 4, 0);
        title.Margin = Views.Pads(0, 0, 5, 0);
        Controls.Add(title, 0, 0);
        if (picker != null)
        {
            ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            picker.Dock = DockStyle.Fill;
            picker.MinimumSize = new Size(Views.Px(60), Views.Px(28));
            picker.Margin = new Padding(0);
            Controls.Add(picker, 1, 0);
        }
    }

    internal void ShowPath(string path, string empty = "未选择")
    {
        if (String.IsNullOrWhiteSpace(path)) title.Text = empty;
        else
        {
            string display = System.IO.Path.GetFileName(path.TrimEnd('\\', '/'));
            title.Text = String.IsNullOrEmpty(display) ? path : display;
        }
        tooltip.SetToolTip(title, path ?? "");
    }
}
