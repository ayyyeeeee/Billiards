@echo off
setlocal
cd /d "%~dp0..\.."
python -m plots.participant_learning.app --all
if errorlevel 1 goto :failed
python -m plots.baseline_transfer.robust_comparison
if errorlevel 1 goto :failed
echo Robust analysis complete. See results.
pause
exit /b 0
:failed
echo Analysis failed.
pause
exit /b 1
