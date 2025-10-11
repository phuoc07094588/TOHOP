# -*- coding: utf-8 -*-
"""
ui_login.py
Hộp thoại kích hoạt (đăng nhập) bản quyền, dựa trên License Server FastAPI.
"""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
import json, time

try:
    import config  # dùng ENABLE_LICENSE nếu có
except Exception:
    class _Cfg: ENABLE_LICENSE = True
    config = _Cfg()

from license_client import (
    activate as api_activate,
    status as api_status,
    machine_fingerprint,
    load_token, save_token, LicenseError
)

DEFAULT_SERVER = getattr(config, "LICENSE_SERVER_URL", "")  # để trống cho bạn tự điền

class LicenseDialog(tk.Toplevel):
    def __init__(self, master=None, *, title="Kích hoạt bản quyền"):
        super().__init__(master)
        self.title(title)
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.var_server = tk.StringVar(value=DEFAULT_SERVER)
        self.var_key    = tk.StringVar(value="")
        self.var_fp     = tk.StringVar(value=machine_fingerprint())
        self.var_status = tk.StringVar(value="Chưa kích hoạt")
        self.ok = False

        pad = {"padx": 12, "pady": 6}
        frm = ttk.Frame(self); frm.pack(fill="both", expand=True, **pad)

        ttk.Label(frm, text="Server URL:").grid(row=0, column=0, sticky="w")
        self.ent_server = ttk.Entry(frm, textvariable=self.var_server, width=42)
        self.ent_server.grid(row=0, column=1, sticky="we")

        ttk.Label(frm, text="License Key:").grid(row=1, column=0, sticky="w")
        self.ent_key = ttk.Entry(frm, textvariable=self.var_key, width=42, show="•")
        self.ent_key.grid(row=1, column=1, sticky="we")

        ttk.Label(frm, text="Device ID:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frm, textvariable=self.var_fp, width=42, state="readonly").grid(row=2, column=1, sticky="we")

        ttk.Label(frm, text="Trạng thái:").grid(row=3, column=0, sticky="w")
        ttk.Label(frm, textvariable=self.var_status, foreground="gray").grid(row=3, column=1, sticky="w")

        btns = ttk.Frame(frm); btns.grid(row=4, column=0, columnspan=2, sticky="e", pady=(8,0))
        ttk.Button(btns, text="Dán", command=self._paste).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="Kích hoạt", command=self._activate).pack(side="left")
        ttk.Button(btns, text="Đóng", command=self._on_close).pack(side="left", padx=(6,0))

        frm.columnconfigure(1, weight=1)

        # nếu đã có token -> hiển thị trạng thái
        self.after(50, self._load_existing)

    def _load_existing(self):
        info = load_token()
        if not info:
            return
        try:
            ok = api_status(info.get("server_url",""), info.get("token",""))
            self.var_status.set(f"Đã kích hoạt: plan={ok.get('plan')} key={ok.get('key')}")
            self.var_server.set(info.get("server_url",""))
        except Exception as e:
            self.var_status.set(f"Token cũ không hợp lệ: {e}")

    def _paste(self):
        try:
            val = self.clipboard_get().strip()
            self.var_key.set(val)
        except Exception:
            pass

    def _activate(self):
        server = self.var_server.get().strip()
        key    = self.var_key.get().strip()
        fp     = self.var_fp.get().strip()
        try:
            info = api_activate(server, key, fp)
            save_token(info)
            self.var_status.set(f"✔️ Kích hoạt thành công (plan={info.get('plan')}, hết hạn {info.get('expires')})")
            self.ok = True
            messagebox.showinfo("Kích hoạt", "Kích hoạt thành công!")
            self.destroy()
        except LicenseError as e:
            messagebox.showerror("Kích hoạt thất bại", str(e))
        except Exception as e:
            messagebox.showerror("Lỗi", str(e))

    def _on_close(self):
        self.destroy()

def ensure_license(tk_root=None) -> bool:
    """
    Dùng ở đầu chương trình. Trả về True nếu đã/kích hoạt OK, False nếu user hủy.
    """
    if not getattr(config, "ENABLE_LICENSE", True):
        return True

    # 1) thử đọc token cũ rồi gọi /status
    info = load_token()
    if info:
        try:
            api_status(info.get("server_url",""), info.get("token",""))
            return True
        except Exception:
            pass

    # 2) bật dialog để user kích hoạt
    root = tk_root or tk.Tk()
    created = tk_root is None
    if created:
        root.withdraw()
    dlg = LicenseDialog(root)
    root.wait_window(dlg)
    if created:
        try: root.destroy()
        except Exception: pass
    return bool(dlg.ok)

def show_license_manager(master=None):
    """
    Mở hộp thoại quản lý/kích hoạt lại từ Tab CẤU HÌNH.
    """
    dlg = LicenseDialog(master)
    dlg.grab_set()