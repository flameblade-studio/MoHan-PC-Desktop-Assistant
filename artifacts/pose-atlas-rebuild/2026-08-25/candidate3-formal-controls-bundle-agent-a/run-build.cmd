@echo off
setlocal
set "HERE=%~dp0"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
"%PYTHON%" "%HERE%build_formal_controls_bundle.py" 1>"%HERE%stdout.txt" 2>"%HERE%stderr.txt"
set "RC=%ERRORLEVEL%"
>"%HERE%exit-code.txt" echo %RC%
exit /b %RC%
