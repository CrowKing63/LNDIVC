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
       └─ WebRTC (로컬 네트워크 또는 Tailscale VPN)
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

> **OBS Studio 주의**: 설치 후 OBS를 한 번 실행한 뒤 메뉴 **도구 → 가상 카메라 시작**을 눌러 드라이버를 활성화해야 합니다. 이후에는 OBS 없이도 가상 카메라가 작동합니다.

---

## 설치 (최초 1회)

### 1. 저장소 다운로드

ZIP으로 다운로드 후 압축 해제합니다.

### 2. setup.bat 실행

`server` 폴더에서 `setup.bat`을 더블클릭합니다.

- Python 가상환경 생성 및 패키지 자동 설치
- 인증서 설정 마법사 실행 → **Tailscale** 또는 **자체 서명** 선택

---

## 인증서 방식 선택

### 방식 A — Tailscale (권장)

Vision Pro에서 **인증서 신뢰 설정 불필요**. IP가 바뀌어도 주소 고정.

**준비:**
1. Windows PC와 Vision Pro 모두 [Tailscale](https://tailscale.com/download) 설치 및 같은 계정 로그인
2. [admin.tailscale.com/dns](https://login.tailscale.com/admin/dns) 접속 → **Enable MagicDNS** + **Enable HTTPS** 활성화
3. `setup.bat` 실행 → `[1] Tailscale` 선택

**결과:** `setup.bat`이 `tailscale cert` 명령으로 인증서를 자동 발급합니다.

---

### 방식 B — 자체 서명 (기존 방식)

Tailscale 없이 로컬 네트워크만 사용하는 경우.

`setup.bat` 실행 → `[2] 자체 서명` 선택 후 아래 단계 진행:

1. `server/cert.pem` 파일을 **AirDrop** 또는 **이메일**로 Vision Pro에 전송
2. Vision Pro에서 파일을 열면 프로파일 설치 화면 열림 → **설치**
3. **설정 → 일반 → 정보 → 인증서 신뢰 설정**
   → `LNDIVC Local` 스위치 켜기 → **계속**

---

## 매일 사용 방법

### Windows

1. `server/start.bat` 더블클릭
2. 터미널에 표시되는 주소 확인

```
=======================================================
  LNDIVC 서버 실행 중
  Vision Pro Safari에서 아래 주소로 접속하세요:

    https://my-pc.tail12345.ts.net:8443        ← Tailscale
    https://192.168.x.x:8443                   ← 자체 서명
=======================================================
```

### Vision Pro

1. Safari에서 위 주소로 이동
2. **스트리밍 시작** 버튼 탭
3. 카메라·마이크 권한 허용
4. 화면에 "스트리밍 중" 메시지 확인

### Zoom / PlayAbility 설정

| 설정 | 값 |
|------|----|
| 카메라 | `OBS Virtual Camera` |
| 마이크 | `CABLE Output (VB-Audio Virtual Cable)` |

---

## 테스트 및 검증

실제 Vision Pro 없이도 각 단계를 개별적으로 확인할 수 있습니다.

### 1단계 — 서버 시작 확인

`start.bat`(또는 `python server.py`) 실행 후 아래 출력이 나오면 정상입니다.

```
=======================================================
  LNDIVC 서버 실행 중
  Vision Pro Safari에서 아래 주소로 접속하세요:

    https://my-pc.tail12345.ts.net:8443   ← Tailscale
    https://192.168.x.x:8443              ← 자체 서명

  가상 카메라: OBS Virtual Camera          ← "비활성" 이면 OBS 설치 확인
  오디오 출력: VB-Audio CABLE Input        ← "기본 스피커" 이면 VB-Cable 설치 확인
=======================================================
```

**체크포인트**

| 항목 | 정상 출력 | 비정상 원인 |
|------|-----------|------------|
| cert.pem / key.pem | (오류 없이 서버 시작) | `setup.bat` 미실행 |
| 가상 카메라 | `OBS Virtual Camera` | OBS 미설치 또는 가상 카메라 미활성 |
| 오디오 출력 | `VB-Audio CABLE Input` | VB-Audio Cable 미설치 |

---

### 2단계 — HTTPS 접속 확인 (PC 브라우저)

Windows Chrome/Edge에서 서버 주소를 직접 열어 연결을 먼저 검증합니다.

1. `https://192.168.x.x:8443` (또는 Tailscale 주소) 접속
2. **Tailscale 방식**: 잠금 아이콘 표시 → 정상
3. **자체 서명 방식**: "연결이 안전하지 않음" 경고 → **고급 → 계속** 클릭 → 페이지 로딩 확인

> PC에서 페이지가 열리면 서버·인증서·네트워크는 정상입니다.

---

### 3단계 — WebSocket 시그널링 확인 (브라우저 개발자 도구)

PC 브라우저에서 F12 → **네트워크** 탭 → 필터: `WS`

1. 페이지에서 **스트리밍 시작** 클릭
2. `wss://…/ws` 항목이 **101 Switching Protocols** 상태로 표시되면 정상
3. `offer` / `answer` 메시지가 오가는지 **메시지** 탭에서 확인

---

### 4단계 — Vision Pro 연결 테스트

1. Vision Pro Safari에서 서버 주소 접속
2. **스트리밍 시작** 탭 → 카메라·마이크 권한 **허용**
3. 상태 표시가 `✅ 스트리밍 중` 으로 바뀌면 WebRTC 연결 성공
4. Windows 터미널에 아래 로그 확인:

```
WebRTC 상태: connected
비디오 트랙 수신 시작
오디오 트랙 수신 시작
```

---

### 5단계 — 가상 카메라 출력 확인

1. Windows **카메라 앱** 실행 → 상단 카메라 전환 버튼 클릭
2. 목록에서 `OBS Virtual Camera` 선택
3. Vision Pro 페르소나 영상이 표시되면 비디오 파이프라인 정상

> 카메라 앱 대신 OBS Studio 내 **미리보기** 에서도 확인 가능합니다.

---

### 6단계 — 가상 오디오 출력 확인

1. Windows **설정 → 시스템 → 사운드 → 볼륨 믹서** 실행
2. `CABLE Output (VB-Audio Virtual Cable)` 장치 선택 후 Vision Pro에서 말하기
3. 레벨 미터가 움직이면 오디오 파이프라인 정상

---

### 7단계 — Zoom 통합 테스트

| 설정 위치 | 값 |
|----------|----|
| Zoom 설정 → 비디오 → 카메라 | `OBS Virtual Camera` |
| Zoom 설정 → 오디오 → 마이크 | `CABLE Output (VB-Audio Virtual Cable)` |

1. Zoom 테스트 미팅 시작 → **비디오 미리보기**에서 페르소나 영상 확인
2. **마이크 테스트**에서 Vision Pro 음성 녹음·재생 확인

---

### 단계별 문제 판단표

| 증상 | 의심 단계 | 확인 방법 |
|------|-----------|----------|
| 서버 실행 즉시 종료 | 1단계 | cert.pem/key.pem 존재 여부 |
| 브라우저에서 페이지 안 열림 | 2단계 | 방화벽 8443 포트 허용 여부 |
| 상태가 "협상 중"에서 멈춤 | 3단계 | 개발자 도구 WS 탭 확인 |
| 연결은 됐지만 카메라 앱에 영상 없음 | 5단계 | OBS 가상 카메라 활성화 여부 |
| Zoom 마이크에 소리 없음 | 6단계 | VB-Audio Cable 설치·재시작 여부 |

---

## 배포용 .exe 빌드 (선택)

Python이 없는 PC에 배포할 수 있는 단독 실행 파일을 생성합니다.

```
server/build.bat 더블클릭
  → dist/LNDIVC/ 폴더 생성
```

**배포 방법:**
1. `dist/LNDIVC/` 폴더 전체를 대상 PC에 복사
2. `LNDIVC.exe --setup` 실행 → 인증서 설정
3. `LNDIVC.exe` 실행 → 서버 시작

> OBS Studio와 VB-Audio Virtual Cable은 대상 PC에 별도 설치 필요합니다.

---

## 파일 구조

```
LNDIVC/
└── server/
    ├── server.py           # 메인 서버 (HTTPS + WebSocket + WebRTC)
    ├── setup_wizard.py     # 인증서 설정 마법사 (Tailscale / 자체 서명)
    ├── generate_cert.py    # 자체 서명 인증서 생성
    ├── requirements.txt    # Python 의존성
    ├── setup.bat           # 최초 설치 스크립트
    ├── start.bat           # 서버 실행 스크립트
    ├── build.bat           # PyInstaller .exe 빌드 스크립트
    ├── LNDIVC.spec         # PyInstaller 스펙
    └── static/
        └── index.html      # Vision Pro Safari 접속 페이지
```

---

## 트러블슈팅

### Safari에서 "이 연결은 안전하지 않습니다" 경고 (자체 서명 방식)

→ cert.pem 신뢰 설정이 완료되지 않은 경우입니다.
→ 경고 페이지에서 **고급 → 이 웹사이트 방문**을 눌러도 `getUserMedia`가 차단됩니다. 반드시 신뢰 설정을 완료하세요.
→ 번거롭다면 **Tailscale 방식**으로 전환하면 이 단계가 불필요합니다.

### Tailscale 인증서 발급 실패

→ [admin.tailscale.com/dns](https://login.tailscale.com/admin/dns)에서 **MagicDNS**와 **HTTPS**가 모두 활성화되어 있는지 확인하세요.
→ Vision Pro에도 Tailscale 앱이 설치·로그인되어 있어야 접속 가능합니다.

### 카메라 권한이 계속 거부됨

→ Vision Pro **설정 → 개인 정보 보호 및 보안 → 카메라**에서 Safari 권한을 허용했는지 확인하세요.

### OBS Virtual Camera가 목록에 없음

→ OBS Studio를 실행한 뒤 **도구 → 가상 카메라 시작**을 눌러주세요.

### 마이크가 Zoom에 표시되지 않음

→ VB-Audio Virtual Cable 설치 후 Windows를 재시작하세요.
→ Zoom 마이크 설정에서 `CABLE Output (VB-Audio Virtual Cable)` 선택.

### IP 주소가 바뀌어 접속이 안 됨 (자체 서명 방식)

→ `start.bat` 실행 시 터미널에 현재 IP가 출력됩니다.
→ IP가 자주 바뀐다면 Tailscale 방식으로 전환하면 IP 변경 문제가 사라집니다.

---

## 기술 스택

- **스트리밍 프로토콜**: WebRTC (브라우저 ↔ aiortc)
- **시그널링**: WebSocket over WSS (aiohttp)
- **비디오**: H.264 / VP8 (협상 자동)
- **오디오**: Opus 48kHz mono
- **가상 카메라**: pyvirtualcam → OBS Virtual Camera 드라이버
- **가상 오디오**: sounddevice → VB-Audio Virtual Cable
- **인증서**: Tailscale (Let's Encrypt) 또는 자체 서명 (cryptography)
