"""
LNDIVC Tray Application
-----------------------
시스템 트레이 기반 GUI.  server.py를 백그라운드 스레드로 구동.

실행: python tray_app.py
"""

import asyncio
import json
import socket
import sys
import threading
from pathlib import Path

# ── 경로 설정 ─────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    DATA_DIR   = Path(sys.executable).parent
    BUNDLE_DIR = Path(sys._MEIPASS)
else:
    DATA_DIR   = Path(__file__).parent
    BUNDLE_DIR = Path(__file__).parent

# ── 선택적 의존성 ─────────────────────────────────────────────────────
try:
    import pystray
    from PIL import Image, ImageDraw
    HAVE_TRAY = True
except ImportError:
    HAVE_TRAY = False

try:
    import customtkinter as ctk
    HAVE_CTK = True
except ImportError:
    import tkinter as ctk   # type: ignore
    HAVE_CTK = False

try:
    import qrcode
    HAVE_QR = True
except ImportError:
    HAVE_QR = False

from i18n import t, set_lang, get_lang, LANG_OPTIONS
import server as srv


# ── 전역 상태 ─────────────────────────────────────────────────────────
_icon: "pystray.Icon | None" = None
_server_thread: "threading.Thread | None" = None
_loop: "asyncio.AbstractEventLoop | None" = None
_stop_event: "asyncio.Event | None" = None
_conn_status = "stopped"   # stopped | running | connected | error


# ── 설정 로드/저장 ────────────────────────────────────────────────────
def _load_config() -> dict:
    p = DATA_DIR / "config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding='utf-8'))
        except Exception:
            pass
    return {'mode': 'self_signed', 'hostname': '', 'port': 8443, 'lang': 'ko'}


def _save_config(cfg: dict) -> None:
    (DATA_DIR / "config.json").write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8'
    )


def _get_url() -> str:
    cfg = _load_config()
    port = cfg.get('port', 8443)
    if cfg.get('mode') == 'tailscale' and cfg.get('hostname'):
        return f"https://{cfg['hostname']}:{port}"
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        local_ip = "127.0.0.1"
    return f"https://{local_ip}:{port}"


# ── 트레이 아이콘 이미지 ──────────────────────────────────────────────
_STATUS_COLORS = {
    'stopped':   (120, 120, 120),
    'running':   (255, 165,   0),
    'connected': ( 52, 199,  89),
    'error':     (255,  59,  48),
}


def _make_icon_image(status: str = 'stopped') -> "Image.Image":
    color = _STATUS_COLORS.get(status, _STATUS_COLORS['stopped'])
    img  = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 외곽 흰 링
    draw.ellipse([2, 2, 62, 62], fill=(255, 255, 255, 200))
    # 상태 색상 원
    draw.ellipse([10, 10, 54, 54], fill=(*color, 255))
    return img


# ── 트레이 아이콘/메뉴 업데이트 ──────────────────────────────────────
def _update_icon() -> None:
    if _icon is None:
        return
    _icon.icon = _make_icon_image(_conn_status)
    label = {
        'stopped':   t('status_stopped'),
        'running':   t('status_running'),
        'connected': t('status_connected'),
        'error':     t('status_error'),
    }.get(_conn_status, _conn_status)
    _icon.title = f"LNDIVC – {label}"


