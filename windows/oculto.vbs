' oculto.vbs - lanza un .bat SIN ventana de consola (ventana 0 de WScript.Shell.Run).
' Lo usan las tareas programadas del AG Launcher y de Bot Lab: una tarea sin /RU (usuario actual)
' abre una consola de cmd cada vez que corre; a traves de este envoltorio no se ve nada.
' Uso: "%SystemRoot%\System32\wscript.exe" "...\windows\oculto.vbs" "C:\ruta\al\guion.bat"
' (los programas Python no lo necesitan: van con pythonw.exe, que ya no tiene consola)
CreateObject("WScript.Shell").Run "cmd /c """ & WScript.Arguments(0) & """", 0, False
