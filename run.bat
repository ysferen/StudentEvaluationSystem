@echo off
echo Starting Student Evaluation System Development Servers...
echo.

REM Activate virtual environment and start Django in new window
echo Starting Django Backend Server...
start "Django Server" cmd /k "cd backend\venv\Scripts\ && activate.bat && cd ..\..\student_evaluation_system\ && python manage.py runserver"

REM Wait a moment for Django to start
timeout /t 3 /nobreak >nul

REM Start Frontend in new window
echo Starting Frontend Development Server...
start "Frontend Server" cmd /k "cd frontend\ && npm run dev"

echo.
echo Both servers are starting in separate windows:
echo - Django Backend: http://127.0.0.1:8000
echo - Frontend: http://localhost:5173 (or as shown in frontend window)
echo.
echo Close this window anytime. The servers will continue running in their own windows.
echo Press any key to exit this launcher...
pause >nul
