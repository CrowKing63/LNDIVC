"""
LNDIVC - Vision Pro → Windows Virtual Webcam Server
====================================================
Vision Pro Safari에서 WebRTC로 연결하면:
  - 비디오(페르소나/전면 카메라) → OBS Virtual Camera
  - 오디오(마이크) → 기본 스피커 또는 VB-Audio Virtual Cable

실행: python server.py
"""

import asyncio
import json
import logging
import socket
import ssl
from pathlib import Path

import av
import cv2
import numpy as np
import pyvirtualcam
import sounddevice as sd
from aiohttp import web
from aiortc import RTCIceCandidate, RTCPeerConnection, RTCSessionDescription

# ── 설정 ──────────────────────────────────────────────────────────────
VIDEO_WIDTH = 1280
VIDEO_HEIGHT = 720
VIDEO_FPS = 30
AUDIO_SAMPLE_RATE = 48000
AUDIO_CHANNELS = 1
PORT = 8443

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s  %(message)s")
log = logging.getLogger(__name__)

# ── 전역 상태 (단일 클라이언트 가정) ──────────────────────────────────
g_cam: pyvirtualcam.Camera | None = None
g_audio_out: sd.OutputStream | None = None
g_audio_buf: asyncio.Queue = asyncio.Queue(maxsize=20)


# ── 오디오 큐를 소비해 sounddevice에 전달 ─────────────────────────────
async def audio_writer():
    """별도 태스크: 오디오 큐 → sounddevice 출력"""
    loop = asyncio.get_event_loop()
    while True:
        chunk = await g_audio_buf.get()
        if g_audio_out is not None:
            try:
                await loop.run_in_executor(None, g_audio_out.write, chunk)
            except Exception as e:
                log.warning(f"오디오 출력 오류: {e}")


# ── WebRTC 트랙 수신 ──────────────────────────────────────────────────
async def receive_video(track):
    log.info("비디오 트랙 수신 시작")
    while True:
        try:
            frame: av.VideoFrame = await track.recv()
            img = frame.to_ndarray(format="rgb24")

            # 해상도가 다르면 리사이즈
            h, w = img.shape[:2]
            if w != VIDEO_WIDTH or h != VIDEO_HEIGHT:
                img = cv2.resize(img, (VIDEO_WIDTH, VIDEO_HEIGHT))

            if g_cam is not None:
                g_cam.send(img)
                g_cam.sleep_until_next_frame()
        except Exception as e:
            log.info(f"비디오 트랙 종료: {e}")
            break


async def receive_audio(track):
    log.info("오디오 트랙 수신 시작")
    while True:
        try:
            frame: av.AudioFrame = await track.recv()
            # Opus → s16 PCM 변환
            pcm = frame.to_ndarray()  # shape: (channels, samples) float32 or int16
            if pcm.dtype != np.int16:
                pcm = np.clip(pcm, -1.0, 1.0)
                pcm = (pcm * 32767).astype(np.int16)
            # sounddevice는 (samples, channels) 형태를 기대
            chunk = pcm.T.reshape(-1, AUDIO_CHANNELS).copy()
            try:
                g_audio_buf.put_nowait(chunk)
            except asyncio.QueueFull:
                pass  # 버퍼 가득 차면 드롭
        except Exception as e:
            log.info(f"오디오 트랙 종료: {e}")
            break


# ── HTTP 라우터 ───────────────────────────────────────────────────────
async def handle_index(request):
    return web.FileResponse(Path(__file__).parent / "static" / "index.html")


async def handle_ws(request):
    """WebSocket 시그널링 + WebRTC 피어 연결 처리"""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    log.info(f"클라이언트 연결: {request.remote}")

    pc = RTCPeerConnection()

    @pc.on("track")
    def on_track(track):
        if track.kind == "video":
            asyncio.ensure_future(receive_video(track))
        elif track.kind == "audio":
            asyncio.ensure_future(receive_audio(track))

    @pc.on("connectionstatechange")
    async def on_state():
        log.info(f"WebRTC 상태: {pc.connectionState}")
        if pc.connectionState in ("failed", "closed", "disconnected"):
            await pc.close()

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)
                msg_type = data.get("type")

                if msg_type == "offer":
                    await pc.setRemoteDescription(
                        RTCSessionDescription(sdp=data["sdp"], type=data["type"])
                    )
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    await ws.send_json(
                        {"type": answer.type, "sdp": pc.localDescription.sdp}
                    )
                    log.info("Answer 전송 완료")

                elif msg_type == "ice":
                    cand = data.get("candidate", {})
                    raw = cand.get("candidate", "")
                    if raw:
                        # RTCIceCandidate 파싱
                        ice = RTCIceCandidate(
                            sdpMid=cand.get("sdpMid"),
                            sdpMLineIndex=cand.get("sdpMLineIndex"),
                            candidate=raw,
                        )
                        await pc.addIceCandidate(ice)

            except Exception as e:
                log.error(f"시그널링 오류: {e}")
        elif msg.type == web.WSMsgType.ERROR:
            log.error(f"WebSocket 오류: {ws.exception()}")

    log.info("클라이언트 연결 종료")
    await pc.close()
    return ws


# ── 메인 ─────────────────────────────────────────────────────────────
async def run_server():
    # SSL 설정
    cert = Path(__file__).parent / "cert.pem"
    key = Path(__file__).parent / "key.pem"
    if not cert.exists() or not key.exists():
        print("\n❌  cert.pem / key.pem 없음.")
        print("    먼저 setup.bat 을 실행하거나: python generate_cert.py\n")
        return

    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain(cert, key)

    # VB-Audio Virtual Cable 찾기 (없으면 기본 장치)
    vbcable_idx = None
    for i, dev in enumerate(sd.query_devices()):
        if "CABLE Input" in dev["name"] and dev["max_output_channels"] > 0:
            vbcable_idx = i
            log.info(f"VB-Audio CABLE Input 발견: index={i}")
            break
    if vbcable_idx is None:
        log.warning("VB-Audio CABLE Input 없음 → 기본 스피커 출력 (Zoom 마이크 연동 불가)")

    # aiohttp 앱
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/ws", handle_ws)

    local_ip = socket.gethostbyname(socket.gethostname())

    global g_cam, g_audio_out

    with pyvirtualcam.Camera(
        width=VIDEO_WIDTH, height=VIDEO_HEIGHT, fps=VIDEO_FPS, print_fps=False
    ) as cam:
        g_cam = cam
        log.info(f"가상 카메라 활성화: {cam.device}")

        with sd.OutputStream(
            samplerate=AUDIO_SAMPLE_RATE,
            channels=AUDIO_CHANNELS,
            dtype="int16",
            blocksize=2048,
            device=vbcable_idx,
        ) as audio_out:
            g_audio_out = audio_out

            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, "0.0.0.0", PORT, ssl_context=ssl_ctx)
            await site.start()

            print(f"\n{'='*55}")
            print(f"  LNDIVC 서버 실행 중")
            print(f"  Vision Pro Safari에서 아래 주소로 접속하세요:")
            print(f"\n    https://{local_ip}:{PORT}\n")
            print(f"  가상 카메라: {cam.device}")
            print(f"  오디오 출력: {'VB-Audio CABLE Input' if vbcable_idx is not None else '기본 스피커'}")
            print(f"{'='*55}\n")

            # 오디오 큐 소비 태스크 시작
            audio_task = asyncio.ensure_future(audio_writer())
            try:
                await asyncio.Event().wait()  # 무한 대기
            finally:
                audio_task.cancel()
                await runner.cleanup()


def main():
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\n서버 종료")


if __name__ == "__main__":
    main()
