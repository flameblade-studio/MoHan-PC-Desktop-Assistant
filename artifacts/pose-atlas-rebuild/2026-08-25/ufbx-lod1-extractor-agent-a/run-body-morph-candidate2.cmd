@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
set "OUT=%ROOT%\body-morph-candidate2"
if not exist "%OUT%" mkdir "%OUT%"
"%PYTHON%" "%ROOT%\morph_body_candidate2.py" ^
  --vertices "%ROOT%\run-fixed-clone\mhr-lod1.vertices.tsv" ^
  --faces "%ROOT%\run-fixed-clone\mhr-lod1.faces.tsv" ^
  --output-dir "%OUT%" 1>"%OUT%\stdout.json" 2>"%OUT%\stderr.txt"
set "RESULT=%ERRORLEVEL%"
>"%OUT%\exit-code.txt" echo %RESULT%
exit /b %RESULT%
