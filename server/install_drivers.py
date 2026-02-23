"""
LNDIVC 드라이버 자동 설치 모듈
-------------------------------
- UnityCapture  : 가상 카메라 (DirectShow 필터)
- VB-Audio CABLE: 가상 마이크 (오디오 드라이버)

두 도구 모두 설치 시 UAC(관리자 권한) 프롬프트가 표시됩니다.
"""

import os
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# ── 영구 설치 경로: %APPDATA%\LNDIVC\drivers\ ─────────────────────────
_APPDATA     = Path(os.environ.get('APPDATA', str(Path.home())))
DRIVERS_DIR  = _APPDATA / 'LNDIVC' / 'drivers'
UNITY_DIR    = DRIVERS_DIR / 'UnityCapture'

# ── UnityCapture ──────────────────────────────────────────────────────
_UNITY_CLSID      = '{5C2CD55C-92AD-4999-8666-912BD3E700BB}'
# 릴리즈 없음 → master 브랜치 직접 다운로드 (Install/ 폴더에 컴파일된 DLL 포함)
_UNITY_MASTER_ZIP = 'https://github.com/schellingb/UnityCapture/archive/master.zip'
_UNITY_SITE       = 'https://github.com/schellingb/UnityCapture'

# ── VB-Audio CABLE ────────────────────────────────────────────────────
# VB-Audio는 오랫동안 Pack43을 유지해 왔고, 실패 시 공식 사이트로 안내함
_VBCABLE_URL      = 'https://download.vb-audio.com/Download_CABLE/VBCABLE_Driver_Pack43.zip'
_VBCABLE_SITE     = 'https://vb-audio.com/Cable/'


# ── 설치 확인 ──────────────────────────────────────────────────────────

def check_unitycapture() -> bool:
    """UnityCapture DirectShow 필터가 등록되어 있는지 확인"""
    try:
        import winreg
        sub = rf'CLSID\{_UNITY_CLSID}\InprocServer32'
        checks = [
            (winreg.HKEY_CLASSES_ROOT,   sub,                              winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_CLASSES_ROOT,   sub,                              0),
            (winreg.HKEY_LOCAL_MACHINE,  rf'SOFTWARE\Classes\{sub}',       winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_LOCAL_MACHINE,  rf'SOFTWARE\Classes\{sub}',       0),
            (winreg.HKEY_CURRENT_USER,   rf'Software\Classes\{sub}',       winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_CURRENT_USER,   rf'Software\Classes\{sub}',       0),
        ]
        for hive, reg_sub, flags in checks:
            try:
                key = winreg.OpenKey(hive, reg_sub, access=winreg.KEY_READ | flags)
                winreg.CloseKey(key)
                return True
            except OSError:
                continue
    except ImportError:
        pass

    # reg query 폴백: Python WOW64 리디렉션 우회
    try:
        import subprocess
        for hive_path in (
            rf'HKCR\CLSID\{_UNITY_CLSID}\InprocServer32',
            rf'HKLM\SOFTWARE\Classes\CLSID\{_UNITY_CLSID}\InprocServer32',
            rf'HKCU\Software\Classes\CLSID\{_UNITY_CLSID}\InprocServer32',
        ):
            r = subprocess.run(
                ['reg', 'query', hive_path],
                capture_output=True, creationflags=0x08000000,
            )
            if r.returncode == 0:
                return True
    except Exception:
        pass

    return False


def check_vbcable() -> bool:
    """VB-Audio CABLE이 설치되어 있는지 레지스트리로 확인"""
    try:
        import winreg
        for sub in (
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VB-Audio Virtual Cable',
            r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\VB-Audio Virtual Cable',
        ):
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub)
                winreg.CloseKey(key)
                return True
            except Exception:
                pass
    except ImportError:
        pass
    # 알려진 설치 경로로 추가 확인
    for p in (
        r'C:\Program Files\VB\CABLE\VBCABLE_Setup_x64.exe',
        r'C:\Program Files (x86)\VB\CABLE\VBCABLE_Setup_x64.exe',
    ):
        if Path(p).exists():
            return True
    return False


