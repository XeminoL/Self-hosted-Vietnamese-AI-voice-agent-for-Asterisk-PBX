@echo off
title Vietnamese voice switchboard
setlocal

set DISTRO=Ubuntu

where wsl >nul 2>&1 || goto :no_wsl

wsl -d %DISTRO% -e true >nul 2>&1 || goto :no_distro

for /f "usebackq delims=" %%i in (`wsl -d %DISTRO% -e wslpath -a "%~dp0."`) do set PROJECT=%%i

wsl -d %DISTRO% --cd "%PROJECT%" -e bash ./run.sh
set CODE=%ERRORLEVEL%

echo.
if not "%CODE%"=="0" echo The switchboard stopped with error code %CODE%. Look in the logs folder.
echo Press any key to close this window.
pause >nul
exit /b %CODE%

:no_wsl
echo WSL is not installed on this machine.
echo Install it from an admin PowerShell with:  wsl --install
echo.
pause
exit /b 1

:no_distro
echo The WSL distro "%DISTRO%" is not available.
echo Run  wsl -l -v  to see which ones you have, then edit DISTRO at the top of this file.
echo.
pause
exit /b 1