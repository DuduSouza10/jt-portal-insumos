@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Portal de Insumos - J&T Express

echo ==============================================
echo  Portal de Insumos - J^&T Express
echo ==============================================
echo.

if not exist .venv\Scripts\python.exe (
  echo Criando ambiente local...
  py -m venv .venv
  if errorlevel 1 (
    echo.
    echo Nao consegui criar o ambiente com py.
    echo Tentando com python...
    python -m venv .venv
  )
)

if not exist .venv\Scripts\python.exe (
  echo.
  echo ERRO: Nao consegui criar o ambiente virtual.
  echo Verifique se o Python esta instalado e marcado no PATH.
  pause
  exit /b 1
)

echo Atualizando pip...
.venv\Scripts\python.exe -m pip install --upgrade pip

echo Instalando dependencias...
.venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Abrindo o portal...
.venv\Scripts\python.exe app.py

echo.
pause
