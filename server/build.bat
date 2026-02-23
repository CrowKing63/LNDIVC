@echo off
chcp 65001 > nul
echo.
echo =====================================================
echo   LNDIVC PyInstaller 빌드
echo =====================================================
echo.
echo   이 스크립트는 LNDIVC.zip 배포 패키지를 생성합니다.
echo   사용자는 ZIP을 풀고 LNDIVC.exe 를 실행하면 됩니다.
echo.

:: Python 확인
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo        https://python.org 에서 Python 3.11 이상을 설치하세요.
    pause
    exit /b 1
)

:: 가상환경 없으면 자동 생성
if not exist ".venv\Scripts\activate.bat" (
    echo [1/4] 가상환경 생성 중...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [오류] 가상환경 생성 실패.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    echo [2/4] 의존성 설치 중... (최초 1회, 수 분 소요)
    pip install -r requirements.txt -q
    if %errorlevel% neq 0 (
        echo [오류] 의존성 설치 실패.
        pause
        exit /b 1
    )
) else (
    echo [1/4] 가상환경 확인 완료.
    call .venv\Scripts\activate.bat
    echo [2/4] 의존성 확인 중...
    pip install -r requirements.txt -q
)

:: PyInstaller 설치
echo [3/4] PyInstaller 설치 중...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo [오류] PyInstaller 설치 실패.
    pause
    exit /b 1
)

:: 이전 빌드 정리
echo      이전 빌드 정리 중...
if exist "dist\LNDIVC"     rmdir /s /q "dist\LNDIVC"
if exist "build"           rmdir /s /q "build"
if exist "dist\LNDIVC.zip" del /q "dist\LNDIVC.zip"

:: 빌드 실행
echo [4/4] 빌드 중... (수 분 소요)
pyinstaller LNDIVC.spec --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo [오류] 빌드 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

:: ZIP 패키지 생성
echo      ZIP 패키지 생성 중...
powershell -NoProfile -Command ^
  "Compress-Archive -Path 'dist\LNDIVC\*' -DestinationPath 'dist\LNDIVC.zip' -Force"
if %errorlevel% neq 0 (
    echo [경고] ZIP 생성 실패. dist\LNDIVC\ 폴더를 수동으로 압축하세요.
) else (
    echo      dist\LNDIVC.zip 생성 완료.
)

echo.
echo =====================================================
echo   빌드 완료!
echo =====================================================
echo.
echo   배포 파일: dist\LNDIVC.zip
echo.
echo   배포 방법:
echo   1. LNDIVC.zip 을 사용자에게 전달
echo   2. 압축 해제 후 LNDIVC.exe 실행 (Python 불필요)
echo   3. 첫 실행 시 설정 마법사가 자동으로 시작됩니다
echo.
echo   ※ OBS Studio 및 VB-Audio Virtual Cable은
echo     대상 PC에 별도 설치 필요
echo.
pause
