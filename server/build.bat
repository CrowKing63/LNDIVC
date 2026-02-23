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

:: 가상환경 확인
if not exist ".venv\Scripts\activate.bat" (
    echo [오류] 가상환경이 없습니다. 먼저 setup.bat 을 실행하세요.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

:: PyInstaller 설치
echo [1/3] PyInstaller 설치 중...
pip install pyinstaller -q
if %errorlevel% neq 0 (
    echo [오류] PyInstaller 설치 실패.
    pause
    exit /b 1
)

:: 이전 빌드 정리
echo      이전 빌드 정리 중...
if exist "dist\LNDIVC" rmdir /s /q "dist\LNDIVC"
if exist "build"       rmdir /s /q "build"
if exist "dist\LNDIVC.zip" del /q "dist\LNDIVC.zip"

:: 빌드 실행
echo [2/3] 빌드 중... (수 분 소요)
pyinstaller LNDIVC.spec --noconfirm
if %errorlevel% neq 0 (
    echo.
    echo [오류] 빌드 실패. 위 오류 메시지를 확인하세요.
    pause
    exit /b 1
)

:: ZIP 패키지 생성
echo [3/3] ZIP 패키지 생성 중...
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
echo      - 언어 선택 후 인증서 설정 (Tailscale / 자체 서명)
echo      - 완료 후 트레이 아이콘으로 서버 관리
echo.
echo   ※ OBS Studio 및 VB-Audio Virtual Cable은
echo     대상 PC에 별도 설치 필요
echo.
pause
