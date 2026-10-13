' =============================================================
'  Qt File Explorer launcher (no console window)
'
'  Finds a Python that already has PySide6, then starts the GUI
'  with it. pythonw.exe has no console attached, so nothing is
'  left on screen and nothing flashes up.
'
'  To install dependencies, double-click start.bat once.
'
'  CAUTION: do not use VBScript reserved words as variable names.
'  "list", "sub" and "base" are reserved and will not parse.
' =============================================================
Option Explicit

Dim fso, shell, scriptDir, runPy
Dim cand, i, pyPath, firstErr, cmdLine, rc, folderItem, folderList
Dim rootDir, pyFile

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

' Grow the candidate list with & Array() rather than Join(), which
' only accepts a fixed string array.
cand = Array( _
    scriptDir & "\.venv\Scripts\pythonw.exe", _
    scriptDir & "\.venv\Scripts\python.exe" _
)

rootDir = shell.ExpandEnvironmentStrings( _
    "%USERPROFILE%\.workbuddy\binaries\python\envs\default\Scripts")
If fso.FileExists(rootDir & "\pythonw.exe") Then
    cand = cand & Array(rootDir & "\pythonw.exe")
End If
If fso.FileExists(rootDir & "\python.exe") Then
    cand = cand & Array(rootDir & "\python.exe")
End If

' Probe the managed version folders (3.13.12, 3.12.x, ...).
rootDir = shell.ExpandEnvironmentStrings( _
    "%USERPROFILE%\.workbuddy\binaries\python\versions")
If fso.FolderExists(rootDir) Then
    Set folderList = fso.GetFolder(rootDir).SubFolders
    For Each folderItem In folderList
        If fso.FileExists(folderItem.Path & "\pythonw.exe") Then
            cand = cand & Array(folderItem.Path & "\pythonw.exe")
        End If
        If fso.FileExists(folderItem.Path & "\python.exe") Then
            cand = cand & Array(folderItem.Path & "\python.exe")
        End If
    Next
End If

pyPath = ""
firstErr = ""

For i = 0 To UBound(cand)
    If pyPath = "" Then
        pyFile = cand(i)
        If fso.FileExists(pyFile) Then
            ' Probe with the window hidden (0) so nothing flashes.
            ' python.exe and pythonw.exe accept the same -c argument.
            cmdLine = """" & pyFile & """ -c ""import PySide6"""

            On Error Resume Next
            rc = shell.Run(cmdLine, 0, True)
            If Err.Number <> 0 Then
                firstErr = "Interpreter error: " & Err.Description
                Err.Clear
            ElseIf rc = 0 Then
                pyPath = pyFile
            Else
                firstErr = "PySide6 is missing for: " & pyFile
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

' Launch detached so this launcher can exit immediately.
cmdLine = """" & pyPath & """ """ & runPy & """"

On Error Resume Next
shell.Run(cmdLine, 1, False)
If Err.Number <> 0 Then
    MsgBox "Launch failed:" & vbCrLf & Err.Description, 16, "Qt File Explorer"
    WScript.Quit 1
End If
On Error GoTo 0