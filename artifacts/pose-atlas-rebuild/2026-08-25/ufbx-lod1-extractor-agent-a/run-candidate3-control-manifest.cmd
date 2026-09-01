@echo off
setlocal
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\candidate3-yaw-controls-24"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
set "MANIFEST=%OUT%\candidate3-camera-anchor-control-manifest.json"
"%PYTHON%" "%ROOT%\build_candidate3_control_manifest.py" ^
  --controls-dir "%OUT%\controls" ^
  --candidate3-bin "%ROOT%\body-morph-candidate3\candidate3-vertices.bin" ^
  --candidate3-obj "%ROOT%\body-morph-candidate3\candidate3.obj" ^
  --candidate3-report "%ROOT%\body-morph-candidate3\candidate3-report.json" ^
  --candidate3-audit "%ROOT%\candidate3-anatomy-audit\candidate3-anatomy-audit.json" ^
  --candidate2-rejection "%ROOT%\candidate2-anatomy-audit\candidate2-anatomy-audit.json" ^
  --topology-qa "%OUT%\topology-continuity-qa.json" ^
  --legacy-iou-qa "%OUT%\qa-report-attempt1-strict-fail.json" ^
  --schema "%ROOT%\candidate3-camera-anchor-control-manifest.schema.json" ^
  --output "%MANIFEST%" 1>"%OUT%\control-manifest-build-stdout.json" 2>"%OUT%\control-manifest-build-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\control-manifest-build-exit-code.txt" echo %STEP%
if not "%STEP%"=="0" exit /b %STEP%
"%PYTHON%" "%ROOT%\validate_candidate3_control_manifest.py" --manifest "%MANIFEST%" --output "%OUT%\control-manifest-validation.json" 1>"%OUT%\control-manifest-validation-stdout.json" 2>"%OUT%\control-manifest-validation-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\control-manifest-validation-exit-code.txt" echo %STEP%
>"%OUT%\control-manifest-overall-exit-code.txt" echo %STEP%
exit /b %STEP%
