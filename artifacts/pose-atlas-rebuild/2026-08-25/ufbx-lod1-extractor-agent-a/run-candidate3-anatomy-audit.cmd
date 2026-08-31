@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\candidate3-anatomy-audit"
set "C3=%ROOT%\body-morph-candidate3"
set "PYTHON=C:\Users\hitos\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
if not exist "%OUT%" mkdir "%OUT%"
"%PYTHON%" "%ROOT%\audit_candidate2_anatomy.py" ^
  --base-vertices "%ROOT%\run-fixed-clone\mhr-lod1.vertices.tsv" ^
  --faces "%ROOT%\run-fixed-clone\mhr-lod1.faces.tsv" ^
  --candidate-bin "%C3%\candidate3-vertices.bin" ^
  --candidate-report "%C3%\candidate3-report.json" ^
  --skeleton "%ROOT%\candidate2-anatomy-audit\mhr-official-127-skeleton.tsv" ^
  --output-dir "%OUT%" --label candidate3 1>"%OUT%\audit-stdout.json" 2>"%OUT%\audit-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\audit-exit-code.txt" echo %STEP%
exit /b %STEP%
