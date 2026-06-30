@echo off
title Diagrama Pantaneiro - Parando...

echo ============================================
echo   Diagrama Pantaneiro - Parando...
echo ============================================
echo.

echo [*] Derrubando containers...
docker compose down

if errorlevel 1 (
    echo [!] Falha ao parar os containers.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Servicos parados.
echo ============================================

pause
