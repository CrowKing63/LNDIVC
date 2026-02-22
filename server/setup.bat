@echo off
chcp 65001 > nul
echo.
echo =====================================================
echo   LNDIVC 최초 설치 (setup.bat)
echo =====================================================
echo.

:: Python 확인
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo        https://www.python.org 에서 Python 3.11+ 설치 후 재실행
    pause
    exit /b 1
)

:: 가상환경 생성 (없으면)
if not exist ".venv" (
    echo [1/3] Python 가상환경 생성 중...
    python -m venv .venv
) else (
    echo [1/3] 가상환경이 이미 존재합니다.
)

:: 의존성 설치
echo [2/3] Python 패키지 설치 중... (수 분 소요)
call .venv\Scripts\activate.bat
pip install --upgrade pip -q
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [오류] 패키지 설치 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

:: 인증서 설정 마법사 실행 (Tailscale 또는 자체 서명 선택)
echo [3/3] 인증서 설정 중...
python setup_wizard.py
if %errorlevel% neq 0 (
    echo [오류] 인증서 설정 실패.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   설치 완료! 추가 준비 사항
echo =====================================================
echo.
echo   1. OBS Studio 설치 (가상 카메라 드라이버 포함)
echo      https://obsproject.com
echo      - 설치 후 OBS 실행 → 도구 → 가상 카메라 시작
echo      - 이후 OBS를 닫아도 가상 카메라는 동작합니다
echo.
echo   2. [선택] VB-Audio Virtual Cable 설치 (Zoom 마이크 연동용)
echo      https://vb-audio.com/Cable
echo.
echo   3. start.bat 실행 → Vision Pro Safari에서 위 주소 접속
echo.
pause
