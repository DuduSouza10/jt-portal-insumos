@echo off
setlocal
cd /d "%~dp0"

echo ===============================================
echo  J^&T Express - Ambiente limpo Flask + SQLite
echo ===============================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo [1/4] Removendo ambiente antigo, se existir...
if exist .venv rmdir /s /q .venv

echo [2/4] Criando ambiente virtual .venv...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo ERRO: nao consegui criar o ambiente virtual. Instale o Python e marque a opcao PATH.
    pause
    exit /b 1
)

echo [3/4] Instalando dependencias minimas...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: falha ao instalar dependencias.
    pause
    exit /b 1
)

echo [4/4] Configurando VS Code para usar o .venv...
if not exist ".vscode" mkdir ".vscode"
> ".vscode\settings.json" echo {
>> ".vscode\settings.json" echo   "python.defaultInterpreterPath": "${workspaceFolder}\\.venv\\Scripts\\python.exe",
>> ".vscode\settings.json" echo   "python.terminal.activateEnvironment": true,
>> ".vscode\settings.json" echo   "python.analysis.typeCheckingMode": "basic",
>> ".vscode\settings.json" echo   "python.analysis.autoSearchPaths": true,
>> ".vscode\settings.json" echo   "python.analysis.useLibraryCodeForTypes": true
>> ".vscode\settings.json" echo }

python -c "import flask; print('Flask OK. Ambiente configurado.')"

echo.
echo Pronto. Agora feche e abra o VS Code nessa pasta.
echo Se ainda aparecer erro, aperte Ctrl+Shift+P, Python: Select Interpreter, e selecione .venv\Scripts\python.exe.
echo.
pause
