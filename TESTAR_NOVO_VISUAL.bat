@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Portal de Insumos - J&T Express (teste local)

echo ==============================================
echo  Portal de Insumos - J^&T Express
echo  Teste local do novo visual
echo ==============================================
echo.

set "PY="
where py >nul 2>nul && set "PY=py"
if not defined PY where python >nul 2>nul && set "PY=python"
if not defined PY (
  echo ERRO: Python nao encontrado.
  echo Instale o Python 3.10 ou mais novo em python.org e marque "Add Python to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Criando ambiente local ^(so na primeira vez^)...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo ERRO: nao consegui criar o ambiente virtual.
    pause
    exit /b 1
  )
)

if not exist ".venv\.dependencias_ok" (
  echo Instalando dependencias ^(so na primeira vez, pode demorar um pouco^)...
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo ERRO ao instalar dependencias. Verifique a internet e tente de novo.
    pause
    exit /b 1
  )
  echo ok> ".venv\.dependencias_ok"
)

set DISABLE_AUTO_INSTALL=1
set DATABASE_DRIVER=sqlite
echo.
echo Abrindo o portal... o navegador abre sozinho.
echo Login de teste: usuario dev / senha Dev@123
echo Se o visual parecer antigo, aperte Ctrl+F5 na pagina.
echo Para encerrar, feche esta janela ou aperte Ctrl+C.
echo.
".venv\Scripts\python.exe" app.py

echo.
pause
