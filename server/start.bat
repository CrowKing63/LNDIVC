@echo off
chcp 65001 > nul

:: 가상환경 확인
if not exist ".venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. 먼저 setup.bat 을 실행하세요.
    pause
    exit /b 1
)

:: 인증서 확인
if not exist "cert.pem" (
    echo [오류] cert.pem 이 없습니다. 먼저 setup.bat 을 실행하세요.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat
python server.py
pause
