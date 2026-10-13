' ===================================================================
'  Qt File Explorer launcher
'
'  Double-click this file to start the app WITHOUT a console window.
'  start.bat does the real work: it finds a Python, installs PySide6 if
'  needed, then re-launches the GUI through pythonw.exe (no console).
' ===================================================================
Option Explicit

Dim shell, fso, scriptDir, launcher, result

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
launcher = scriptDir & "\start.bat"

If Not fso.FileExists(launcher) Then
    MsgBox "start.bat not found next to this file:" & vbCrLf & _
           scriptDir, 16, "Qt File Explorer"
    WScript.Quit 1
End If

' 7 = minimized, so nothing flashes on screen. The window still exists,
' which keeps error output reachable if something goes wrong.
result = shell.Run("""" & launcher & """ --run", 7, False

If result <> 0 Then
    MsgBox "Failed to start. Exit code: " & result & vbCrLf & vbCrLf & _
           "Double-click start.bat instead to see the error message.", _
           16, "Qt File Explorer"
End If