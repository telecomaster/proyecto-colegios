@echo off
echo ========================================
echo   Proyecto Colegios - Virtual Lab Assistant
echo ========================================
echo.
echo PREREQUISITE CHECK:
echo   - Docker Desktop must be running
echo   - Ollama must be installed and running natively
echo     Download: https://ollama.com/download
echo.
set OLLAMA="C:\Users\renes\AppData\Local\Programs\Ollama\ollama.exe"

echo [1/3] Checking Ollama and pulling Llama 3 model...
%OLLAMA% pull llama3.2:1b
if %errorlevel% neq 0 (
    echo WARNING: Could not pull model. Check your connection.
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