def _build_menu() -> "pystray.Menu":
    running = _server_thread is not None and _server_thread.is_alive()

    def _toggle(icon, item):
        if running:
            stop_server()
        else:
            start_server()

    return pystray.Menu(
        pystray.MenuItem(
            lambda item: t('server_stop') if running else t('server_start'),
            _toggle,
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            t('show_qr'),
            lambda icon, item: _open_window(_qr_window_fn),
            enabled=running,
        ),
        pystray.MenuItem(
            t('settings'),
            lambda icon, item: _open_window(_settings_window_fn),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(t('quit'), _on_quit),
    )


def _refresh_menu() -> None:
    if _icon is not None:
        _icon.menu = _build_menu()


# ── 서버 관리 ─────────────────────────────────────────────────────────
def _on_status_change(state: str) -> None:
    """server.py에서 WebRTC 상태 변경 시 호출"""
    global _conn_status
    if state == 'connected':
        _conn_status = 'connected'
    elif state in ('disconnected', 'failed', 'closed'):
        _conn_status = 'running'   # 서버는 살아있음
    _update_icon()


def _server_thread_fn() -> None:
    global _loop, _stop_event, _conn_status
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _stop_event = asyncio.Event()
    _conn_status = 'running'
    _update_icon()
    _refresh_menu()
    try:
        _loop.run_until_complete(
            srv.run_server(stop_event=_stop_event, on_status=_on_status_change)
        )
    except Exception as e:
        print(f"[서버 오류] {e}")
    finally:
        _conn_status = 'stopped'
        _update_icon()
        _refresh_menu()
        _loop.close()
        _loop = None
        _stop_event = None


def start_server() -> None:
    global _server_thread
    if _server_thread and _server_thread.is_alive():
        return
    if not (DATA_DIR / "cert.pem").exists():
        _open_window(_setup_window_fn)
        return
    _server_thread = threading.Thread(target=_server_thread_fn, daemon=True)
    _server_thread.start()
    _refresh_menu()


def stop_server() -> None:
    global _conn_status
    if _loop and _stop_event:
        _loop.call_soon_threadsafe(_stop_event.set)
    _conn_status = 'stopped'
    _update_icon()
    _refresh_menu()


def _on_quit(icon, item=None) -> None:
    stop_server()
    if _icon is not None:
        _icon.stop()


# ── 창 유틸리티 ───────────────────────────────────────────────────────
def _open_window(fn) -> None:
    """별도 스레드에서 tkinter 창 열기 (pystray 콜백에서 호출용)"""
    threading.Thread(target=fn, daemon=True).start()


def _apply_ctk_theme() -> None:
    if HAVE_CTK:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")


# ── QR 코드 창 ────────────────────────────────────────────────────────
def _qr_window_fn() -> None:
    url = _get_url()
    _apply_ctk_theme()

    root = ctk.CTk() if HAVE_CTK else ctk.Tk()   # type: ignore
    root.title(f"LNDIVC – {t('show_qr')}")
    root.resizable(False, False)

    lbl_title = ctk.CTkLabel(root, text=t('scan_qr'), font=('', 15, 'bold')) if HAVE_CTK \
        else ctk.Label(root, text=t('scan_qr'))     # type: ignore
    lbl_title.pack(pady=(20, 6))

    lbl_url = ctk.CTkLabel(root, text=url, font=('', 11), wraplength=300) if HAVE_CTK \
        else ctk.Label(root, text=url, wraplength=300)  # type: ignore
    lbl_url.pack(pady=(0, 10))

    if HAVE_QR:
        try:
            from PIL import ImageTk
            qr_img = qrcode.make(url).resize((240, 240))
            photo  = ImageTk.PhotoImage(qr_img)
            lbl_qr = ctk.CTkLabel(root, image=photo, text='') if HAVE_CTK \
                else ctk.Label(root, image=photo)   # type: ignore
            lbl_qr.image = photo   # type: ignore  # GC 방지
            lbl_qr.pack(pady=(0, 10))
        except Exception:
            pass

    # URL 복사 버튼
    _copy_text = ctk.StringVar(value=t('copy_url'))

    def _copy():
        root.clipboard_clear()
        root.clipboard_append(url)
        _copy_text.set(t('copied'))
        root.after(1500, lambda: _copy_text.set(t('copy_url')))

    if HAVE_CTK:
        ctk.CTkButton(root, textvariable=_copy_text, command=_copy, width=220).pack(pady=(0, 6))
        ctk.CTkButton(root, text=t('close'), command=root.destroy,
                      fg_color='gray30', width=220).pack(pady=(0, 20))
    else:
        ctk.Button(root, textvariable=_copy_text, command=_copy).pack(pady=4)   # type: ignore
        ctk.Button(root, text=t('close'), command=root.destroy).pack(pady=(0, 16))  # type: ignore

    root.mainloop()


# ── 설정 창 ───────────────────────────────────────────────────────────
def _settings_window_fn() -> None:
    _apply_ctk_theme()
    cfg  = _load_config()
    lang = cfg.get('lang', 'ko')

    root = ctk.CTk() if HAVE_CTK else ctk.Tk()   # type: ignore
    root.title(t('settings'))
    root.resizable(False, False)
    root.geometry("380x300")

    if HAVE_CTK:
        ctk.CTkLabel(root, text=t('settings'), font=('', 16, 'bold')).pack(pady=(20, 14))

        # 언어
        ctk.CTkLabel(root, text=t('language'), anchor='w').pack(fill='x', padx=24)
        lang_var = ctk.StringVar(value=lang)
        ctk.CTkOptionMenu(root, variable=lang_var, values=LANG_OPTIONS).pack(
            fill='x', padx=24, pady=(4, 14))

        # 인증서 방식 표시
        mode      = cfg.get('mode', 'self_signed')
        mode_text = t('cert_tailscale') if mode == 'tailscale' else t('cert_self_signed')
        ctk.CTkLabel(root, text=f"{t('cert_mode')}: {mode_text}", anchor='w').pack(
            fill='x', padx=24)
        ctk.CTkButton(root, text=t('run_setup'), height=32,
                      command=lambda: [root.destroy(), _open_window(_setup_window_fn)]
                      ).pack(fill='x', padx=24, pady=(4, 16))

        def _apply():
            cfg['lang'] = lang_var.get()
            _save_config(cfg)
            set_lang(lang_var.get())
            _update_icon()
            _refresh_menu()
            root.destroy()

        row = ctk.CTkFrame(root, fg_color='transparent')
        row.pack(fill='x', padx=24, pady=6)
        ctk.CTkButton(row, text=t('cancel'), command=root.destroy,
                      fg_color='gray30').pack(side='left', expand=True, fill='x', padx=(0, 6))
        ctk.CTkButton(row, text=t('apply'), command=_apply).pack(
            side='right', expand=True, fill='x')
    else:
        ctk.Label(root, text=t('settings')).pack(pady=10)    # type: ignore
        ctk.Button(root, text=t('close'), command=root.destroy).pack(pady=10)  # type: ignore

    root.mainloop()


# ── 인증서 설정 창 ────────────────────────────────────────────────────
def _setup_window_fn() -> None:
    from setup_wizard import (get_tailscale_hostname, setup_tailscale,
                               setup_self_signed, save_config as wiz_save)
    _apply_ctk_theme()

    root = ctk.CTk() if HAVE_CTK else ctk.Tk()   # type: ignore
    root.title(t('setup_title'))
    root.resizable(False, False)
    root.geometry("420x380")

    ts_host    = get_tailscale_hostname()
    ts_present = ts_host is not None

    if HAVE_CTK:
        ctk.CTkLabel(root, text=t('setup_title'), font=('', 16, 'bold')).pack(pady=(20, 14))

        mode_var = ctk.StringVar(value='tailscale' if ts_present else 'self_signed')

        ctk.CTkLabel(root, text=t('cert_mode'), anchor='w').pack(fill='x', padx=24)
        ctk.CTkRadioButton(
            root, text=t('cert_tailscale'), variable=mode_var, value='tailscale',
            state='normal' if ts_present else 'disabled'
        ).pack(anchor='w', padx=48, pady=2)
        ctk.CTkRadioButton(
            root, text=t('cert_self_signed'), variable=mode_var, value='self_signed'
        ).pack(anchor='w', padx=48, pady=2)

        ts_info = f"  ✓ {t('tailscale_detected')}: {ts_host}" if ts_present \
            else f"  {t('tailscale_not_found')}"
        ctk.CTkLabel(root, text=ts_info,
                     text_color='#34c759' if ts_present else 'gray',
                     anchor='w').pack(fill='x', padx=24, pady=(4, 10))

        log_var = ctk.StringVar(value='')
        ctk.CTkLabel(root, textvariable=log_var, wraplength=360, anchor='w').pack(
            fill='x', padx=24, pady=(0, 8))

        def _do_setup():
            mode = mode_var.get()
            log_var.set(t('setup_in_progress'))
            root.update()
            ok = False
            if mode == 'tailscale' and ts_present:
                ok = setup_tailscale(ts_host, DATA_DIR)
                if ok:
                    wiz_save('tailscale', ts_host, DATA_DIR)
            else:
                ok = setup_self_signed(DATA_DIR)
                if ok:
                    wiz_save('self_signed', '', DATA_DIR)
            log_var.set(t('setup_done') if ok else t('setup_failed'))

        row = ctk.CTkFrame(root, fg_color='transparent')
        row.pack(fill='x', padx=24, pady=12)
        ctk.CTkButton(row, text=t('cancel'), command=root.destroy,
                      fg_color='gray30').pack(side='left', expand=True, fill='x', padx=(0, 6))
        ctk.CTkButton(row, text=t('apply'), command=_do_setup).pack(
            side='right', expand=True, fill='x')
    else:
        ctk.Label(root, text=t('setup_title')).pack(pady=10)  # type: ignore
        ctk.Button(root, text=t('close'), command=root.destroy).pack(pady=10)  # type: ignore

    root.mainloop()


# ── 메인 ──────────────────────────────────────────────────────────────
def main() -> None:
    global _icon

    cfg = _load_config()
    set_lang(cfg.get('lang', 'ko'))

    if not HAVE_TRAY:
        # 트레이 불가 → 터미널 폴백
        print("[경고] pystray / Pillow 없음 → 터미널 모드로 실행합니다.")
        asyncio.run(srv.run_server())
        return

    if HAVE_CTK:
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

    _icon = pystray.Icon(
        name='LNDIVC',
        icon=_make_icon_image('stopped'),
        title='LNDIVC',
        menu=_build_menu(),
    )

    # cert.pem 있으면 자동 시작
    if (DATA_DIR / "cert.pem").exists():
        start_server()

    _icon.run()   # 메인 스레드 점유 (Windows pystray 요구사항)


if __name__ == '__main__':
    main()
