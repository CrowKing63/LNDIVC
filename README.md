# LNDIVC

**Vision Pro 페르소나 → Windows 가상 웹캠 스트리머**

Apple Vision Pro의 페르소나(전면 카메라)와 마이크를 로컬 네트워크를 통해 Windows PC의 가상 웹캠·마이크로 노출합니다.
Zoom, PlayAbility 등 모든 DirectShow 기반 소프트웨어에서 일반 웹캠처럼 선택할 수 있습니다.

**별도 visionOS 앱 설치 불필요** — Vision Pro Safari에서 로컬 웹페이지에 접속하는 방식입니다.

---

## 동작 원리

```
Vision Pro Safari
  └─ getUserMedia() → 페르소나 카메라 + 마이크
       └─ WebRTC (로컬 네트워크)
            └─ Windows server.py
                 ├─ 비디오 → OBS Virtual Camera
                 │             └─ Zoom / PlayAbility
                 └─ 오디오 → VB-Audio CABLE Input
                               └─ CABLE Output (Zoom 마이크)
```

---

## 사전 준비 (Windows)

| 필수 항목 | 다운로드 |
|-----------|----------|
| Python 3.11 이상 | https://www.python.org |
| OBS Studio (가상 카메라 드라이버 포함) | https://obsproject.com |
| VB-Audio Virtual Cable *(마이크 연동 선택)* | https://vb-audio.com/Cable |

> **OBS Studio 주의**: 설치 후 OBS를 한 번 실행한 뒤 메뉴 **도구 → 가상 카메라 시작**을 눌러 드라이버를 활성화해야 합니다. 이후에는 OBS 없이도 `server.py`만으로 가상 카메라가 작동합니다.

---

## 설치 (최초 1회)

### 1. 저장소 다운로드

ZIP으로 다운로드 후 압축 해제합니다.

### 2. setup.bat 실행

`server` 폴더에서 `setup.bat`을 더블클릭합니다.

- Python 가상환경 생성
- 필요한 패키지 자동 설치
- HTTPS 인증서(`cert.pem`, `key.pem`) 자동 생성

### 3. cert.pem → Vision Pro 신뢰 설정 (최초 1회)

1. `server/cert.pem` 파일을 **AirDrop** 또는 **이메일**로 Vision Pro에 전송
2. Vision Pro에서 파일을 열면 프로파일 설치 화면이 열림 → **설치**
3. **설정 → 일반 → 정보 → 인증서 신뢰 설정**
   → `LNDIVC Local` 스위치 켜기 → **계속**

> 이 단계를 완료해야 Safari가 로컬 HTTPS 인증서를 신뢰합니다.

---

## 매일 사용 방법

### Windows

1. **OBS 가상 카메라 활성화** (최초 이후 OBS를 실행하지 않아도 됨)
2. `server/start.bat` 더블클릭
3. 터미널에 표시되는 주소 확인:
   ```
   https://192.168.x.x:8443
   ```

### Vision Pro

1. Safari에서 위 주소로 이동
2. **스트리밍 시작** 버튼 탭
3. 카메라·마이크 권한 허용
4. 화면에 "✅ 스트리밍 중" 메시지 확인

### Zoom / PlayAbility 설정

| 설정 | 값 |
|------|----|
| 카메라 | `OBS Virtual Camera` |
| 마이크 | `CABLE Output (VB-Audio Virtual Cable)` |

---

## 파일 구조

```
LNDIVC/
└── server/
    ├── server.py           # 메인 서버 (HTTPS + WebSocket 시그널링 + WebRTC 수신)
    ├── generate_cert.py    # 자체 서명 인증서 생성
    ├── requirements.txt    # Python 의존성
    ├── setup.bat           # 최초 설치 스크립트
    ├── start.bat           # 서버 실행 스크립트
    └── static/
        └── index.html      # Vision Pro Safari 접속 페이지
```

---

## 트러블슈팅

### Safari에서 "이 연결은 안전하지 않습니다" 경고

→ cert.pem 신뢰 설정(위 3단계)이 완료되지 않은 경우입니다.
→ 경고 페이지에서 **고급 → 이 웹사이트 방문**을 눌러도 `getUserMedia`가 차단될 수 있습니다. 반드시 신뢰 설정을 완료하세요.

### 카메라 권한이 계속 거부됨

→ Vision Pro **설정 → 개인 정보 보호 및 보안 → 카메라**에서 Safari 권한을 허용했는지 확인하세요.

### OBS Virtual Camera가 목록에 없음

→ OBS Studio를 실행한 뒤 **도구 → 가상 카메라 시작**을 눌러주세요.

### 마이크가 Zoom에 표시되지 않음

→ VB-Audio Virtual Cable 설치 후 Windows를 재시작하세요.
→ Zoom 마이크 설정에서 `CABLE Output (VB-Audio Virtual Cable)` 선택.

### IP 주소가 바뀌어 접속이 안 됨

→ `server/start.bat` 실행 시 터미널에 현재 IP가 출력됩니다.
→ IP가 자주 바뀐다면 공유기에서 Windows PC에 고정 IP를 할당하는 것을 권장합니다.
→ 또는 `python generate_cert.py`를 다시 실행하면 새 IP로 인증서가 갱신됩니다.

---

## 기술 스택

- **스트리밍 프로토콜**: WebRTC (브라우저 ↔ aiortc)
- **시그널링**: WebSocket over WSS (aiohttp)
- **비디오**: H.264 / VP8 (협상 자동)
- **오디오**: Opus 48kHz mono
- **가상 카메라**: pyvirtualcam → OBS Virtual Camera 드라이버
- **가상 오디오**: sounddevice → VB-Audio Virtual Cable
