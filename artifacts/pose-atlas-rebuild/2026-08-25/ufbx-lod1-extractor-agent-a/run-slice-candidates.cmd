@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "AGENT_DIR=%~dp0"
set "PROJECT_ROOT=D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision"
set "PYTHON=%PROJECT_ROOT%\tools\third_party\InstantMesh\.conda\python.exe"
set "BASE_VERTICES=%AGENT_DIR%run-fixed-clone\mhr-lod1.vertices.tsv"
set "FACES=%AGENT_DIR%run-fixed-clone\mhr-lod1.faces.tsv"
set "NEUTRAL_OBJ=%PROJECT_ROOT%\artifacts\pose-atlas-rebuild\2026-08-25\ufbx-lod1-extractor\mhr-zero-neutral-lod1.obj"
set "BAND_SUMMARY=%PROJECT_ROOT%\artifacts\pose-atlas-rebuild\2026-08-25\mhr-neutral-body-smoke-agent-b\pointcloud-contact-sheet-summary.json"
set "OUTPUT_DIR=%AGENT_DIR%cross-sections"
if not exist "%OUTPUT_DIR%" mkdir "%OUTPUT_DIR%"
if errorlevel 1 exit /b 10
"%PYTHON%" "%AGENT_DIR%slice_candidate_loops.py" --base-vertices "%BASE_VERTICES%" --faces "%FACES%" --neutral-obj "%NEUTRAL_OBJ%" --band-summary "%BAND_SUMMARY%" --output-dir "%OUTPUT_DIR%" 1>"%OUTPUT_DIR%\stdout.json" 2>"%OUTPUT_DIR%\stderr.txt"
set "STEP_EXIT=%ERRORLEVEL%"
>"%OUTPUT_DIR%\exit-code.txt" echo %STEP_EXIT%
exit /b %STEP_EXIT%
