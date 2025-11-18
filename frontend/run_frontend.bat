@echo off
REM Voice Assistant Frontend Startup Script

echo ===================================
echo Voice Assistant Frontend
echo ===================================
echo.

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies...
    call npm install
    echo.
)

REM Check if .env.local exists
if not exist ".env.local" (
    echo Warning: .env.local not found!
    if exist "env.local.example" (
        copy env.local.example .env.local
        echo Created .env.local from example
    )
    echo.
)

echo Starting Next.js development server...
echo Frontend will be available at: http://localhost:3000
echo.
echo Make sure backend is running at: http://localhost:8000
echo.
echo Press Ctrl+C to stop
echo.

npm run dev

