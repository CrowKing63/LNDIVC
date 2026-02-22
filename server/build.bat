@echo off
chcp 65001 > nul
echo.
echo =====================================================
echo   LNDIVC PyInstaller 빌드
echo =====================================================
echo.
echo   이 스크립트는 LNDIVC.exe 배포 패키지를 생성합니다.
echo   빌드 완료 후 dist\LNDIVC\ 폴더를 그대로 배포하세요.
echo.

:: 가상환경 확인
if not exist ".venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. 먼저 setup.bat 을 실행하세요.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

:: PyInstaller 설치
echo [1/2] PyInstaller 설치 중...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo [오류] PyInstaller 설치 실패.
    pause
    exit /b 1
)

:: 이전 빌드 정리
if exist "dist\LNDIVC" (
    echo      이전 빌드 삭제 중...
    rmdir /s /q "dist\LNDIVC"
)
if exist "build" (
    rmdir /s /q "build"
)

:: 빌드 실행
echo [2/2] 빌드 중... (수 분 소요)
pyinstaller LNDIVC.spec --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo [오류] 빌드 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

echo.
echo =====================================================
echo   빌드 완료!
echo =====================================================
echo.
echo   출력 폴더: dist\LNDIVC\
echo.
echo   배포 방법:
echo   1. dist\LNDIVC\ 폴더 전체를 대상 PC에 복사
echo   2. LNDIVC.exe 를 직접 실행 (Python 불필요)
echo.
echo   첫 실행 전 cert 설정:
echo   - LNDIVC.exe --setup  을 실행해 인증서를 설정하세요
echo     (Python 설치 불필요 — .exe 안에 내장됨)
echo.
echo   ※ OBS Studio 및 VB-Audio Virtual Cable은
echo     대상 PC에 별도 설치 필요
echo.
pause
