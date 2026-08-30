@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision"
set "PYTHON=C:\Users\hitos\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
set "B_DIR=%PROJECT_ROOT%\artifacts\pose-atlas-rebuild\2026-08-25\mhr-neutral-body-smoke-agent-b"
set "OUT=%AGENT_DIR%body-fit-candidate1"
if not exist "%OUT%" mkdir "%OUT%"
if errorlevel 1 exit /b 10
"%PYTHON%" "%AGENT_DIR%fit_body_candidate1.py" --vertices "%AGENT_DIR%run-fixed-clone\mhr-lod1.vertices.tsv" --faces "%AGENT_DIR%run-fixed-clone\mhr-lod1.faces.tsv" --offsets "%B_DIR%\ufbx-identity-45-sparse-offsets.tsv" --bands "%B_DIR%\pointcloud-contact-sheet-summary.json" --archive "%PROJECT_ROOT%\artifacts\third-party-downloads\MHR-v1.0.1-assets\assets.zip" --equivalence "%B_DIR%\body-identity-equivalence-summary.json" --output-dir "%OUT%" 1>"%OUT%\stdout.json" 2>"%OUT%\stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%OUT%\exit-code.txt" echo %STEP_EXIT%
exit /b %STEP_EXIT%