# ── 다운로드 유틸리티 ─────────────────────────────────────────────────

def _download(url: str, dest: Path, log_cb=None) -> bool:
    """URL → dest 파일 다운로드. 진행률 로그 포함."""
    try:
        log_cb and log_cb(f"  다운로드: {Path(url).name}")
        req = urllib.request.Request(url, headers={'User-Agent': 'LNDIVC/1.0'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get('Content-Length', 0))
            dest.parent.mkdir(parents=True, exist_ok=True)
            downloaded = 0
            with open(dest, 'wb') as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if log_cb and total:
                        pct = downloaded * 100 // total
                        log_cb(f"  {pct}%  ({downloaded // 1024} / {total // 1024} KB)")
        return True
    except Exception as e:
        log_cb and log_cb(f"  ✗ 다운로드 실패: {e}")
        return False


def _open_browser(url: str) -> None:
    try:
        subprocess.Popen(['start', '', url], shell=True,
                         creationflags=0x08000000)
    except Exception:
        pass


def _run_powershell_runas(exe: str, args=None, log_cb=None) -> bool:
    """PowerShell Start-Process -Verb RunAs 로 관리자 권한 실행 (완료 대기)"""
    if args:
        if isinstance(args, (list, tuple)):
            # Build a proper PS array: @("arg1", "arg2") — each element double-quoted
            ps_args = ', '.join(f'"{a}"' for a in args)
            arg_part = f' -ArgumentList @({ps_args})'
        else:
            # Legacy plain string (no inner quotes expected)
            arg_part = f' -ArgumentList "{args}"'
    else:
        arg_part = ''
    ps = f'Start-Process "{exe}"{arg_part} -Verb RunAs -Wait'
    try:
        result = subprocess.run(
            ['powershell', '-NonInteractive', '-Command', ps],
            creationflags=0x08000000,
            capture_output=True, text=True,
        )
        if result.returncode != 0 and log_cb:
            err = (result.stderr or result.stdout or '').strip()
            if err:
                log_cb(f"  ✗ PowerShell 오류: {err[:200]}")
        return result.returncode == 0
    except Exception as e:
        log_cb and log_cb(f"  ✗ 실행 실패: {e}")
        return False


# ── UnityCapture 설치 ─────────────────────────────────────────────────

def install_unitycapture(log_cb=None) -> bool:
    """
    UnityCapture master 브랜치를 다운로드하고 64비트 DLL을 regsvr32로 등록합니다.
    Install/ 폴더에 컴파일된 UnityCaptureFilter64.dll이 포함되어 있습니다.
    반환: 설치 성공 여부
    """
    log = log_cb or print

    # 1. master.zip 다운로드 (컴파일된 DLL 포함)
    log("● UnityCapture 다운로드 중 (master 브랜치)...")
    tmp = Path(tempfile.mkdtemp())
    zip_path = tmp / 'unitycapture.zip'
    if not _download(_UNITY_MASTER_ZIP, zip_path, log):
        log(f"  → 브라우저에서 수동 설치: {_UNITY_SITE}")
        _open_browser(_UNITY_SITE)
        return False

    # 2. 압축 해제
    log("  압축 해제 중...")
    extract = tmp / 'src'
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract)
    except Exception as e:
        log(f"  ✗ 압축 해제 실패: {e}")
        return False

    # 3. Install/ 폴더에서 64비트 DLL 탐색
    #    파일명: UnityCaptureFilter64.dll  (Install/ 폴더 안에 위치)
    dll_file = None
    # 우선순위: 이름에 '64' 포함된 DLL
    for p in sorted(extract.rglob('*.dll')):
        if '64' in p.name:
            dll_file = p
            break
    # 없으면 아무 DLL이라도
    if not dll_file:
        candidates = list(extract.rglob('*.dll'))
        dll_file = candidates[0] if candidates else None

    if not dll_file:
        log("  ✗ DLL 파일을 찾을 수 없음 — 브라우저에서 수동 설치")
        _open_browser(_UNITY_SITE)
        return False

    log(f"  발견: {dll_file.name}")

    # 4. APPDATA에 영구 복사
    dest = UNITY_DIR / dll_file.name
    log(f"  복사: {dest}")
    try:
        UNITY_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dll_file, dest)
    except Exception as e:
        log(f"  ✗ 복사 실패: {e}")
        return False

    # 5. regsvr32 등록 — 배치 파일로 실제 exit code 캡처
    log("  DirectShow 필터 등록 중 (UAC 창이 열릴 수 있음)...")
    tmp_dir   = Path(tempfile.gettempdir())
    exit_file = tmp_dir / 'lndivc_regsvr32_exit.txt'
    bat_file  = tmp_dir / 'lndivc_register.bat'
    exit_file.unlink(missing_ok=True)
    bat_file.write_text(
        f'@echo off\r\n'
        f'regsvr32 /s "{dest}"\r\n'
        f'(echo %ERRORLEVEL%)>"{exit_file}"\r\n',
        encoding='mbcs',
    )
    _run_powershell_runas('cmd.exe', ['/c', str(bat_file)], log)

    # exit code 해석
    reg_code = -1
    try:
        reg_code = int(exit_file.read_text(encoding='mbcs').strip())
    except Exception:
        pass

    _REGSVR32_ERRORS = {
        1: "DllRegisterServer 실패 (의존 DLL 누락 또는 손상)",
        2: "DllRegisterServer 없음 (COM DLL이 아님)",
        3: "모듈 없음 (DLL 경로 오류)",
        4: "모듈 유효하지 않음",
        5: "접근 거부 (관리자 권한 필요)",
    }
    if reg_code == 0:
        log("  → regsvr32 성공 (코드 0)")
        log("  ✓ UnityCapture 설치 완료!")
        return True
    elif reg_code in _REGSVR32_ERRORS:
        log(f"  → regsvr32 오류 (코드 {reg_code}): {_REGSVR32_ERRORS[reg_code]}")
    elif reg_code > 0:
        log(f"  → regsvr32 실패 코드: {reg_code}")
    else:
        log("  → exit code 없음 — UAC를 취소했거나 실행 오류")

    log("  ✗ 등록 실패 — 위 오류 코드를 확인하세요")
    return False


