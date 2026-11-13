@echo off
setlocal
cd /d "%~dp0..\.."
python learning_curve_tool\learning_curves.py --all
if errorlevel 1 goto :failed
python plot_baseline_vs_transfer.py --out baseline_vs_transfer_robust
if errorlevel 1 goto :failed
echo Robust analysis complete. See learning_curves and baseline_vs_transfer_robust.
pause
exit /b 0
:failed
echo Analysis failed. Please inspect the error above.
pause
exit /b 1
