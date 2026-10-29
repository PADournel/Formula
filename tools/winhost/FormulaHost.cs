// FORMULA.exe : fenêtre Windows de FORMULA (WinForms + WebView2).
//
// Remplace l'ancienne fenêtre Edge (--app). Le programme :
//   - lance le serveur local (python\pythonw.exe <code>\formula.py --host <pid>), sans console ;
//   - affiche http://127.0.0.1:<port>/ dans un WebView2, en fenêtre (2/3 de l'écran, redimensionnable)
//     ou en plein écran (réglage Affichage de l'interface, ou F11) ;
//   - refuse toute autre adresse, les nouvelles fenêtres, les téléchargements, les permissions
//     (caméra, micro, notifications…), les outils de développement et les menus du navigateur ;
//   - se ferme quand le serveur s'arrête (bouton Quitter), et arrête le serveur quand on le ferme ;
//   - si WebView2 ne démarre pas, demande (Oui/Non) avant d'ouvrir Edge en mode application.
//
// Fichiers lus : <dossier de l'exe>\formula-data\code-dir.txt (dossier du code, écrit par
// tools\install_windows.py). Profil WebView2 : <dossier de l'exe>\formula-data\webview2.
// Bibliothèques WebView2 : <dossier de l'exe>\host\.
// Compilé par tools\install_windows.py avec le compilateur C# fourni avec Windows (.NET Framework 4).
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

[assembly: AssemblyTitle("FORMULA")]
[assembly: AssemblyProduct("FORMULA")]
[assembly: AssemblyDescription("FORMULA - lanceur d'émulateurs")]

static class Program
{
    public static string BaseDir = AppDomain.CurrentDomain.BaseDirectory.TrimEnd('\\');
    public static string HostDir = Path.Combine(BaseDir, "host");