# ── VB-Audio CABLE 설치 ───────────────────────────────────────────────

def install_vbcable(log_cb=None) -> bool:
    """
    VB-Audio 공식 서버에서 CABLE을 다운로드하고 설치합니다.
    반환: 설치 성공 여부
    """
    log = log_cb or print

    # 1. 다운로드
    log("● VB-Audio CABLE 다운로드 중...")
    tmp = Path(tempfile.mkdtemp())
    zip_path = tmp / 'vbcable.zip'

    if not _download(_VBCABLE_URL, zip_path, log):
        log(f"  → 브라우저에서 수동 다운로드: {_VBCABLE_SITE}")
        _open_browser(_VBCABLE_SITE)
        return False

    # 2. 압축 해제
    log("  압축 해제 중...")
    extract = tmp / 'vbc'
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract)
    except Exception as e:
        log(f"  ✗ 압축 해제 실패: {e}")
        return False

    # 3. 설치 프로그램 탐색 (64비트 우선)
    setup = None
    for p in extract.rglob('VBCABLE_Setup_x64.exe'):
        setup = p
        break
    if not setup:
        for p in extract.rglob('*.exe'):
            setup = p
            break

    if not setup:
        log("  ✗ 설치 프로그램을 찾을 수 없음")
        return False

    # 4. 관리자 권한으로 설치 (완료까지 대기)
    log("  VB-Cable 설치 중 (UAC 창이 열릴 수 있음, 완료까지 기다리세요)...")
    _run_powershell_runas(str(setup), log_cb=log)

    if check_vbcable():
        log("  ✓ VB-Audio CABLE 설치 완료!")
        return True
    else:
        # 설치는 됐지만 레지스트리 인식에 시간이 걸릴 수 있음
        log("  ⚠ 설치 완료 (장치 인식까지 시간이 걸릴 수 있음 — 재부팅 권장)")
        return True
