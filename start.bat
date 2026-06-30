@echo off
title Diagrama Pantaneiro

echo ============================================
echo   Diagrama Pantaneiro - Iniciando...
echo ============================================
echo.

REM Verifica se .env existe
if not exist ".env" (
    echo [!] .env nao encontrado. Copiando .env.example...
    copy .env.example .env
    echo [!] Edite .env e gere um JWT_SECRET forte antes de subir.
    echo     python -c "import secrets; print(secrets.token_urlsafe(64))"
    pause
    exit /b 1
)

REM Verifica se Docker esta rodando
docker info >nul 2>&1
if errorlevel 1 (
    echo [!] Docker nao esta rodando. Abra o Docker Desktop primeiro.
    pause
    exit /b 1
)

echo [*] Subindo containers...
docker compose up --build -d

if errorlevel 1 (
    echo [!] Falha ao subir os containers.
    pause
    exit /b 1
)

echo.
echo ============================================
echo   Pronto!
echo   Frontend: http://localhost:8081
echo   API docs: http://localhost:8000/docs
echo.
echo   Para parar: docker compose down
echo   Para ver logs: docker compose logs -f
echo ============================================

pause
