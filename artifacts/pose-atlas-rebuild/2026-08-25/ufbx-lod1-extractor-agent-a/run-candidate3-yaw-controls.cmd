@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\candidate3-yaw-controls-24"
set "RAW=%OUT%\raw-netpbm"
set "CONTROLS=%OUT%\controls"
set "PYTHON=C:\Users\hitos\AppData\Local\Comfy-Desktop\ComfyUI-Installs\ComfyUI\ComfyUI\.venv\Scripts\python.exe"
set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
set "UFBX=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\third-party-downloads\ufbx-v0.23.0"
set "FBX=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\third-party-downloads\MHR-v1.0.1-assets\extracted\assets\lod1.fbx"
set "RENDERER_SOURCE=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\mhr-neutral-body-smoke-agent-b\cpu_yaw_control_renderer.c"
set "PACKAGER=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\mhr-neutral-body-smoke-agent-b\package_cpu_yaw_controls.py"
if not exist "%OUT%" mkdir "%OUT%"
if not exist "%RAW%" mkdir "%RAW%"
if not exist "%CONTROLS%" mkdir "%CONTROLS%"

"%PYTHON%" "%ROOT%\adapt_candidate3_renderer_vertices.py" --source "%ROOT%\body-morph-candidate3\candidate3-vertices.bin" --output "%OUT%\candidate3-renderer-vertices.bin" 1>"%OUT%\adapt-stdout.json" 2>"%OUT%\adapt-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\adapt-exit-code.txt" echo %STEP%
if not "%STEP%"=="0" exit /b %STEP%

call "%VCVARS%" 1>"%OUT%\vcvars-stdout.txt" 2>"%OUT%\vcvars-stderr.txt"
if errorlevel 1 exit /b %ERRORLEVEL%
cl.exe /nologo /std:c11 /O2 /W3 /DWIDTH=1024 /DHEIGHT=1536 /I"%UFBX%" "%RENDERER_SOURCE%" "%UFBX%\ufbx.c" /Fe:"%OUT%\candidate3-cpu-yaw-renderer.exe" 1>"%OUT%\compile-stdout.txt" 2>"%OUT%\compile-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\compile-exit-code.txt" echo %STEP%
if not "%STEP%"=="0" exit /b %STEP%

"%OUT%\candidate3-cpu-yaw-renderer.exe" "%OUT%\candidate3-renderer-vertices.bin" "%FBX%" "%RAW%" 1>"%OUT%\render-stdout.txt" 2>"%OUT%\render-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\render-exit-code.txt" echo %STEP%
if not "%STEP%"=="0" exit /b %STEP%

"%PYTHON%" "%PACKAGER%" --raw "%RAW%" --controls "%CONTROLS%" --contact-sheet "%OUT%\normal-contact-sheet.png" --manifest "%OUT%\manifest.json" --vertices "%ROOT%\body-morph-candidate3\candidate3-vertices.bin" --renderer-vertices "%OUT%\candidate3-renderer-vertices.bin" --topology "%FBX%" 1>"%OUT%\package-stdout.json" 2>"%OUT%\package-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\package-exit-code.txt" echo %STEP%
if not "%STEP%"=="0" exit /b %STEP%

"%PYTHON%" "%ROOT%\qa_candidate3_yaw_controls.py" --controls "%CONTROLS%" --manifest "%OUT%\manifest.json" --contact-sheet "%OUT%\candidate3-controls-contact-sheet.png" --report "%OUT%\qa-report.json" 1>"%OUT%\qa-stdout.json" 2>"%OUT%\qa-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\qa-exit-code.txt" echo %STEP%
>"%OUT%\overall-exit-code.txt" echo %STEP%
exit /b %STEP%
