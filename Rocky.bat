@echo off
setlocal
pushd "%~dp0"
if errorlevel 1 goto failed
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\Launch-Rocky.ps1" %*
set "ROCKY_EXIT=%ERRORLEVEL%"
popd
if not "%ROCKY_EXIT%"=="0" pause
exit /b %ROCKY_EXIT%
:failed
echo Cannot open the Rocky folder. Move the full project to a writable local folder.
pause
exit /b 1
