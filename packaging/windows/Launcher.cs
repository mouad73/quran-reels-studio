using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

// No installer, elevation, registry settings, global PATH or external .NET packages.
internal static class Program {
    [STAThread]
    private static int Main(string[] args) {
        bool created;
        using (var mutex = new Mutex(true, "Local\\TechMouad.QuranReelsStudio", out created)) {
            if (!created) {
                MessageBox.Show("Quran Reels Studio is already running. Open its window from the taskbar.", "Quran Reels Studio");
                return 0;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            using (var form = new StudioWindow()) Application.Run(form);
        }
        return 0;
    }
}

internal sealed class StudioWindow : Form {
    private readonly string data = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "QuranReelsStudio");
    private readonly Label status;
    private readonly Button open;
    private readonly System.Windows.Forms.Timer poll = new System.Windows.Forms.Timer();
    private Process server;
    private ProcessJob job;
    private string url;
    private bool ready;
    private readonly DateTime started = DateTime.UtcNow;

    public StudioWindow() {
        Text = "Quran Reels Studio — TechMouad";
        ClientSize = new Size(580, 430);
        MinimumSize = new Size(596, 469);
        MaximumSize = new Size(760, 520);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(245, 247, 241);
        Font = new Font("Segoe UI", 11);
        RightToLeft = RightToLeft.Yes;
        var title = new Label { Text = "Quran Reels Studio", AutoSize = false, TextAlign = ContentAlignment.MiddleCenter, Bounds = new Rectangle(20, 18, 540, 52), ForeColor = Color.FromArgb(17, 67, 54), Font = new Font("Segoe UI", 24, FontStyle.Bold), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
        Controls.Add(title);
        Controls.Add(new Label { Text = "إنشاء فيديو قرآن بشعارك على جهازك", TextAlign = ContentAlignment.MiddleCenter, Bounds = new Rectangle(20, 75, 540, 30), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right });
        status = new Label { Text = "جارٍ التحضير لأول تشغيل…", TextAlign = ContentAlignment.MiddleCenter, Bounds = new Rectangle(30, 118, 520, 67), ForeColor = Color.FromArgb(40, 75, 65), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
        Controls.Add(status);
        open = Button("فتح الأداة في المتصفح", new Rectangle(30, 198, 520, 46), delegate { Open(url); });
        open.Enabled = false;
        Button("مجلد الفيديوهات", new Rectangle(30, 257, 250, 42), delegate { Directory.CreateDirectory(Path.Combine(data, "output")); Open(Path.Combine(data, "output")); });
        Button("سجل التشغيل", new Rectangle(300, 257, 250, 42), delegate { var file = Path.Combine(data, "launcher.log"); if (File.Exists(file)) Open(file); });
        Controls.Add(new Label { Text = "يتطلب التشغيل الأول الإنترنت لتحميل محرك الفيديو.\nاترك هذه النافذة مفتوحة أثناء العمل. إغلاقها يوقف الأداة.", TextAlign = ContentAlignment.MiddleCenter, Bounds = new Rectangle(30, 315, 520, 54), Font = new Font("Segoe UI", 9), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right });
        var help = new LinkLabel { Text = "شرح الاستخدام على TechMouad", TextAlign = ContentAlignment.MiddleCenter, Bounds = new Rectangle(30, 382, 520, 26), Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right };
        help.LinkClicked += delegate { Open("https://techmouad.com/إنشاء-فيديو-قرآن/"); };
        Controls.Add(help);
        Shown += delegate { StartServer(); };
        FormClosed += delegate { StopServer(); };
        poll.Interval = 900;
        poll.Tick += delegate { CheckServer(); };
    }

    private Button Button(string text, Rectangle bounds, EventHandler handler) {
        var button = new Button { Text = text, Bounds = bounds, BackColor = Color.FromArgb(19, 105, 95), ForeColor = Color.White, FlatStyle = FlatStyle.Flat, Cursor = Cursors.Hand };
        button.FlatAppearance.BorderSize = 0;
        button.Click += handler;
        Controls.Add(button);
        return button;
    }

    private void Open(string destination) {
        if (String.IsNullOrEmpty(destination)) return;
        try { Process.Start(new ProcessStartInfo(destination) { UseShellExecute = true }); }
        catch (Exception) { MessageBox.Show("Could not open automatically. Open this address or path manually:\n" + destination, Text); }
    }

    private void StartServer() {
        try {
            string runtime = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "runtime", "pythonw.exe");
            if (!File.Exists(runtime)) throw new IOException("Extract the entire ZIP before opening QuranReelsStudio.exe. Keep the runtime and app folders beside it.");
            Directory.CreateDirectory(data);
            File.WriteAllText(Path.Combine(data, "launcher-status.txt"), "جارٍ بدء التشغيل…");
            // Windows chooses an unused loopback port, so existing Streamlit apps stay running.
            int port;
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            port = ((IPEndPoint)listener.LocalEndpoint).Port;
            listener.Stop();
            url = "http://127.0.0.1:" + port + "/";
            var info = new ProcessStartInfo(runtime, "-m quran_reels.desktop --port " + port) { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = data };
            info.EnvironmentVariables["QRS_DATA_DIR"] = data;
            info.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
            info.EnvironmentVariables["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false";
            job = new ProcessJob();
            server = Process.Start(info);
            // Closing or crashing the launcher also stops Python and its FFmpeg children.
            job.Assign(server);
            poll.Start();
        } catch (Exception error) {
            StopServer();
            status.Text = "تعذر بدء التشغيل. راجع سجل التشغيل أو أعد فك ضغط الملف.";
            MessageBox.Show(error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void CheckServer() {
        if (server == null) return;
        if (server.HasExited) {
            poll.Stop();
            open.Enabled = false;
            status.Text = "توقف التشغيل. افتح السجل لمعرفة السبب، ثم أغلق النافذة وأعد المحاولة.";
            return;
        }
        if (ready) return;
        try { status.Text = File.ReadAllText(Path.Combine(data, "launcher-status.txt")); } catch (IOException) { }
        try {
            var request = (HttpWebRequest)WebRequest.Create(url + "_stcore/health");
            request.Proxy = null;
            request.Timeout = 450;
            using (var response = (HttpWebResponse)request.GetResponse()) {
                if (response.StatusCode != HttpStatusCode.OK) return;
            }
            ready = true;
            status.Text = "الأداة جاهزة. اختر الخلفية والآيات ثم راجع التصميم.\n\u200e" + url + "\u200e";
            open.Enabled = true;
            Open(url);
        } catch (WebException) {
            if ((DateTime.UtcNow - started).TotalMinutes > 8) status.Text = "التحضير يستغرق وقتاً. تحقق من الإنترنت وافتح سجل التشغيل لمعرفة التفاصيل.";
        }
    }

    private void StopServer() {
        poll.Stop();
        if (job != null) { job.Dispose(); job = null; }
        if (server != null) {
            try { if (!server.HasExited) server.Kill(); } catch (InvalidOperationException) { }
            server.Dispose();
            server = null;
        }
    }

    protected override void Dispose(bool disposing) {
        if (disposing) { StopServer(); poll.Dispose(); }
        base.Dispose(disposing);
    }
}

internal sealed class ProcessJob : IDisposable {
    private IntPtr handle;
    [StructLayout(LayoutKind.Sequential)] private struct BasicLimits { public Int64 PerProcessUserTimeLimit, PerJobUserTimeLimit; public UInt32 LimitFlags; public UIntPtr MinimumWorkingSetSize, MaximumWorkingSetSize; public UInt32 ActiveProcessLimit; public UIntPtr Affinity; public UInt32 PriorityClass, SchedulingClass; }
    [StructLayout(LayoutKind.Sequential)] private struct IoCounters { public UInt64 ReadOperationCount, WriteOperationCount, OtherOperationCount, ReadTransferCount, WriteTransferCount, OtherTransferCount; }
    [StructLayout(LayoutKind.Sequential)] private struct ExtendedLimits { public BasicLimits BasicLimitInformation; public IoCounters IoInfo; public UIntPtr ProcessMemoryLimit, JobMemoryLimit, PeakProcessMemoryUsed, PeakJobMemoryUsed; }
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)] private static extern IntPtr CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool SetInformationJobObject(IntPtr job, int infoClass, ref ExtendedLimits info, UInt32 size);
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("kernel32.dll")] private static extern bool CloseHandle(IntPtr handle);
    public ProcessJob() {
        handle = CreateJobObject(IntPtr.Zero, null);
        var limits = new ExtendedLimits();
        limits.BasicLimitInformation.LimitFlags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (handle == IntPtr.Zero || !SetInformationJobObject(handle, 9, ref limits, (UInt32)Marshal.SizeOf(typeof(ExtendedLimits)))) {
            Dispose(); throw new IOException("Could not prepare the application process group.");
        }
    }
    public void Assign(Process process) {
        if (!AssignProcessToJobObject(handle, process.Handle)) throw new IOException("Could not attach the local server to the launcher.");
    }
    public void Dispose() { if (handle != IntPtr.Zero) { CloseHandle(handle); handle = IntPtr.Zero; } }
}
