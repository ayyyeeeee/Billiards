@echo off
setlocal
set "APP=%~dp0learning_curves.py"
set "PYW=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\pythonw.exe"
REM Prefer installed Python with a complete scientific stack for robust fits.
python -c "import numpy, scipy, pandas, matplotlib" >nul 2>nul
if not errorlevel 1 goto :system_python
if exist "%PYW%" (
    start "" "%PYW%" "%APP%" --gui
    exit /b
)
where pythonw.exe >nul 2>nul
if not errorlevel 1 (
    start "" pythonw.exe "%APP%" --gui
    exit /b
)
echo Python was not found. Please install Python 3.12 or restore the Codex Python runtime.
pause

:system_python
for /f "delims=" %%P in ('python -c "import sys;print(sys.executable)"') do set "ROBUST_PY=%%P"
for %%P in ("%ROBUST_PY%") do set "ROBUST_PYW=%%~dpPpythonw.exe"
start "" "%ROBUST_PYW%" "%APP%" --gui
exit /b
