@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\body-morph-candidate2"
set "PYTHON=C:\Users\hitos\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
"%PYTHON%" "%ROOT%\verify_candidate2.py" ^
  --vertices-bin "%OUT%\candidate2-vertices.bin" ^
  --obj "%OUT%\candidate2.obj" ^
  --faces "%ROOT%\run-fixed-clone\mhr-lod1.faces.tsv" ^
  --report "%OUT%\candidate2-report.json" 1>"%OUT%\verify-stdout.json" 2>"%OUT%\verify-stderr.txt"
set "RESULT=%ERRORLEVEL%"
>"%OUT%\verify-exit-code.txt" echo %RESULT%
exit /b %RESULT%
