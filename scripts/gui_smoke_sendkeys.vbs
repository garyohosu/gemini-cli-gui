' Smoke test for Gemini CLI GUI Wrapper via SendKeys
' Starts the app, activates window, then drives UI.

Option Explicit

Const APP_TITLE = "Gemini CLI GUI Wrapper"
Const PY_CMD = "py app.py"
Const START_WAIT_MS = 2500
Const WAIT_MS = 800
Const TAB_TO_FOLDER_BTN = 2
Const TAB_TO_INPUT = 6
Const RETRIES = 10

Dim shell, fso, logPath, logFile
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
logPath = CreateAbsolutePath("logs\sendkeys.log")
EnsureFolderExists fso, GetParentFolder(logPath)
Set logFile = fso.OpenTextFile(logPath, 8, True, -1)

LogLine logFile, "Start"

Dim workspacePath
workspacePath = "C:\\temp"

Dim promptText
promptText = "dirを実行してください"

' Start app
shell.Run PY_CMD, 1, False
WScript.Sleep START_WAIT_MS

Dim pid
pid = FindAppPid("python.exe", "app.py")
LogLine logFile, "PID=" & pid

Dim activated
activated = False

If pid <> 0 Then
  activated = TryActivatePid(pid)
End If

If Not activated Then
  activated = TryActivateTitle(APP_TITLE)
End If

If Not activated Then
  LogLine logFile, "Failed to activate window: " & APP_TITLE
  WScript.Echo "Failed to activate window: " & APP_TITLE
  WScript.Quit 1
End If

WScript.Sleep WAIT_MS

' Focus folder button
SendTabs shell, TAB_TO_FOLDER_BTN
shell.SendKeys "{ENTER}"
WScript.Sleep WAIT_MS

' Input workspace path in dialog
shell.SendKeys workspacePath
shell.SendKeys "{ENTER}"
WScript.Sleep WAIT_MS

' Focus input area
SendTabs shell, TAB_TO_INPUT
shell.SendKeys promptText
shell.SendKeys "^({ENTER})"

LogLine logFile, "Finished"
WScript.Echo "SendKeys smoke test finished."

Sub SendTabs(s, count)
  Dim i
  For i = 1 To count
    s.SendKeys "{TAB}"
    WScript.Sleep 150
  Next
End Sub

Function FindAppPid(procName, keyword)
  Dim wmi, items, item
  FindAppPid = 0
  Set wmi = GetObject("winmgmts:\\.\root\cimv2")
  Set items = wmi.ExecQuery("SELECT ProcessId, CommandLine FROM Win32_Process WHERE Name='" & procName & "'")
  For Each item In items
    If Not IsNull(item.CommandLine) Then
      If InStr(1, item.CommandLine, keyword, vbTextCompare) > 0 Then
        FindAppPid = item.ProcessId
        Exit Function
      End If
    End If
  Next
End Function

Function TryActivatePid(pid)
  Dim i
  TryActivatePid = False
  For i = 1 To RETRIES
    If shell.AppActivate(CLng(pid)) Then
      TryActivatePid = True
      LogLine logFile, "Activated by PID"
      Exit Function
    End If
    WScript.Sleep 200
  Next
End Function

Function TryActivateTitle(title)
  Dim i
  TryActivateTitle = False
  For i = 1 To RETRIES
    If shell.AppActivate(title) Then
      TryActivateTitle = True
      LogLine logFile, "Activated by title"
      Exit Function
    End If
    WScript.Sleep 200
  Next
End Function

Sub EnsureFolderExists(fs, path)
  If Not fs.FolderExists(path) Then
    fs.CreateFolder(path)
  End If
End Sub

Function GetParentFolder(path)
  Dim i
  i = InStrRev(path, "\")
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
