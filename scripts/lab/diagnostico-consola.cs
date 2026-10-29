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
    public static string Snapshot() {
        uint[] ids = new uint[128]; uint count = GetConsoleProcessList(ids, (uint)ids.Length);
        bool inJob; bool known = IsProcessInJob(System.Diagnostics.Process.GetCurrentProcess().Handle, IntPtr.Zero, out inJob);
        string[] console = new string[Math.Min(count, (uint)ids.Length)];
        for (int i=0; i<console.Length; i++) console[i] = ids[i].ToString();
        return "consolePids=" + string.Join(",", console) + " inJob=" + (known ? inJob.ToString() : "unknown");
    }
}
