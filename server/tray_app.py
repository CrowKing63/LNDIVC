"""
LNDIVC Tray Application
-----------------------
시스템 트레이 기반 GUI.  server.py를 백그라운드 스레드로 구동.

실행: python tray_app.py
"""

import asyncio
import json
import queue as _queue
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

# server.py는 av / cv2 등 무거운 패키지에 의존하므로 지연 임포트
# (가상환경 없이 실행 시 트레이 GUI는 뜨되, 서버 시작 시 오류 안내)
srv = None

def _import_server():
    global srv
    if srv is not None:
        return True
    try:
        import server as _srv
        srv = _srv
        return True
    except ImportError as e:
        _show_import_error(str(e))
        return False

def _show_import_error(err: str) -> None:
    msg = (
        f"서버 모듈 로드 실패:\n{err}\n\n"
        "가상환경이 활성화되어 있는지 확인하세요.\n"
        "setup.bat → start.bat 순서로 실행하세요."
    )
    try:
        import tkinter.messagebox as mb
        import tkinter as tk
        _r = tk.Tk(); _r.withdraw()
        mb.showerror("LNDIVC – 오류", msg)
        _r.destroy()
    except Exception:
        print(f"[LNDIVC 오류] {msg}")


# ── 전역 상태 ─────────────────────────────────────────────────────────
_icon: "pystray.Icon | None" = None
_server_thread: "threading.Thread | None" = None
_loop: "asyncio.AbstractEventLoop | None" = None
_stop_event: "asyncio.Event | None" = None
_conn_status = "stopped"   # stopped | running | connected | error

# ── GUI 전용 스레드 (tkinter 스레드 안전성) ───────────────────────────
# 모든 CTk/tkinter 창은 이 단일 스레드에서 순차 실행되어
# Tcl 인터프리터 스레드 불일치(RuntimeError: main thread is not in main loop)를 방지한다.
_gui_queue: "_queue.Queue" = _queue.Queue()
_gui_thread: "threading.Thread | None" = None


