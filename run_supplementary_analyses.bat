@echo off
setlocal
cd /d "%~dp0"
python -m plots.supplementary.batch %*
if errorlevel 1 (echo Analysis failed.) else (echo Figures saved in results/supplementary_figures.)
pause
