@echo off
setlocal
set "APP_FOLDER=%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $ws=New-Object -ComObject WScript.Shell; $desktop=[Environment]::GetFolderPath('Desktop'); $sc=$ws.CreateShortcut((Join-Path $desktop 'Hospeda.lnk')); $sc.TargetPath=Join-Path $env:APP_FOLDER 'iniciar_hospeda.bat'; $sc.WorkingDirectory=$env:APP_FOLDER; $sc.Description='Abre Hospeda y sus registros guardados en esta computadora'; $sc.IconLocation=(Join-Path $env:APP_FOLDER 'hospeda.ico') + ',0'; $sc.Save(); Write-Host 'Acceso directo creado en el escritorio.'"
if errorlevel 1 (
  echo No se pudo crear el acceso directo. Comprueba que esta carpeta incluya iniciar_hospeda.bat y hospeda.ico.
  pause
  exit /b 1
)