    [STAThread]
    static int Main(string[] args)
    {
        // les DLL WebView2 sont rangées dans host\ plutôt qu'à côté de l'exe
        AppDomain.CurrentDomain.AssemblyResolve += delegate(object s, ResolveEventArgs e)
        {
            string p = Path.Combine(HostDir, new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(p) ? Assembly.LoadFrom(p) : null;
        };
        bool first;
        using (Mutex m = new Mutex(true, "Local\\FORMULA-window", out first))
        {
            if (!first)
            {
                Host.BringExistingToFront();
                return 0;
            }
            return Run();
        }
    }

    [MethodImpl(MethodImplOptions.NoInlining)]
    static int Run()
    {
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        Host h = new Host();
        string err = h.StartServer();
        if (err != null)
        {
            MessageBox.Show(err, "FORMULA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return 1;
        }
        Application.Run(h);
        h.StopServer();
        return 0;
    }
}

class Host : Form
{
    const string Title = "FORMULA";
    int port = 47800;
    string origin;
    Process server;                 // null si un serveur FORMULA tournait déjà
    WebView2 web;
    System.Windows.Forms.Timer watch;
    bool closingFromServer;
    Rectangle windowed;             // position et taille de la fenêtre hors plein écran

    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool SetForegroundWindow(IntPtr h);
    [System.Runtime.InteropServices.DllImport("user32.dll")]
    static extern bool ShowWindow(IntPtr h, int cmd);

    public static void BringExistingToFront()
    {
        foreach (Process p in Process.GetProcessesByName("FORMULA"))
        {
            if (p.Id != Process.GetCurrentProcess().Id && p.MainWindowHandle != IntPtr.Zero)
            {
                ShowWindow(p.MainWindowHandle, 9);   // SW_RESTORE
                SetForegroundWindow(p.MainWindowHandle);
            }
        }
    }

    public Host()
    {
        string env = Environment.GetEnvironmentVariable("FORMULA_PORT");
        int v;
        if (env != null && int.TryParse(env, out v)) port = v;
        origin = "http://127.0.0.1:" + port + "/";

        Text = Title;
        BackColor = Color.Black;
        StartPosition = FormStartPosition.Manual;
        MinimumSize = new Size(640, 420);
        windowed = DefaultWindowBounds();
        Bounds = windowed;
        if (SavedFullscreen()) SetFullscreen(true);
        KeyPreview = true;
        try { Icon = Icon.ExtractAssociatedIcon(Application.ExecutablePath); } catch { }

        web = new WebView2();
        web.Dock = DockStyle.Fill;
        web.DefaultBackgroundColor = Color.Black;
        web.CreationProperties = new CoreWebView2CreationProperties();
        web.CreationProperties.UserDataFolder = Path.Combine(Program.BaseDir, "formula-data", "webview2");
        // mêmes restrictions que l'ancienne fenêtre Edge : pas de traduction, pas de tâches de fond
        web.CreationProperties.AdditionalBrowserArguments =
            "--disable-background-networking --disable-component-update --disable-domain-reliability " +
            "--no-pings --disable-sync --disable-features=Translate,msSmartScreenProtection";
        web.CoreWebView2InitializationCompleted += OnReady;
        Controls.Add(web);

        FormClosing += delegate { if (!closingFromServer) StopServer(); };
        Shown += async delegate
        {
            Activate();
            try
            {
                CoreWebView2Environment.SetLoaderDllFolderPath(Program.HostDir);
                await web.EnsureCoreWebView2Async(null);
            }
            catch (Exception ex)
            {
                WebViewFailed(ex.Message);
            }
        };
    }

    // WebView2 absent ou en panne : on propose Edge (mode appli), seulement si l'utilisateur dit oui
    void WebViewFailed(string why)
    {
        DialogResult r = MessageBox.Show(
            "La fenêtre de FORMULA (WebView2, fournie avec Windows 10 et 11) n'a pas pu démarrer :\n" + why +
            "\n\nOuvrir FORMULA dans Microsoft Edge à la place ?\n" +
            "Edge serait lancé en mode application, en navigation InPrivate, sur la page locale " + origin +
            " uniquement.", Title, MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
        if (r != DialogResult.Yes) { Close(); return; }
        string edge = @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe";
        if (!File.Exists(edge)) edge = @"C:\Program Files\Microsoft\Edge\Application\msedge.exe";
        if (!File.Exists(edge))
        {
            MessageBox.Show("Microsoft Edge est introuvable.", Title, MessageBoxButtons.OK, MessageBoxIcon.Error);
            Close();
            return;
        }
        ProcessStartInfo si = new ProcessStartInfo(edge,
            "--inprivate --app=" + origin + " --start-fullscreen --user-data-dir=\"" +
            Path.Combine(Program.BaseDir, "formula-data", "edge-profile") + "\" --no-first-run " +
            "--no-default-browser-check --disable-sync --disable-background-mode --disable-background-networking " +
            "--disable-component-update --no-pings --disable-domain-reliability " +
            "--disable-features=Translate,msImplicitSignin,msEdgeSyncConsent");
        si.UseShellExecute = false;
        Hide();
        Process p = Process.Start(si);
        p.EnableRaisingEvents = true;
        p.Exited += delegate { BeginInvokeClose(); };
    }

    // ------------------------------------------------------------ serveur local

    bool PortOpen()
    {
        try
        {
            using (TcpClient c = new TcpClient())
            {
                IAsyncResult r = c.BeginConnect("127.0.0.1", port, null, null);
                bool ok = r.AsyncWaitHandle.WaitOne(300) && c.Connected;
                if (ok) c.EndConnect(r);
                return ok;
            }
        }
        catch { return false; }
    }

    public string StartServer()
    {
        if (!PortOpen())
        {
            string codeFile = Path.Combine(Program.BaseDir, "formula-data", "code-dir.txt");
            string code = File.Exists(codeFile) ? File.ReadAllText(codeFile).Trim() : "";
            string script = Path.Combine(code, "formula.py");
            string py = Path.Combine(Program.BaseDir, "python", "pythonw.exe");
            if (!File.Exists(script)) return "Code de FORMULA introuvable (" + codeFile + ").";
            if (!File.Exists(py)) return "Python introuvable (" + py + ").";
            ProcessStartInfo si = new ProcessStartInfo(py,
                "\"" + script + "\" --host " + Process.GetCurrentProcess().Id);
            si.UseShellExecute = false;
            si.CreateNoWindow = true;
            si.WorkingDirectory = code;
            server = Process.Start(si);
            server.EnableRaisingEvents = true;
            server.Exited += delegate { BeginInvokeClose(); };
            for (int i = 0; i < 100 && !PortOpen(); i++)
            {
                if (server.HasExited) return "Le serveur de FORMULA s'est arrêté au démarrage.";
                Thread.Sleep(200);
            }
            if (!PortOpen()) return "Le serveur de FORMULA ne répond pas sur " + origin;
        }
        else
        {
            // serveur déjà lancé à part : on se ferme quand il s'arrête
            watch = new System.Windows.Forms.Timer();
            watch.Interval = 2000;
            watch.Tick += delegate { if (!PortOpen()) { watch.Stop(); closingFromServer = true; Close(); } };
            watch.Start();
        }
        return null;
    }

    void BeginInvokeClose()
    {
        try
        {
            if (IsHandleCreated)
                BeginInvoke((MethodInvoker)delegate { closingFromServer = true; Close(); });
        }
        catch { }
    }

    public void StopServer()
    {
        try
        {
            if (server != null && !server.HasExited) server.Kill();
        }
        catch { }
    }

    // ------------------------------------------------------------ WebView2 verrouillé

    void OnReady(object sender, CoreWebView2InitializationCompletedEventArgs e)
    {
        if (!e.IsSuccess)
        {
            WebViewFailed(e.InitializationException.Message);
            return;
        }
        CoreWebView2 c = web.CoreWebView2;
        CoreWebView2Settings s = c.Settings;
        s.AreDevToolsEnabled = false;
        s.AreDefaultContextMenusEnabled = false;
        s.AreBrowserAcceleratorKeysEnabled = false;
        s.IsStatusBarEnabled = false;
        s.IsZoomControlEnabled = false;
        s.IsPinchZoomEnabled = false;
        s.IsSwipeNavigationEnabled = false;
        s.IsPasswordAutosaveEnabled = false;
        s.IsGeneralAutofillEnabled = false;
        s.AreHostObjectsAllowed = false;
        // un seul message accepté de la page : "fullscreen:1" ou "fullscreen:0" (réglage Affichage)
        s.IsWebMessageEnabled = true;
        s.IsBuiltInErrorPageEnabled = true;
        s.IsReputationCheckingRequired = false;   // SmartScreen : rien n'est envoyé pour une page locale

        c.NavigationStarting += delegate(object o, CoreWebView2NavigationStartingEventArgs a)
        {
            if (!a.Uri.StartsWith(origin, StringComparison.OrdinalIgnoreCase)) a.Cancel = true;
        };
        c.FrameNavigationStarting += delegate(object o, CoreWebView2NavigationStartingEventArgs a)
        {
            if (!a.Uri.StartsWith(origin, StringComparison.OrdinalIgnoreCase) && a.Uri != "about:blank") a.Cancel = true;
        };
        c.NewWindowRequested += delegate(object o, CoreWebView2NewWindowRequestedEventArgs a) { a.Handled = true; };
        c.DownloadStarting += delegate(object o, CoreWebView2DownloadStartingEventArgs a) { a.Cancel = true; };
        c.PermissionRequested += delegate(object o, CoreWebView2PermissionRequestedEventArgs a)
        {
            a.State = CoreWebView2PermissionState.Deny;
        };
        c.LaunchingExternalUriScheme += delegate(object o, CoreWebView2LaunchingExternalUriSchemeEventArgs a)
        {
            a.Cancel = true;
        };
        c.DocumentTitleChanged += delegate { Text = Title; };
        c.WebMessageReceived += delegate(object o, CoreWebView2WebMessageReceivedEventArgs a)
        {
            if (!a.Source.StartsWith(origin, StringComparison.OrdinalIgnoreCase)) return;
            string m;
            try { m = a.TryGetWebMessageAsString(); } catch { return; }
            if (m == "fullscreen:1") SetFullscreen(true);
            else if (m == "fullscreen:0") SetFullscreen(false);
        };
        // clavier directement à la page (F11, flèches…) dès l'ouverture et à chaque retour sur la fenêtre
        c.NavigationCompleted += delegate { web.Focus(); };
        Activated += delegate { web.Focus(); };
        c.Navigate(origin);
    }

    // ------------------------------------------------------------ fenêtre / plein écran

    // fenêtre par défaut : 2/3 de l'écran principal (hors barre des tâches), centrée
    static Rectangle DefaultWindowBounds()
    {
        Rectangle wa = Screen.PrimaryScreen.WorkingArea;
        int w = wa.Width * 2 / 3, h = wa.Height * 2 / 3;
        return new Rectangle(wa.X + (wa.Width - w) / 2, wa.Y + (wa.Height - h) / 2, w, h);
    }

    // réglage enregistré par l'interface dans formula-data\settings.json ("fullscreen": true)
    static bool SavedFullscreen()
    {
        try
        {
            string f = Path.Combine(Program.BaseDir, "formula-data", "settings.json");
            return File.Exists(f) &&
                System.Text.RegularExpressions.Regex.IsMatch(File.ReadAllText(f), "\"fullscreen\"\\s*:\\s*true");
        }
        catch { return false; }
    }

    bool IsFullscreen { get { return FormBorderStyle == FormBorderStyle.None; } }

    // demandé par la page (réglage Affichage ou F11, que la page reçoit) ; la page enregistre le réglage
    void SetFullscreen(bool on)
    {
        if (on != IsFullscreen)
        {
            if (on)
            {
                windowed = WindowState == FormWindowState.Normal ? Bounds : RestoreBounds;
                WindowState = FormWindowState.Normal;
                FormBorderStyle = FormBorderStyle.None;
                Bounds = IsHandleCreated ? Screen.FromControl(this).Bounds : Screen.PrimaryScreen.Bounds;
            }
            else
            {
                FormBorderStyle = FormBorderStyle.Sizable;
                WindowState = FormWindowState.Normal;
                Bounds = windowed;
            }
        }
    }
}
