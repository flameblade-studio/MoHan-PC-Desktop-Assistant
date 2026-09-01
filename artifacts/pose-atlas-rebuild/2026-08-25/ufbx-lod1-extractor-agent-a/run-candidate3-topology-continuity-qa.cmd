@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\candidate3-yaw-controls-24"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
"%PYTHON%" "%ROOT%\qa_candidate3_topology_continuity.py" ^
  --vertices "%ROOT%\body-morph-candidate3\candidate3-vertices.bin" ^
  --controls "%OUT%\controls" ^
  --manifest "%OUT%\manifest.json" ^
  --legacy-qa "%OUT%\qa-report-attempt1-strict-fail.json" ^
  --projections "%OUT%\candidate3-vertex-projections.npz" ^
  --report "%OUT%\topology-continuity-qa.json" 1>"%OUT%\topology-continuity-stdout.json" 2>"%OUT%\topology-continuity-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\topology-continuity-exit-code.txt" echo %STEP%
exit /b %STEP%
