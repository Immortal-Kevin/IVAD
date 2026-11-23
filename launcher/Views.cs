using System;
using System.Drawing;
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

    internal static Label Text(string value, float size = 10, bool bold = false)
    {
        return new Label { Text = value, AutoSize = true, ForeColor = Ink,
            Font = new Font("Microsoft YaHei UI", size, bold ? FontStyle.Bold : FontStyle.Regular),
            Margin = new Padding(0, 0, 0, 7), TextAlign = ContentAlignment.MiddleLeft };
    }

    internal static Label Single(string value, int height = 30)
    {
        var label = Text(value);
        label.AutoSize = false;
        label.AutoEllipsis = true;
        label.Height = height;
        label.Dock = DockStyle.Fill;
        return label;
    }

    internal static Button Button(string text, bool primary = false)
    {
        var button = new Button { Text = text, AutoSize = true, Height = 34,
            MinimumSize = new Size(92, 34), FlatStyle = FlatStyle.Flat,
            BackColor = primary ? Blue : Color.White, ForeColor = primary ? Color.White : Ink,
            Margin = new Padding(0, 0, 8, 0), Cursor = Cursors.Hand, UseVisualStyleBackColor = false };
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
        grid.RowStyles.Add(height == -1 ? new RowStyle(SizeType.Percent, 100) :
            height == 0 ? new RowStyle(SizeType.AutoSize) : new RowStyle(SizeType.Absolute, height));
        grid.Controls.Add(control, 0, index);
        grid.SetColumnSpan(control, grid.ColumnCount);
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
            Padding = new Padding(17), AutoScroll = scroll };
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
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 14));
        grid.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100 - leftPercent));
        grid.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        grid.Controls.Add(left, 0, 0);
        grid.Controls.Add(right, 2, 0);
        return grid;
    }

    internal static ComboBox Choice(string label, params string[] options)
    {
        var box = new ComboBox { AccessibleName = label, Dock = DockStyle.Fill,
            DropDownStyle = ComboBoxStyle.DropDownList, Margin = new Padding(0, 1, 0, 3) };
        box.Items.AddRange(options);
        box.SelectedIndex = 0;
        return box;
    }

    internal static NumericUpDown Number(string label, decimal min, decimal max, decimal value, decimal step,
                                          int decimals = 0)
    {
        return new NumericUpDown { AccessibleName = label, Dock = DockStyle.Fill, Minimum = min, Maximum = max,
            Value = value, Increment = step, DecimalPlaces = decimals, Margin = new Padding(0, 2, 0, 3) };
    }

    internal static void Field(TableLayoutPanel grid, string name, Control input)
    {
        var row = Grid(2);
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 126));
        row.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        row.Controls.Add(Single(name), 0, 0);
        row.Controls.Add(input, 1, 0);
        Row(grid, row, 38);
    }

    internal static FlowLayoutPanel Actions(params Control[] children)
    {
        var row = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, WrapContents = false,
            Margin = new Padding(0), Padding = new Padding(0, 5, 0, 0) };
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
        Margin = new Padding(0, 1, 0, 3);
        ColumnCount = picker == null ? 1 : 2;
        RowCount = 1;
        RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        title = Views.Single("未选择", 32);
        title.AccessibleName = name;
        title.BackColor = Views.Canvas;
        title.Padding = new Padding(7, 0, 4, 0);
        title.Margin = new Padding(0, 0, 5, 0);
        Controls.Add(title, 0, 0);
        if (picker != null)
        {
            ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
            picker.Dock = DockStyle.Fill;
            picker.MinimumSize = new Size(60, 0);
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
