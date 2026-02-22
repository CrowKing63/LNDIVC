"""
LNDIVC Setup Wizard
-------------------
인증서 설정 마법사 - Tailscale 또는 자체 서명 중 선택

사용법:
    python setup_wizard.py
"""

import json
import subprocess
import sys
from pathlib import Path


def _base_dir() -> Path:
    """실행 파일 기준 디렉터리 (frozen/non-frozen 공통)"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def get_tailscale_hostname() -> "str | None":
    """Tailscale 설치 및 연결 여부 확인, 호스트명 반환"""
    try:
        result = subprocess.run(
            ['tailscale', 'status', '--json'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            dns = data.get('Self', {}).get('DNSName', '')
            return dns.rstrip('.') if dns else None
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
        pass
    return None


def setup_tailscale(hostname: str, base_dir: Path) -> bool:
    """Tailscale HTTPS 인증서 발급 (Let's Encrypt 기반, 브라우저 자동 신뢰)"""
    cert_path = base_dir / 'cert.pem'
    key_path  = base_dir / 'key.pem'

    print(f"\n  Tailscale 호스트명: {hostname}")
    print("  인증서 발급 중... (약 10초 소요)")

    result = subprocess.run(
        ['tailscale', 'cert',
         '--cert-file', str(cert_path),
         '--key-file',  str(key_path),
         hostname],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"\n[오류] 인증서 발급 실패:")
        if result.stderr.strip():
            print(f"  {result.stderr.strip()}")
        print()
        print("  해결 방법:")
        print("  1. https://login.tailscale.com/admin/dns 접속")
        print("  2. 'Enable MagicDNS' 활성화")
        print("  3. 'Enable HTTPS' 활성화 후 setup.bat 다시 실행")
        return False

    print("  인증서 발급 완료!")
    return True


def setup_self_signed(base_dir: Path) -> bool:
    """자체 서명 인증서 생성"""
    try:
        from generate_cert import generate
        generate(base_dir)
        return True
    except Exception as e:
        print(f"[오류] 인증서 생성 실패: {e}")
        return False


def save_config(mode: str, hostname: str, base_dir: Path) -> None:
    config = {'mode': mode, 'hostname': hostname, 'port': 8443}
    (base_dir / 'config.json').write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8'
    )


def main(base_dir: "Path | None" = None) -> None:
    if base_dir is None:
        base_dir = _base_dir()

    print()
    print("=" * 55)
    print("  LNDIVC 인증서 설정")
    print("=" * 55)
    print()

    ts_hostname = get_tailscale_hostname()

    if ts_hostname:
        print(f"  Tailscale 감지됨: {ts_hostname}")
        print()
        print("  인증서 방식 선택:")
        print("  [1] Tailscale  (권장 - Vision Pro 인증서 신뢰 불필요)")
        print("  [2] 자체 서명  (기존 - Vision Pro 인증서 신뢰 필요)")
        print()
        choice = input("  선택 (1 또는 2, 기본값 1): ").strip() or "1"
    else:
        print("  Tailscale이 감지되지 않았습니다 → 자체 서명 인증서 사용")
        print()
        print("  Tailscale을 쓰면 Vision Pro 인증서 신뢰 설정이 불필요합니다.")
        print("  https://tailscale.com/download 에서 설치 후 setup.bat 재실행")
        print()
        choice = "2"

    print()

    if choice == "1" and ts_hostname:
        if not setup_tailscale(ts_hostname, base_dir):
            sys.exit(1)
        save_config('tailscale', ts_hostname, base_dir)
        print()
        print("=" * 55)
        print("  Tailscale 설정 완료!")
        print("=" * 55)
        print()
        print("  Vision Pro에서 인증서 신뢰 설정이 필요 없습니다.")
        print()
        print("  start.bat 실행 후 Vision Pro Safari에서:")
        print(f"    https://{ts_hostname}:8443")
        print()
        print("  (Vision Pro에 Tailscale 앱이 설치되어 있어야 합니다)")
        print()
    else:
        if not setup_self_signed(base_dir):
            sys.exit(1)
        save_config('self_signed', '', base_dir)


if __name__ == '__main__':
    main()
