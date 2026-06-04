@echo off
chcp 65001 >nul
title Analise Futebol IA - NAO FECHE esta janela enquanto estiver usando o app
set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not exist "%PY%" set "PY=python"
cd /d "%~dp0"
echo.
echo   ===============================================
echo     ANALISE FUTEBOL IA
echo   ===============================================
echo.
echo   Iniciando... o navegador vai abrir sozinho.
echo   Endereco: http://localhost:8765
echo   (Se nao abrir, copie esse endereco no navegador.)
echo.
echo   IMPORTANTE: nao feche esta janela enquanto usar o app.
echo.
"%PY%" server.py
echo.
echo   Servidor encerrado. Pode fechar esta janela.
pause