def _gui_worker() -> None:
    while True:
        fn = _gui_queue.get()
        if fn is None:
            return
        try:
            fn()
        except Exception as exc:
            print(f"[GUI 오류] {exc}")


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
        pystray.MenuItem(
            t('drivers'),
            lambda icon, item: _open_window(_drivers_window_fn),
        ),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(
            t('uninstall'),
            lambda icon, item: _open_window(_uninstall_window_fn),
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
    if not _import_server():   # 가상환경 미활성 시 오류 안내 후 중단
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
    """GUI 전용 스레드에서 창 열기 (tkinter 스레드 안전)"""
    global _gui_thread
    if _gui_thread is None or not _gui_thread.is_alive():
        _gui_thread = threading.Thread(target=_gui_worker, daemon=True)
        _gui_thread.start()
    _gui_queue.put(fn)


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


# ── 드라이버 설치 창 ──────────────────────────────────────────────────
def _drivers_window_fn() -> None:
    from install_drivers import (check_unitycapture, check_vbcable,
                                  install_unitycapture, install_vbcable)
    _apply_ctk_theme()

    root = ctk.CTk() if HAVE_CTK else ctk.Tk()   # type: ignore
    root.title(t('drivers_title'))
    root.resizable(False, False)
    root.geometry("500x520")

    if not HAVE_CTK:
        ctk.Label(root, text=t('drivers_title')).pack(pady=20)   # type: ignore
        ctk.Button(root, text=t('close'), command=root.destroy).pack()  # type: ignore
        root.mainloop()
        return

    ctk.CTkLabel(root, text=t('drivers_title'),
                 font=('', 16, 'bold')).pack(pady=(20, 4))
    ctk.CTkLabel(root, text=t('drivers_desc'), text_color='gray').pack(pady=(0, 14))

    # ── 드라이버 상태 행 ─────────────────────────────────────────────
    # 상태 레이블과 설치 버튼을 담는 프레임
    drv_frame = ctk.CTkFrame(root)
    drv_frame.pack(fill='x', padx=24, pady=(0, 10))

    unity_ok  = [check_unitycapture()]
    vbc_ok    = [check_vbcable()]

    def _status_color(ok: bool) -> str:
        return '#34c759' if ok else '#ff3b30'

    # UnityCapture 행
    uc_row = ctk.CTkFrame(drv_frame, fg_color='transparent')
    uc_row.pack(fill='x', padx=12, pady=(10, 4))
    ctk.CTkLabel(uc_row, text=t('drv_unity_name'), anchor='w').pack(side='left')
    uc_status = ctk.CTkLabel(uc_row,
                              text=t('installed') if unity_ok[0] else t('not_installed'),
                              text_color=_status_color(unity_ok[0]))
    uc_status.pack(side='right', padx=(8, 0))
    uc_btn = ctk.CTkButton(uc_row, text=t('install_btn'), width=70,
                            state='disabled' if unity_ok[0] else 'normal')
    uc_btn.pack(side='right')

    # VB-Cable 행
    vbc_row = ctk.CTkFrame(drv_frame, fg_color='transparent')
    vbc_row.pack(fill='x', padx=12, pady=(4, 10))
    ctk.CTkLabel(vbc_row, text=t('drv_vbc_name'), anchor='w').pack(side='left')
    vbc_status = ctk.CTkLabel(vbc_row,
                               text=t('installed') if vbc_ok[0] else t('not_installed'),
                               text_color=_status_color(vbc_ok[0]))
    vbc_status.pack(side='right', padx=(8, 0))
    vbc_btn = ctk.CTkButton(vbc_row, text=t('install_btn'), width=70,
                             state='disabled' if vbc_ok[0] else 'normal')
    vbc_btn.pack(side='right')

    # 요약 레이블
    all_ok = unity_ok[0] and vbc_ok[0]
    summary_var = ctk.StringVar(
        value=t('drv_all_ok') if all_ok else t('drv_missing'))
    summary_color = '#34c759' if all_ok else '#ffa500'
    summary_lbl = ctk.CTkLabel(root, textvariable=summary_var,
                                text_color=summary_color)
    summary_lbl.pack(pady=(0, 8))

    # ── 로그 박스 ────────────────────────────────────────────────────
    ctk.CTkLabel(root, text=t('log'), anchor='w').pack(fill='x', padx=24)
    log_box = ctk.CTkTextbox(root, height=130, state='disabled')
    log_box.pack(fill='x', padx=24, pady=(4, 10))

    _busy = [False]

    def _log(msg: str) -> None:
        # root.after()는 다른 스레드에서 호출해도 안전한 tkinter 유일한 메서드
        def _update():
            log_box.configure(state='normal')
            log_box.insert('end', msg + '\n')
            log_box.see('end')
            log_box.configure(state='disabled')
        root.after(0, _update)

    def _refresh_status() -> None:
        def _do():
            unity_ok[0] = check_unitycapture()
            vbc_ok[0]   = check_vbcable()
            uc_status.configure(
                text=t('installed') if unity_ok[0] else t('not_installed'),
                text_color=_status_color(unity_ok[0]))
            uc_btn.configure(state='disabled' if unity_ok[0] else 'normal')
            vbc_status.configure(
                text=t('installed') if vbc_ok[0] else t('not_installed'),
                text_color=_status_color(vbc_ok[0]))
            vbc_btn.configure(state='disabled' if vbc_ok[0] else 'normal')
            all_done = unity_ok[0] and vbc_ok[0]
            summary_var.set(t('drv_all_ok') if all_done else t('drv_missing'))
            summary_lbl.configure(text_color='#34c759' if all_done else '#ffa500')
        root.after(0, _do)

    def _run_install(fn, label: str) -> None:
        if _busy[0]:
            return
        _busy[0] = True
        root.after(0, lambda: uc_btn.configure(state='disabled'))
        root.after(0, lambda: vbc_btn.configure(state='disabled'))
        root.after(0, lambda: btn_all.configure(state='disabled'))
        _log(f"\n── {label} ──")
        try:
            fn(_log)
        finally:
            _refresh_status()
            _busy[0] = False
            root.after(0, lambda: btn_all.configure(state='normal'))

    # 버튼 커맨드 연결
    uc_btn.configure(
        command=lambda: threading.Thread(
            target=_run_install,
            args=(install_unitycapture, t('drv_unity_name')),
            daemon=True
        ).start()
    )
    vbc_btn.configure(
        command=lambda: threading.Thread(
            target=_run_install,
            args=(install_vbcable, t('drv_vbc_name')),
            daemon=True
        ).start()
    )

    def _install_all() -> None:
        if _busy[0]:
            return
        _busy[0] = True
        root.after(0, lambda: uc_btn.configure(state='disabled'))
        root.after(0, lambda: vbc_btn.configure(state='disabled'))
        root.after(0, lambda: btn_all.configure(state='disabled'))
        _log(f"\n── {t('install_all_btn')} ──")
        try:
            if not unity_ok[0]:
                install_unitycapture(_log)
            if not vbc_ok[0]:
                install_vbcable(_log)
        finally:
            _refresh_status()
            _busy[0] = False
            root.after(0, lambda: btn_all.configure(state='normal'))

    # ── 하단 버튼 ────────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(root, fg_color='transparent')
    btn_row.pack(fill='x', padx=24, pady=6)

    ctk.CTkButton(btn_row, text=t('refresh'),
                  command=_refresh_status,
                  fg_color='gray30', width=90
                  ).pack(side='left', padx=(0, 6))

    btn_all = ctk.CTkButton(btn_row, text=t('install_all_btn'),
                             command=lambda: threading.Thread(
                                 target=_install_all, daemon=True).start(),
                             state='normal' if not all_ok else 'disabled')
    btn_all.pack(side='left', expand=True, fill='x', padx=(0, 6))

    ctk.CTkButton(btn_row, text=t('close'), command=root.destroy,
                  fg_color='gray30', width=90).pack(side='right')

    root.mainloop()


# ── 제거 헬퍼 ─────────────────────────────────────────────────────────
_UNITY_CLSID = '{5C2CD55C-92AD-4999-8666-912BD3E700BB}'


def _find_unitycapture() -> "str | None":
    """레지스트리 또는 설치 경로에서 UnityCapture DLL 경로 반환"""
    try:
        import winreg
        sub = rf'CLSID\{_UNITY_CLSID}\InprocServer32'
        checks = [
            (winreg.HKEY_CLASSES_ROOT,  sub,                        winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_CLASSES_ROOT,  sub,                        0),
            (winreg.HKEY_LOCAL_MACHINE, rf'SOFTWARE\Classes\{sub}', winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_LOCAL_MACHINE, rf'SOFTWARE\Classes\{sub}', 0),
            (winreg.HKEY_CURRENT_USER,  rf'Software\Classes\{sub}', winreg.KEY_WOW64_64KEY),
            (winreg.HKEY_CURRENT_USER,  rf'Software\Classes\{sub}', 0),
        ]
        for hive, reg_sub, flags in checks:
            try:
                key = winreg.OpenKey(hive, reg_sub, access=winreg.KEY_READ | flags)
                val, _ = winreg.QueryValueEx(key, '')
                winreg.CloseKey(key)
                if val and Path(val).exists():
                    return val
            except Exception:
                continue
    except ImportError:
        pass
    # 폴백: APPDATA에 복사한 DLL 직접 탐색
    from install_drivers import UNITY_DIR
    if UNITY_DIR.exists():
        for f in sorted(UNITY_DIR.glob('*.dll')):
            return str(f)
    return None


def _find_vbcable_uninstaller() -> "str | None":
    """레지스트리 또는 알려진 경로에서 VB-Cable 제거 프로그램 탐색"""
    try:
        import winreg
        subkeys = (
            r'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\VB-Audio Virtual Cable',
            r'SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\VB-Audio Virtual Cable',
        )
        for root_hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sub in subkeys:
                try:
                    key = winreg.OpenKey(root_hive, sub)
                    val, _ = winreg.QueryValueEx(key, 'UninstallString')
                    winreg.CloseKey(key)
                    if val:
                        return val
                except Exception:
                    pass
    except ImportError:
        pass
    for p in (
        r'C:\Program Files\VB\CABLE\VBCABLE_Setup_x64.exe',
        r'C:\Program Files (x86)\VB\CABLE\VBCABLE_Setup_x64.exe',
    ):
        if Path(p).exists():
            return p
    return None


def _get_camera_apps() -> "list[tuple[str, int]]":
    """가상 카메라를 점유할 수 있는 실행 중 프로세스 목록 반환"""
    targets = {
        'zoom.exe', 'teams.exe', 'obs64.exe', 'obs32.exe',
        'chrome.exe', 'firefox.exe', 'msedge.exe', 'slack.exe',
        'discord.exe', 'webex.exe', 'skype.exe', 'msteams.exe',
    }
    result = []
    try:
        import subprocess
        out = subprocess.check_output(
            ['tasklist', '/fo', 'csv', '/nh'],
            creationflags=0x08000000,   # CREATE_NO_WINDOW
        ).decode('utf-8', errors='replace')
        for line in out.splitlines():
            parts = line.strip('"').split('","')
            if len(parts) >= 2 and parts[0].lower() in targets:
                try:
                    result.append((parts[0], int(parts[1])))
                except ValueError:
                    pass
    except Exception:
        pass
    return result


def _kill_pid(pid: int) -> None:
    import subprocess
    subprocess.run(['taskkill', '/PID', str(pid), '/F'],
                   capture_output=True, creationflags=0x08000000)


def _schedule_delete(path: str) -> bool:
    """MoveFileExW DELAY_UNTIL_REBOOT: 재부팅 후 파일 삭제 예약"""
    try:
        import ctypes
        return bool(ctypes.windll.kernel32.MoveFileExW(path, None, 4))
    except Exception:
        return False


def _regsvr32_unregister(path: str) -> bool:
    """관리자 권한으로 regsvr32 /u /s 실행 (UAC 상승 포함)"""
    import subprocess
    # 1차: 현재 권한으로 시도
    ret = subprocess.run(
        ['regsvr32', '/u', '/s', path],
        capture_output=True, creationflags=0x08000000,
    )
    if ret.returncode == 0:
        return True
    # 2차: PowerShell RunAs (UAC 프롬프트)
    try:
        ps_cmd = (
            f'Start-Process regsvr32.exe '
            f'-ArgumentList "/u /s `\'{path}`\'" '
            f'-Verb RunAs -Wait -PassThru'
        )
        subprocess.run(
            ['powershell', '-Command', ps_cmd],
            creationflags=0x08000000,
        )
        return True   # UAC 성공 여부는 별도 확인 불가 → True 반환
    except Exception:
        return False


def _do_uninstall(remove_unity: bool, remove_vbcable: bool,
                  log_cb: "callable") -> bool:
    """
    실제 제거 수행.
    log_cb(str) : UI 로그 갱신 콜백
    반환: 재부팅 필요 여부 (True = 재부팅 권고)
    """
    import subprocess
    needs_reboot = False

    # 1. 서버 중지
    log_cb("● 서버 중지 중...")
    stop_server()

    # 2. 설정·인증서 파일 삭제
    log_cb("● 설정 파일 삭제 중...")
    for fname in ('cert.pem', 'key.pem', 'config.json'):
        p = DATA_DIR / fname
        if p.exists():
            try:
                p.unlink()
                log_cb(f"  ✓ {fname}")
            except Exception as e:
                log_cb(f"  ✗ {fname}: {e}")

    # 3. UnityCapture 드라이버 제거
    if remove_unity:
        unity_path = _find_unitycapture()
        if unity_path:
            log_cb("● UnityCapture 드라이버 등록 해제 중...")
            ok = _regsvr32_unregister(unity_path)
            if ok:
                log_cb("  ✓ 등록 해제 완료")
            else:
                log_cb("  ✗ 등록 해제 실패 (관리자 권한 필요)")

            # .ax 파일 삭제 시도
            log_cb(f"  파일 삭제 시도: {unity_path}")
            try:
                Path(unity_path).unlink()
                log_cb("  ✓ 파일 삭제 완료")
            except PermissionError:
                # 프로세스가 파일을 물고 있음 → 재부팅 후 삭제 예약
                if _schedule_delete(unity_path):
                    log_cb("  ↻ 파일 삭제 예약됨 (재부팅 후 자동 삭제)")
                    needs_reboot = True
                else:
                    log_cb(f"  ✗ 파일 삭제 실패 — 직접 삭제 필요:\n    {unity_path}")
            except Exception as e:
                log_cb(f"  ✗ 파일 삭제 실패: {e}")
        else:
            log_cb("● UnityCapture: 미설치 (건너뜀)")

    # 4. VB-Cable 제거
    if remove_vbcable:
        vbc = _find_vbcable_uninstaller()
        if vbc:
            log_cb("● VB-Audio CABLE 제거 실행 중 (UAC 창이 열릴 수 있음)...")
            try:
                subprocess.Popen([vbc], creationflags=0x08000000)
                log_cb("  ✓ 제거 프로그램 실행됨")
            except Exception as e:
                log_cb(f"  ✗ 실행 실패: {e}")
        else:
            log_cb("● VB-Audio CABLE: 미설치 (건너뜀)")

    log_cb("─" * 38)
    if needs_reboot:
        log_cb(f"완료. {t('reboot_required')}")
    else:
        log_cb("✓ 완료.")
    log_cb(f"앱 폴더: {DATA_DIR}")
    return needs_reboot


# ── 제거 창 ───────────────────────────────────────────────────────────
def _uninstall_window_fn() -> None:
    _apply_ctk_theme()

    unity_path  = _find_unitycapture()
    vbc_path    = _find_vbcable_uninstaller()
    camera_apps = _get_camera_apps()

    root = ctk.CTk() if HAVE_CTK else ctk.Tk()   # type: ignore
    root.title(t('uninstall_title'))
    root.resizable(False, True)   # 세로만 허용 — 콘텐츠 양에 따라 자동 높이
    root.minsize(500, 420)

    if not HAVE_CTK:
        ctk.Label(root, text=t('uninstall_title')).pack(pady=20)   # type: ignore
        ctk.Button(root, text=t('close'), command=root.destroy).pack()  # type: ignore
        root.mainloop()
        return

    ctk.CTkLabel(root, text=t('uninstall_title'),
                 font=('', 16, 'bold'), text_color='#ff3b30').pack(pady=(20, 4))
    ctk.CTkLabel(root, text=t('uninstall_warning'),
                 text_color='#ffa500').pack(pady=(0, 14))

    # ── 제거 항목 체크박스 ───────────────────────────────────────────
    ctk.CTkLabel(root, text=t('remove_items'), anchor='w').pack(fill='x', padx=24)

    ctk.CTkLabel(root, text=f"  ✓ {t('remove_configs')}",
                 anchor='w', text_color='gray').pack(fill='x', padx=24)

    def _item_label(base_key: str, found: bool) -> str:
        badge = t('detected') if found else t('not_detected')
        return f"{t(base_key)}  [{badge}]"

    uc_var = ctk.BooleanVar(value=unity_path is not None)
    ctk.CTkCheckBox(root, text=_item_label('remove_unity', unity_path is not None),
                    variable=uc_var,
                    state='normal' if unity_path else 'disabled'
                    ).pack(anchor='w', padx=40, pady=2)

    vbc_var = ctk.BooleanVar(value=False)   # 기본 off: 다른 앱이 쓸 수 있음
    ctk.CTkCheckBox(root, text=_item_label('remove_vbcable', vbc_path is not None),
                    variable=vbc_var,
                    state='normal' if vbc_path else 'disabled'
                    ).pack(anchor='w', padx=40, pady=(2, 12))

    # ── 카메라 사용 중인 프로세스 목록 ──────────────────────────────
    if camera_apps:
        ctk.CTkLabel(root, text=f"⚠  {t('close_apps_warning')}",
                     text_color='#ffa500', anchor='w').pack(fill='x', padx=24)

        # CTkScrollableFrame은 pack에서 남은 공간을 전부 점유하므로
        # 일반 CTkFrame 사용 (목록이 많아야 3~4개)
        app_frame = ctk.CTkFrame(root, fg_color='gray17')
        app_frame.pack(fill='x', padx=24, pady=(4, 10))

        def _make_kill_row(frame, name: str, pid: int) -> None:
            row = ctk.CTkFrame(frame, fg_color='transparent')
            row.pack(fill='x', padx=8, pady=2)
            ctk.CTkLabel(row, text=f"{name}  (PID {pid})", anchor='w').pack(side='left')
            def _kill(r=row, p=pid):
                _kill_pid(p)
                r.destroy()
            ctk.CTkButton(row, text=t('kill_process'), width=70, height=26,
                          fg_color='#ff3b30', command=_kill).pack(side='right')

        for name, pid in camera_apps:
            _make_kill_row(app_frame, name, pid)

    # ── 로그 박스 ────────────────────────────────────────────────────
    ctk.CTkLabel(root, text=t('log'), anchor='w').pack(fill='x', padx=24)
    log_box = ctk.CTkTextbox(root, height=90, state='disabled')
    log_box.pack(fill='x', padx=24, pady=(4, 6))

    def _log(msg: str) -> None:
        def _update():
            log_box.configure(state='normal')
            log_box.insert('end', msg + '\n')
            log_box.see('end')
            log_box.configure(state='disabled')
        root.after(0, _update)

    done = [False]

    def _run_uninstall() -> None:
        if done[0]:
            return
        done[0] = True
        btn_run.configure(state='disabled')
        btn_cancel.configure(state='disabled')

        needs_reboot = _do_uninstall(uc_var.get(), vbc_var.get(), _log)

        # 완료 후 버튼 교체
        extra = ctk.CTkFrame(root, fg_color='transparent')
        extra.pack(fill='x', padx=24, pady=(0, 4))
        ctk.CTkButton(
            extra, text=t('open_folder'), fg_color='gray30',
            command=lambda: __import__('subprocess').Popen(
                ['explorer', str(DATA_DIR)])
        ).pack(side='left', expand=True, fill='x', padx=(0, 6))
        ctk.CTkButton(
            extra, text=t('quit'),
            command=lambda: [_on_quit(None), root.destroy()],
            fg_color='#ff3b30',
        ).pack(side='right', expand=True, fill='x')

    # ── 실행/취소 버튼 ───────────────────────────────────────────────
    btn_row = ctk.CTkFrame(root, fg_color='transparent')
    btn_row.pack(fill='x', padx=24, pady=6)
    btn_cancel = ctk.CTkButton(btn_row, text=t('cancel'), command=root.destroy,
                                fg_color='gray30')
    btn_cancel.pack(side='left', expand=True, fill='x', padx=(0, 6))
    btn_run = ctk.CTkButton(btn_row, text=t('uninstall_btn'),
                             command=_run_uninstall, fg_color='#ff3b30')
    btn_run.pack(side='right', expand=True, fill='x')

    root.mainloop()


# ── 메인 ──────────────────────────────────────────────────────────────
def main() -> None:
    global _icon

    cfg = _load_config()
    set_lang(cfg.get('lang', 'ko'))

    if not HAVE_TRAY:
        # 트레이 불가 → 터미널 폴백
        print("[경고] pystray / Pillow 없음 → 터미널 모드로 실행합니다.")
        if not _import_server():
            return
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
