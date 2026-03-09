@echo off
REM End-to-End Test Runner Script for Windows
REM Semantic Media Engine

setlocal enabledelayedexpansion

echo ==========================================
echo Semantic Media Engine - E2E Test Runner
echo ==========================================
echo.

REM Configuration
set BACKEND_URL=http://localhost:8000
set POSTGRES_DB=semantic_media

echo Step 1: Prerequisites Check
echo ----------------------------

REM Check PostgreSQL
echo Checking PostgreSQL...
pg_isready -h localhost -p 5432 >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PostgreSQL is not running
    echo Start PostgreSQL and try again
    exit /b 1
)
echo [OK] PostgreSQL is running

REM Check Qdrant
echo Checking Qdrant...
curl -s http://localhost:6333/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Qdrant is not running
    echo Start Qdrant with: docker run -p 6333:6333 qdrant/qdrant
    exit /b 1
)
echo [OK] Qdrant is running

echo.
echo Step 2: Backend Service Check
echo ------------------------------

REM Check if backend is running
echo Checking Backend API...
curl -s %BACKEND_URL%/health >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Backend is not running
    echo Please start it manually:
    echo   cd backend
    echo   venv\Scripts\activate
    echo   uvicorn main:app --reload
    echo.
    echo Press any key when backend is ready, or Ctrl+C to cancel...
    pause >nul
)
echo [OK] Backend API is running

echo.
echo Step 3: Running Automated Tests
echo --------------------------------

REM Run Python E2E tests
if exist test_e2e.py (
    python test_e2e.py --backend-url %BACKEND_URL% %*
    set TEST_EXIT_CODE=!errorlevel!
) else (
    echo [ERROR] test_e2e.py not found
    exit /b 1
)

echo.
if !TEST_EXIT_CODE! equ 0 (
    echo ==========================================
    echo All E2E tests passed!
    echo ==========================================
) else (
    echo ==========================================
    echo Some E2E tests failed
    echo ==========================================
)

exit /b !TEST_EXIT_CODE!
