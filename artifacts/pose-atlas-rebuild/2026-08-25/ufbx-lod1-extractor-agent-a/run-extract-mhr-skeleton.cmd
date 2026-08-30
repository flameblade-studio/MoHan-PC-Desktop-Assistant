@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor-agent-a"
set "OUT=%ROOT%\candidate2-anatomy-audit"
set "UFBX=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\third-party-downloads\ufbx-v0.23.0"
set "FBX=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\third-party-downloads\MHR-v1.0.1-assets\extracted\assets\lod1.fbx"
set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"
if not exist "%OUT%" mkdir "%OUT%"
call "%VCVARS%" 1>"%OUT%\vcvars-stdout.txt" 2>"%OUT%\vcvars-stderr.txt"
if errorlevel 1 exit /b %ERRORLEVEL%
cl.exe /nologo /std:c11 /O2 /W4 /WX /I"%UFBX%" "%ROOT%\extract_mhr_skeleton.c" "%UFBX%\ufbx.c" /Fe:"%OUT%\extract_mhr_skeleton.exe" 1>"%OUT%\compile-stdout.txt" 2>"%OUT%\compile-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\compile-exit-code.txt" echo %STEP%
if not "%STEP%"=="0" exit /b %STEP%
"%OUT%\extract_mhr_skeleton.exe" "%FBX%" "%OUT%\mhr-official-127-skeleton.tsv" 1>"%OUT%\extract-stdout.json" 2>"%OUT%\extract-stderr.txt"
set "STEP=%ERRORLEVEL%"
>"%OUT%\extract-exit-code.txt" echo %STEP%
exit /b %STEP%
