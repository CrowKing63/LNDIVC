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
