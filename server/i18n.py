"""
LNDIVC i18n – 한국어 / English
"""

_LANG = 'ko'

_STRINGS: dict[str, dict[str, str]] = {
    'ko': {
        'server_start':       '서버 시작',
        'server_stop':        '서버 중지',
        'status_stopped':     '중지됨',
        'status_running':     '대기 중 (Vision Pro 연결 기다리는 중)',
        'status_connected':   '연결됨',
        'status_error':       '오류',
        'show_qr':            'QR 코드 표시',
        'scan_qr':            'Vision Pro Safari에서 스캔하세요',
        'copy_url':           'URL 복사',
        'copied':             '복사됨!',
        'settings':           '설정',
        'language':           '언어 / Language',
        'cert_mode':          '인증서 방식',
        'cert_tailscale':     'Tailscale (권장)',
        'cert_self_signed':   '자체 서명',
        'run_setup':          '인증서 재설정...',
        'setup_title':        'LNDIVC 설정',
        'tailscale_detected': 'Tailscale 감지됨',
        'tailscale_not_found':'Tailscale이 감지되지 않음 — 자체 서명만 사용 가능',
        'setup_in_progress':  '설정 중...',
        'setup_done':         '✓ 완료. 서버를 재시작하세요.',
        'setup_failed':       '✗ 실패. 다시 시도하세요.',
        'apply':              '적용',
        'cancel':             '취소',
        'close':              '닫기',
        'quit':               '종료',
        'no_cert':            'cert.pem 없음. 먼저 설정을 완료하세요.',
        'cam_label':          '가상 카메라',
        'audio_label':        '오디오 출력',
        'inactive':           '비활성',
        'setup_required':     '서버를 시작하기 전에 인증서 설정이 필요합니다.',
        'setup_btn':          '지금 설정',
        # 제거
        'uninstall':          '제거...',
        'uninstall_title':    'LNDIVC 완전 제거',
        'remove_items':       '제거할 항목:',
        'remove_configs':     '설정·인증서 파일 (cert.pem, key.pem, config.json)',
        'remove_venv':        'Python 가상환경 (.venv) — 앱 종료 후 자동 삭제',
        'uninstall_btn':      '지금 제거',
        'open_folder':        '앱 폴더 열기 (수동 삭제)',
        'log':                '진행 상황:',
        'uninstall_warning':  '⚠ 이 작업은 되돌릴 수 없습니다.',
        # OBS 상태 확인
        'drivers':            'OBS 상태 확인...',
        'drivers_title':      'OBS 가상 카메라 상태',
        'drivers_desc':       'LNDIVC는 OBS Virtual Camera를 사용합니다 (추가 드라이버 설치 불필요).',
        'drv_obs_name':       'OBS Virtual Camera  (필수)',
        'drv_vbc_name':       'VB-Audio CABLE  (선택 — Zoom 마이크 연동)',
        'drv_vbc_optional':   '미설치 (선택 사항)',
        'drv_obs_download':   'OBS 다운로드 → obsproject.com',
        'installed':          '✓ 사용 가능',
        'not_installed':      '✗ 미설치 / 가상 카메라 미시작',
        'drv_obs_ok':         '✓ OBS 가상 카메라가 준비되어 있습니다.',
        'drv_obs_missing':    '✗ OBS를 설치하고 가상 카메라를 시작하세요.',
        'drv_obs_hint':       'OBS 실행 → 도구 → 가상 카메라 시작\n이후 OBS를 닫아도 가상 카메라는 유지됩니다.',
        'refresh':            '새로고침',
    },
    'en': {
        'server_start':       'Start Server',
        'server_stop':        'Stop Server',
        'status_stopped':     'Stopped',
        'status_running':     'Waiting for Vision Pro...',
        'status_connected':   'Connected',
        'status_error':       'Error',
        'show_qr':            'Show QR Code',
        'scan_qr':            'Scan on Vision Pro Safari',
        'copy_url':           'Copy URL',
        'copied':             'Copied!',
        'settings':           'Settings',
        'language':           'Language / 언어',
        'cert_mode':          'Certificate Mode',
        'cert_tailscale':     'Tailscale (Recommended)',
        'cert_self_signed':   'Self-Signed',
        'run_setup':          'Reconfigure Certificate...',
        'setup_title':        'LNDIVC Setup',
        'tailscale_detected': 'Tailscale detected',
        'tailscale_not_found':'Tailscale not found — self-signed only',
        'setup_in_progress':  'Setting up...',
        'setup_done':         '✓ Done. Please restart the server.',
        'setup_failed':       '✗ Failed. Please try again.',
        'apply':              'Apply',
        'cancel':             'Cancel',
        'close':              'Close',
        'quit':               'Quit',
        'no_cert':            'cert.pem not found. Please complete setup first.',
        'cam_label':          'Virtual Camera',
        'audio_label':        'Audio Output',
        'inactive':           'Inactive',
        'setup_required':     'Certificate setup is required before starting the server.',
        'setup_btn':          'Setup Now',
        # uninstall
        'uninstall':          'Uninstall...',
        'uninstall_title':    'Uninstall LNDIVC',
        'remove_items':       'Items to remove:',
        'remove_configs':     'Config & certificate files (cert.pem, key.pem, config.json)',
        'remove_venv':        'Python virtual environment (.venv) — auto-deleted after quit',
        'uninstall_btn':      'Uninstall Now',
        'open_folder':        'Open App Folder (manual delete)',
        'log':                'Progress:',
        'uninstall_warning':  '⚠ This action cannot be undone.',
        # OBS status
        'drivers':            'OBS Status...',
        'drivers_title':      'OBS Virtual Camera Status',
        'drivers_desc':       'LNDIVC uses OBS Virtual Camera (no extra driver installation needed).',
        'drv_obs_name':       'OBS Virtual Camera  (required)',
        'drv_vbc_name':       'VB-Audio CABLE  (optional — Zoom mic integration)',
        'drv_vbc_optional':   'Not installed (optional)',
        'drv_obs_download':   'Download OBS → obsproject.com',
        'installed':          '✓ Available',
        'not_installed':      '✗ Not installed / virtual cam not started',
        'drv_obs_ok':         '✓ OBS Virtual Camera is ready.',
        'drv_obs_missing':    '✗ Please install OBS and start Virtual Camera.',
        'drv_obs_hint':       'In OBS: Tools → Start Virtual Camera\nOBS can be closed afterwards — virtual camera stays active.',
        'refresh':            'Refresh',
    },
}

LANG_OPTIONS = ['ko', 'en']


def set_lang(lang: str) -> None:
    global _LANG
    if lang in _STRINGS:
        _LANG = lang


def get_lang() -> str:
    return _LANG


def t(key: str) -> str:
    return _STRINGS.get(_LANG, _STRINGS['ko']).get(key, key)
