Option Explicit

Const APP_TITLE = "Gemini CLI GUI Wrapper"
Const PY_CMD = "py app.py --log-mode all"
Const START_WAIT_MS = 250
Const WAIT_MS = 800
Const TAB_TO_FOLDER_BTN = 2
Const TAB_TO_INPUT = 6
Const RETRIES = 10
Const RETRY_INTERVAL_MS = 250
Const APP_START_TIMEOUT_MS = 10000
Const RESPONSE_TIMEOUT_MS = 180000
Const RESPONSE_POLL_MS = 1000
Const RESPONSE_LOG_MARKER = "Prompt response received:"

Dim shell, fso, logPath, logFile
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
logPath = CreateAbsolutePath("logs\\sendkeys.log")
EnsureFolderExists fso, GetParentFolder(logPath)
Set logFile = fso.OpenTextFile(logPath, 8, True, -1)

LogLine logFile, "Start"

Dim workspacePath
workspacePath = CreateAbsolutePath(".")

Dim promptText
promptText = "Respond with exactly OK."

Dim guiLogPath
guiLogPath = CreateAbsolutePath("logs\\gui.log")
If fso.FileExists(guiLogPath) Then
  On Error Resume Next
  fso.DeleteFile guiLogPath, True
  On Error GoTo 0
End If

LogLine logFile, "Launch app: " & PY_CMD
shell.Run PY_CMD, 1, False
WScript.Sleep START_WAIT_MS

If Not WaitForWindow(APP_TITLE, APP_START_TIMEOUT_MS) Then
  LogLine logFile, "Failed to activate window within timeout: " & APP_TITLE
  logFile.Close
  WScript.Echo "Failed to activate window within timeout: " & APP_TITLE
  WScript.Quit 1
End If

If Not TryActivateTitle(APP_TITLE) Then
  LogLine logFile, "Failed to activate window: " & APP_TITLE
  logFile.Close
  WScript.Echo "Failed to activate window: " & APP_TITLE
  WScript.Quit 1
End If

WScript.Sleep WAIT_MS

LogLine logFile, "Open workspace chooser"
SendTabs shell, TAB_TO_FOLDER_BTN
shell.SendKeys "{ENTER}"
WScript.Sleep WAIT_MS

LogLine logFile, "Input workspace: " & workspacePath
shell.SendKeys workspacePath
shell.SendKeys "{ENTER}"
WScript.Sleep WAIT_MS

LogLine logFile, "Input prompt and submit"
SendTabs shell, TAB_TO_INPUT
shell.SendKeys promptText
shell.SendKeys "^({ENTER})"

LogLine logFile, "Wait for response marker in gui.log"
If Not WaitForResponseLog(guiLogPath, RESPONSE_TIMEOUT_MS, RESPONSE_LOG_MARKER) Then
  LogLine logFile, "Response verification timed out"
  CloseAppWindow
  logFile.Close
  WScript.Echo "Smoke test failed: response not confirmed."
  WScript.Quit 1
End If

LogLine logFile, "Response verified"
CloseAppWindow
LogLine logFile, "Finished"
logFile.Close
WScript.Echo "SendKeys smoke test finished."

Sub SendTabs(s, count)
  Dim i
  For i = 1 To count
    s.SendKeys "{TAB}"
    WScript.Sleep 150
  Next
End Sub

Function TryActivateTitle(title)
  Dim i
  TryActivateTitle = False
  For i = 1 To RETRIES
    If shell.AppActivate(title) Then
      TryActivateTitle = True
      LogLine logFile, "Activated by title"
      Exit Function
    End If
    WScript.Sleep RETRY_INTERVAL_MS
  Next
End Function

Function WaitForWindow(title, timeoutMs)
  Dim elapsed
  WaitForWindow = False
  elapsed = 0
  Do While elapsed < timeoutMs
    If shell.AppActivate(title) Then
      LogLine logFile, "Window detected"
      WaitForWindow = True
      Exit Function
    End If
    WScript.Sleep RETRY_INTERVAL_MS
    elapsed = elapsed + RETRY_INTERVAL_MS
  Loop
End Function

Function WaitForResponseLog(path, timeoutMs, marker)
  Dim elapsed, content
  WaitForResponseLog = False
  elapsed = 0
  Do While elapsed < timeoutMs
    content = TryReadAllText(path)
    If InStr(1, content, marker, vbTextCompare) > 0 Then
      WaitForResponseLog = True
      Exit Function
    End If
    WScript.Sleep RESPONSE_POLL_MS
    elapsed = elapsed + RESPONSE_POLL_MS
  Loop
End Function

Function TryReadAllText(path)
  Dim ts, content
  content = ""
  If Not fso.FileExists(path) Then
    TryReadAllText = ""
    Exit Function
  End If
  On Error Resume Next
  Set ts = fso.OpenTextFile(path, 1, False, -1)
  If Err.Number = 0 Then
    content = ts.ReadAll
    ts.Close
  End If
  Err.Clear
  On Error GoTo 0
  TryReadAllText = content
End Function

Sub CloseAppWindow()
  If TryActivateTitle(APP_TITLE) Then
    shell.SendKeys "%{F4}"
    LogLine logFile, "Requested app close (Alt+F4)"
    WScript.Sleep 500
  End If
End Sub

Sub EnsureFolderExists(fs, path)
  If Not fs.FolderExists(path) Then
    fs.CreateFolder(path)
  End If
End Sub

Function GetParentFolder(path)
  Dim i
  i = InStrRev(path, "\\")
  If i > 0 Then
    GetParentFolder = Left(path, i - 1)
  Else
    GetParentFolder = "."
  End If
End Function

Function CreateAbsolutePath(relPath)
  Dim fs, base
  Set fs = CreateObject("Scripting.FileSystemObject")
  base = fs.GetAbsolutePathName(".")
  CreateAbsolutePath = fs.BuildPath(base, relPath)
End Function

Sub LogLine(f, msg)
  f.WriteLine Now & " " & msg
End Sub
