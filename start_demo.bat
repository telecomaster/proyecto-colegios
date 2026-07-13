@echo off
setlocal enabledelayedexpansion
echo ========================================
echo   Proyecto Colegios - Virtual Lab Assistant
echo ========================================
echo.
echo PREREQUISITE CHECK:
echo   - Docker Desktop must be running
echo   - Ollama must be installed and running natively
echo     Download: https://ollama.com/download
echo.

rem Debe coincidir con MODEL_NAME en docker-compose.yml / .env.
rem Si tienes una GPU dedicada (ej. RTX 3060) puedes usar un modelo mas
rem grande como llama3.1:8b editando esta linea Y la variable MODEL_NAME
rem en tu archivo .env (ver .env.example).
set MODEL_NAME=llama3.2:3b-instruct-q4_K_M
if exist .env (
    for /f "usebackq tokens=1,2 delims==" %%a in (`findstr /b "MODEL_NAME=" .env`) do set MODEL_NAME=%%b
)

rem Asume que el instalador de Ollama agrego "ollama" al PATH (comportamiento
rem por defecto). Si no es el caso, reemplazar por la ruta completa a ollama.exe.
set OLLAMA=ollama

echo [1/3] Checking Ollama and pulling model !MODEL_NAME!...
%OLLAMA% pull !MODEL_NAME!
if %errorlevel% neq 0 (
    echo WARNING: Could not pull model. Check your connection, or that 'ollama'
    echo          is in your PATH ^(edit OLLAMA= in this script otherwise^).
    pause
    exit /b 1
)

echo.
echo [2/3] Building and starting Docker containers...
docker compose up -d --build
if %errorlevel% neq 0 (
    echo ERROR: Docker compose failed. Is Docker Desktop running?
    pause
    exit /b 1
)

echo.
echo [3/3] Waiting for services to start...
timeout /t 15 /nobreak >nul

echo.
echo ========================================
echo   DEMO READY!
echo ========================================
echo.
echo   Frontend UI:  http://localhost:3000
echo   API Docs:     http://localhost:8000/docs
echo   API Health:   http://localhost:8000/health
echo.
start http://localhost:3000
pause
