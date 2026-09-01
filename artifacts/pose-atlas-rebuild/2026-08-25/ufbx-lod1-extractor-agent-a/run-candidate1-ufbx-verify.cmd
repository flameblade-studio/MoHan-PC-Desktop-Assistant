@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision"
set "OUT=%AGENT_DIR%body-fit-candidate1"
set "B_DIR=%PROJECT_ROOT%\artifacts\pose-atlas-rebuild\2026-08-25\mhr-neutral-body-smoke-agent-b"
set "CALCULATOR=%B_DIR%\ufbx_body_identity_calculator.exe"
set "FBX=%PROJECT_ROOT%\artifacts\third-party-downloads\MHR-v1.0.1-assets\extracted\assets\lod1.fbx"
set "PYTHON=%USERPROFILE%\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
"%CALCULATOR%" "%FBX%" "%OUT%\candidate1-coefficients.tsv" "%OUT%\candidate1-ufbx-reconstruction.bin" 1>"%OUT%\ufbx-reconstruct-stdout.txt" 2>"%OUT%\ufbx-reconstruct-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%OUT%\ufbx-reconstruct-exit-code.txt" echo %STEP_EXIT%
if not "%STEP_EXIT%"=="0" exit /b %STEP_EXIT%
"%PYTHON%" "%AGENT_DIR%verify_candidate1_ufbx.py" --calculator-bin "%OUT%\candidate1-ufbx-reconstruction.bin" --coefficients "%OUT%\candidate1-coefficients.json" --obj "%OUT%\candidate1.obj" 1>"%OUT%\ufbx-verify-stdout.json" 2>"%OUT%\ufbx-verify-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%OUT%\ufbx-verify-exit-code.txt" echo %STEP_EXIT%
exit /b %STEP_EXIT%
