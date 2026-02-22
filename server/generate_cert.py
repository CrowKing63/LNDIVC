"""
generate_cert.py
-----------------
로컬 네트워크 HTTPS 용 자체 서명 인증서 생성기.

사용법:
    python generate_cert.py

생성 파일:
    cert.pem  - 인증서 (Vision Pro에 AirDrop 후 신뢰 설정)
    key.pem   - 개인 키 (서버 전용, 외부 공유 금지)

Vision Pro에서 신뢰 설정 방법:
    1. cert.pem 을 AirDrop 또는 이메일로 Vision Pro에 전송
    2. 설정 → 일반 → VPN 및 기기 관리 → 프로파일 → 설치
    3. 설정 → 일반 → 정보 → 인증서 신뢰 설정
       → 방금 설치한 인증서 토글 → "완전히 신뢰"
"""

import datetime
import ipaddress
import socket
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
except ImportError:
    print("cryptography 패키지가 필요합니다.")
    print("설치: pip install cryptography")
    sys.exit(1)


def get_local_ip() -> str:
    """LAN에서 실제 사용하는 IP 주소 조회"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except Exception:
            return socket.gethostbyname(socket.gethostname())


def generate(out_dir: Path = Path(__file__).parent):
    local_ip = get_local_ip()
    hostname = socket.gethostname()

    print(f"인증서 생성 중...")
    print(f"  IP:       {local_ip}")
    print(f"  Hostname: {hostname}")

    # RSA 2048 키 생성
    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # 인증서 정보
    name = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, local_ip),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "LNDIVC Local"),
    ])

    # SAN: IP + hostname + localhost
    san = x509.SubjectAlternativeName([
        x509.IPAddress(ipaddress.IPv4Address(local_ip)),
        x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        x509.DNSName(hostname),
        x509.DNSName("localhost"),
    ])

    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=825))  # ~2년
        .add_extension(san, critical=False)
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=None), critical=True
        )
        .sign(key, hashes.SHA256(), default_backend())
    )

    cert_path = out_dir / "cert.pem"
    key_path  = out_dir / "key.pem"

    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )

    print(f"\n✅ 인증서 저장 완료")
    print(f"   cert.pem → {cert_path}")
    print(f"   key.pem  → {key_path}")
    print()
    print("=" * 58)
    print("  Vision Pro 인증서 신뢰 설정 (최초 1회)")
    print("=" * 58)
    print(f"  1. cert.pem 을 Vision Pro로 AirDrop 전송")
    print(f"  2. Vision Pro: 설정 → 일반 → VPN 및 기기 관리")
    print(f"     → LNDIVC Local 프로파일 → 설치")
    print(f"  3. 설정 → 일반 → 정보 → 인증서 신뢰 설정")
    print(f"     → LNDIVC Local → 스위치 켜기 → 계속")
    print("=" * 58)
    print(f"\n  이후 Safari에서 https://{local_ip}:8443 접속")


if __name__ == "__main__":
    generate()
