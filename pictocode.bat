@echo off
REM ——— Placez ce .bat à la racine du dossier pictocode ———
cd /d "%~dp0"

echo [pictocode] Vérification de pictocode.exe...
where pictocode.exe >nul 2>&1
if errorlevel 1 (
    echo ERREUR : pictocode.exe introuvable.
    echo Assurez-vous que le script pictocode.exe a bien été installé dans votre Python\Scripts.
    pause
    exit /b 1
)

echo [pictocode] Lancement de pictocode…
pictocode.exe %*
if errorlevel 1 (
    echo.
    echo ERREUR : échec du lancement de pictocode.
) else (
    echo.
    echo pictocode s’est terminé normalement.
)

pause
