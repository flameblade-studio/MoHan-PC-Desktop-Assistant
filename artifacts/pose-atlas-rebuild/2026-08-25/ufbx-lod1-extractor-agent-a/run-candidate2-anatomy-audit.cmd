@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\candidate2-anatomy-audit"
set "C2=%ROOT%\body-morph-candidate2"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
"%PYTHON%" "%ROOT%\audit_candidate2_anatomy.py" ^
  --base-vertices "%ROOT%\run-fixed-clone\mhr-lod1.vertices.tsv" ^
  --faces "%ROOT%\run-fixed-clone\mhr-lod1.faces.tsv" ^
  --candidate-bin "%C2%\candidate2-vertices.bin" ^
  --candidate-report "%C2%\candidate2-report.json" ^
  --skeleton "%OUT%\mhr-official-127-skeleton.tsv" ^
  --output-dir "%OUT%" --label candidate2 1>"%OUT%\audit-stdout.json" 2>"%OUT%\audit-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\audit-exit-code.txt" echo %STEP%
exit /b %STEP%
