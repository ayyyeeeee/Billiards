@echo off
setlocal
cd /d "%~dp0"
python -m plots.publication.dynamics %*
if errorlevel 1 (echo Analysis failed.) else (echo Figures saved in results/publication_figures.)
pause
