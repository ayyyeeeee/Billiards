@echo off
setlocal
cd /d "%~dp0"
python plot_publication_figures.py
if errorlevel 1 (
  echo Generation failed. See the error above.
) else (
  echo Figures saved in publication_figures.
)
pause
