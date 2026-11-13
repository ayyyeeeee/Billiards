@echo off
setlocal
cd /d "%~dp0"
python plot_supplementary_analyses.py
if errorlevel 1 (
  echo Generation failed. See the error above.
) else (
  echo Figures saved in supplementary_figures.
)
pause
