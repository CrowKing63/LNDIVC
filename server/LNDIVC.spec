# -*- mode: python ; coding: utf-8 -*-
#
# LNDIVC PyInstaller 스펙
# 빌드: build.bat 또는 pyinstaller LNDIVC.spec --noconfirm
#
# 출력: dist/LNDIVC/ 폴더 (LNDIVC.exe + 필요 DLL 포함)
# 배포: dist/LNDIVC/ 폴더 전체를 ZIP으로 묶어 배포
#

block_cipher = None

a = Analysis(
    ['tray_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        # static 웹 리소스
        ('static', 'static'),
        # 인증서 생성 모듈
        ('generate_cert.py', '.'),
        # 설정 마법사
        ('setup_wizard.py', '.'),
        # i18n 모듈
        ('i18n.py', '.'),
        # 드라이버 설치 모듈
        ('install_drivers.py', '.'),
        # customtkinter 테마 파일
        ('server.py', '.'),
    ],
    hiddenimports=[
        # aiohttp 내부 모듈
        'aiohttp',
        'aiohttp.web',
        'aiohttp.web_runner',
        'aiohttp.web_ws',
        'aiohttp.resolver',
        'aiohttp.connector',
        # aiortc 코덱 모듈
        'aiortc',
        'aiortc.codecs',
        'aiortc.codecs.h264',
        'aiortc.codecs.opus',
        'aiortc.codecs.vpx',
        'aiortc.contrib',
        'aiortc.contrib.media',
        # PyAV
        'av',
        'av.codec',
        'av.codec.context',
        'av.container',
        'av.filter',
        'av.frame',
        'av.packet',
        # OpenCV
        'cv2',
        # NumPy
        'numpy',
        'numpy.core',
        # sounddevice / PortAudio
        'sounddevice',
        'cffi',
        '_cffi_backend',
        # pyvirtualcam
        'pyvirtualcam',
        # cryptography (인증서 생성용)
        'cryptography',
        'cryptography.hazmat.backends',
        'cryptography.hazmat.backends.openssl',
        'cryptography.hazmat.primitives',
        'cryptography.hazmat.primitives.asymmetric',
        'cryptography.hazmat.primitives.asymmetric.rsa',
        'cryptography.hazmat.primitives.hashes',
        'cryptography.hazmat.primitives.serialization',
        'cryptography.x509',
        'cryptography.x509.oid',
        # GUI
        'pystray',
        'pystray._win32',
        'customtkinter',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageTk',
        'qrcode',
        'qrcode.image.pil',
        'tkinter',
        'tkinter.ttk',
        # JSON / 표준 라이브러리
        'json',
        'ssl',
        'socket',
        'asyncio',
        'subprocess',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 불필요한 대형 패키지 제외
        'matplotlib',
        'scipy',
        'pandas',
        'PyQt5',
        'PyQt6',
        'PySide2',
        'PySide6',
        'wx',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PyAV / aiortc / customtkinter 패키지 데이터 수집
# PyInstaller 5.x: collect_data_files → (src, dest_dir) 2-tuple
# PyInstaller 6.x: a.datas가 일반 list가 되어 normalize_toc에서 3-tuple 요구
# → 버전 무관하게 (dest, src, 'DATA') 3-tuple로 정규화
from PyInstaller.utils.hooks import collect_data_files
import os as _os

def _datas(pkg):
    result = []
    for item in collect_data_files(pkg):
        if len(item) == 3:
            result.append(item)
        else:
            src, dest_dir = item
            base = _os.path.basename(src)
            dest = (dest_dir + '/' + base).lstrip('/') if dest_dir else base
            result.append((dest, src, 'DATA'))
    return result

a.datas += _datas('av')
a.datas += _datas('aiortc')
a.datas += _datas('customtkinter')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LNDIVC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,         # 트레이 앱 → 콘솔 창 없음
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LNDIVC',
)
