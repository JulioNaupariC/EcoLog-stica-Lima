using System;
using System.IO;
using System.Runtime.InteropServices;
// No PowerShell callbacks on native control threads. Never log command lines/environment.
public static class EcoLogConsoleEvidence {
    private delegate bool Handler(uint signal);
    private static Handler handler;
    private static string target;
    private static int pid;
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool SetConsoleCtrlHandler(Handler callback, bool add);
    [DllImport("kernel32.dll")]
    private static extern uint GetConsoleProcessList([Out] uint[] list, uint count);
    [DllImport("kernel32.dll", SetLastError=true)]
    private static extern bool IsProcessInJob(IntPtr process, IntPtr job, out bool result);
    public static void Install(string path, int processId) {
        target = path; pid = processId;
        handler = delegate(uint signal) {
            try {
                // CTRL_C=0, BREAK=1, CLOSE=2, LOGOFF=5, SHUTDOWN=6.
                using (FileStream stream = new FileStream(target, FileMode.Append, FileAccess.Write, FileShare.ReadWrite))
                using (StreamWriter writer = new StreamWriter(stream)) {
                    writer.WriteLine(DateTime.UtcNow.ToString("o") + " console-control pid=" + pid + " signal=" + signal);
                    writer.Flush(); stream.Flush(true);
                }
            } catch { /* A forced kill may prevent any write at all. */ }
            return false; // Observe only; preserve Windows/default handler semantics.
        };
        if (!SetConsoleCtrlHandler(handler, true)) throw new System.ComponentModel.Win32Exception();
    }
    public static bool HasConsole() {
        return GetConsoleProcessList(new uint[1], 1) != 0;
    }
    public static string Snapshot() {
        uint[] ids = new uint[128]; uint count = GetConsoleProcessList(ids, (uint)ids.Length);
        bool inJob; bool known = IsProcessInJob(System.Diagnostics.Process.GetCurrentProcess().Handle, IntPtr.Zero, out inJob);
        string[] console = new string[Math.Min(count, (uint)ids.Length)];
        for (int i=0; i<console.Length; i++) console[i] = ids[i].ToString();
        return "hasConsole=" + (count != 0).ToString() + " consolePids=" + string.Join(",", console) + " inJob=" + (known ? inJob.ToString() : "unknown");
    }
}

// Redirect callbacks run in managed C#, not in PowerShell threads without a runspace.
// The supervisor owns these streams until WaitForExit drains both readers.
public sealed class EcoLogHeadlessProcess : IDisposable {
    public System.Diagnostics.Process Process { get; private set; }
    private StreamWriter output;
    private StreamWriter error;
    private readonly object ioLock = new object();
    private bool started;
    private bool disposed;
    public volatile bool LogFailed;
    public EcoLogHeadlessProcess(string exe, string args, string directory, string outPath, string errPath) {
        try {
            output = new StreamWriter(outPath, false); output.AutoFlush = true;
            error = new StreamWriter(errPath, false); error.AutoFlush = true;
            Process = new System.Diagnostics.Process();
            Process.StartInfo = new System.Diagnostics.ProcessStartInfo {
                FileName = exe, Arguments = args, WorkingDirectory = directory,
                UseShellExecute = false, CreateNoWindow = true,
                RedirectStandardInput = true, RedirectStandardOutput = true, RedirectStandardError = true
            };
            Process.OutputDataReceived += delegate(object sender, System.Diagnostics.DataReceivedEventArgs e) {
                if (e.Data != null) { lock (ioLock) { if (!disposed) { try { output.WriteLine(e.Data); } catch { LogFailed = true; } } } }
            };
            Process.ErrorDataReceived += delegate(object sender, System.Diagnostics.DataReceivedEventArgs e) {
                if (e.Data != null) { lock (ioLock) { if (!disposed) { try { error.WriteLine(e.Data); } catch { LogFailed = true; } } } }
            };
            if (!Process.Start()) throw new InvalidOperationException("Process start failed");
            started = true;
            Process.StandardInput.Close(); // Explicit EOF: no console input inherited.
            Process.BeginOutputReadLine(); Process.BeginErrorReadLine();
        } catch { Dispose(); throw; }
    }
    public void Dispose() {
        // Never terminate a process as a side effect of disposing diagnostic handles.
        if (Process != null) {
            if (started && Process.HasExited) Process.WaitForExit();
            else if (started) {
                // On a managed supervisor failure the child may survive. Detach readers
                // before closing streams; forceful termination cannot execute this path.
                try { Process.CancelOutputRead(); } catch { }
                try { Process.CancelErrorRead(); } catch { }
            }
            Process.Dispose(); Process = null;
        }
        lock (ioLock) {
            disposed = true;
            if (output != null) { output.Dispose(); output = null; }
            if (error != null) { error.Dispose(); error = null; }
        }
    }
}
