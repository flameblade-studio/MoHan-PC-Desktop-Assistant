@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "AGENT_DIR=%~dp0"
set "RUN_DIR=%AGENT_DIR%run-fixed-clone"
set "UFBX_DIR=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision\artifacts\third-party-downloads\ufbx-v0.23.0"
call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 10
where cl.exe
cl.exe /nologo /Bv /std:c11 /O2 /W4 /WX /I"%UFBX_DIR%" /c "%AGENT_DIR%extract_lod1.c" /Fo"%RUN_DIR%\compiler-probe.obj"
exit /b %ERRORLEVEL%
