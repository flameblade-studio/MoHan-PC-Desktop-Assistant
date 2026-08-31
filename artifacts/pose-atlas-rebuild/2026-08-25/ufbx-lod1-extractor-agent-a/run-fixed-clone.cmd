@echo off
setlocal EnableExtensions DisableDelayedExpansion

set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision"
set "UFBX_DIR=%PROJECT_ROOT%\artifacts\third-party-downloads\ufbx-v0.23.0"
set "INPUT_FBX=%PROJECT_ROOT%\artifacts\third-party-downloads\MHR-v1.0.1-assets\extracted\assets\lod1.fbx"
set "RUN_DIR=%AGENT_DIR%run-fixed-clone"
set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat"

if not exist "%UFBX_DIR%\ufbx.c" exit /b 10
if not exist "%UFBX_DIR%\ufbx.h" exit /b 11
if not exist "%UFBX_DIR%\LICENSE" exit /b 12
if not exist "%INPUT_FBX%" exit /b 13
if not exist "%VCVARS%" exit /b 14
if not exist "%RUN_DIR%" mkdir "%RUN_DIR%"
if errorlevel 1 exit /b 15

call "%VCVARS%" 1>"%RUN_DIR%\vcvars-stdout.txt" 2>"%RUN_DIR%\vcvars-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%RUN_DIR%\vcvars-exit-code.txt" echo %STEP_EXIT%
if not "%STEP_EXIT%"=="0" exit /b %STEP_EXIT%

cl.exe /nologo /std:c11 /O2 /W3 /c "%UFBX_DIR%\ufbx.c" /Fo"%RUN_DIR%\ufbx.obj" 1>"%RUN_DIR%\compile-ufbx-stdout.txt" 2>"%RUN_DIR%\compile-ufbx-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%RUN_DIR%\compile-ufbx-exit-code.txt" echo %STEP_EXIT%
if not "%STEP_EXIT%"=="0" exit /b %STEP_EXIT%

cl.exe /nologo /std:c11 /O2 /W4 /WX /I"%UFBX_DIR%" /c "%AGENT_DIR%extract_lod1.c" /Fo"%RUN_DIR%\extract_lod1.obj" 1>"%RUN_DIR%\compile-extractor-stdout.txt" 2>"%RUN_DIR%\compile-extractor-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%RUN_DIR%\compile-extractor-exit-code.txt" echo %STEP_EXIT%
if not "%STEP_EXIT%"=="0" exit /b %STEP_EXIT%

link.exe /nologo "%RUN_DIR%\extract_lod1.obj" "%RUN_DIR%\ufbx.obj" /OUT:"%RUN_DIR%\extract_lod1.exe" 1>"%RUN_DIR%\link-stdout.txt" 2>"%RUN_DIR%\link-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%RUN_DIR%\link-exit-code.txt" echo %STEP_EXIT%
if not "%STEP_EXIT%"=="0" exit /b %STEP_EXIT%

"%RUN_DIR%\extract_lod1.exe" "%INPUT_FBX%" "%RUN_DIR%\mhr-lod1" 1>"%RUN_DIR%\extract-stdout.json" 2>"%RUN_DIR%\extract-stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%RUN_DIR%\extract-exit-code.txt" echo %STEP_EXIT%
exit /b %STEP_EXIT%
