' =============================================================
'  Qt File Explorer launcher (no console window)
'
'  Finds a Python that already has PySide6, then starts the GUI
'  with it. pythonw.exe has no console attached, so nothing is
'  left on screen and nothing flashes up.
'
'  To install dependencies, double-click start.bat once.
' =============================================================
Option Explicit

Dim fso, shell, scriptDir, runPy
Dim list, i, pyPath, firstErr, cmd, rc, sub, folders
Dim base, entry

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)
runPy = scriptDir & "\run.py"

If Not fso.FileExists(runPy) Then
    MsgBox "run.py not found next to this file:" & vbCrLf & _
           scriptDir, vbCrLf & vbCrLf & _
           "Keep this file in the same folder as run.py.", _
           16, "Qt File Explorer"
    WScript.Quit 1
End If

' Build the candidate list by concatenation (Join would need a fixed
' string array, which is awkward to extend with discovered paths).
list = Array( _
    scriptDir & "\.venv\Scripts\pythonw.exe", _
    scriptDir & "\.venv\Scripts\python.exe" _
)

base = shell.ExpandEnvironmentStrings( _
    "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts")
If fso.FileExists(base & "\pythonw.exe") Then
    list = list & Array(base & "\pythonw.exe")
End If
If fso.FileExists(base & "\python.exe") Then
    list = list & Array(base & "\python.exe")
End If

' Probe the managed version folders (3.13.12, 3.12.x, ...).
base = shell.ExpandEnvironmentStrings( _
    "%USERPROFILE%\.workbuddy\binaries\python\versions")
If fso.FolderExists(base) Then
    Set folders = fso.GetFolder(base).SubFolders
    For Each sub In folders
        If fso.FileExists(sub.Path & "\pythonw.exe") Then
            list = list & Array(sub.Path & "\pythonw.exe")
        End If
        If fso.FileExists(sub.Path & "\python.exe") Then
            list = list & Array(sub.Path & "\python.exe")
        End If
    Next
End If

pyPath = ""
firstErr = ""

For i = 0 To UBound(list)
    If pyPath = "" Then
        entry = list(i)
        If fso.FileExists(entry) Then
            ' Probe with the window hidden (0) so nothing flashes.
            ' python.exe and pythonw.exe take the same -c argument.
            cmd = """" & entry & """ -c ""import PySide6"""

            On Error Resume Next
            rc = shell.Run(cmd, 0, True)
            If Err.Number <> 0 Then
                firstErr = "Interpreter error: " & Err.Description
                Err.Clear
            ElseIf rc = 0 Then
                pyPath = entry
            Else
                firstErr = "PySide6 is missing for: " & entry
            End If
            On Error GoTo 0
        End If
    End If
Next

If pyPath = "" Then
    MsgBox "Could not start." & vbCrLf & vbCrLf & _
           "No usable Python with PySide6 was found." & vbCrLf & vbCrLf & _
           firstErr & vbCrLf & vbCrLf & _
           "Double-click start.bat to install dependencies, then try again.", _
           16, "Qt File Explorer"
    WScript.Quit 1
End If

' Launch detached so the launcher can exit immediately.
cmd = """" & pyPath & """ """ & runPy & """"

On Error Resume Next
shell.Run(cmd, 1, False)
If Err.Number <> 0 Then
    MsgBox "Launch failed:" & vbCrLf & Err.Description, 16, "Qt File Explorer"
    WScript.Quit 1
End If
On Error GoTo 0