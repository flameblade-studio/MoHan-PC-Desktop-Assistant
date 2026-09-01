@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
set "OUT=%ROOT%\body-morph-candidate3"
if not exist "%OUT%" mkdir "%OUT%"
"%PYTHON%" "%ROOT%\morph_body_candidate3.py" ^
  --vertices "%ROOT%\run-fixed-clone\mhr-lod1.vertices.tsv" ^
  --faces "%ROOT%\run-fixed-clone\mhr-lod1.faces.tsv" ^
  --skeleton "%ROOT%\candidate2-anatomy-audit\mhr-official-127-skeleton.tsv" ^
  --output-dir "%OUT%" 1>"%OUT%\stdout.json" 2>"%OUT%\stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\exit-code.txt" echo %STEP%
exit /b %STEP%
