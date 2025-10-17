# -*- coding: utf-8 -*-
from __future__ import annotations
"""
main.py
- Khởi chạy ứng dụng GUI chính (Tkinter + ttk.Notebook)
- TÍCH HỢP kích hoạt/đăng nhập bản quyền qua ui_login.ensure_license
- Tạo các tab: CẤU HÌNH, LC, (PHÂN TÍCH nếu có), COMBO
"""

import os
import sys
import traceback

# --- Tkinter / ttk ---
import tkinter as tk
from tkinter import ttk, messagebox

# --- Cấu hình & tiện ích ---
try:
    import config  # cần ENABLE_LICENSE, (tuỳ chọn) LICENSE_SERVER_URL
except Exception:
    class _Cfg: ENABLE_LICENSE = True
    config = _Cfg()

# Hỗ trợ console UTF-8 khi chạy bằng python.exe trên Windows
try:
    from utils import utf8_console  # type: ignore
except Exception:
    def utf8_console():
        pass

# --- Tabs ---
from ui_loadcase import LoadCaseTab
from ui_combo import ComboTab
from ui_config import ConfigTab

# Tab phân tích là tuỳ chọn
try:
    from ui_analysis import AnalysisTab  # type: ignore
    HAS_ANALYSIS = True
except Exception:
    HAS_ANALYSIS = False
    AnalysisTab = None  # type: ignore

# --- Đăng nhập/kích hoạt bản quyền ---
try:
    from ui_login import ensure_license, show_license_manager  # type: ignore
except Exception:
    # Nếu chưa thêm file ui_login.py, cho phép chạy không ràng buộc (dev mode)
    def ensure_license(_root=None) -> bool:
        return True
    def show_license_manager(_master=None):
        messagebox.showinfo("Bản quyền", "Chưa cài đặt ui_login.py")

# =========================
#   ỨNG DỤNG CHÍNH
# =========================
class RobotMainGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TP • LoadCase/Combo Tool")
        try:
            self.geometry("1200x720")
        except Exception:
            pass

        # ---- Notebook ----
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # ---- Tab: CẤU HÌNH ----
        try:
            self.tab_cfg = ConfigTab(self)  # dựa trên dự án của bạn
        except Exception as e:
            # nếu API khác, bọc vào Frame cho an toàn
            self.tab_cfg = ttk.Frame(self)
            ttk.Label(self.tab_cfg, text=f"Lỗi khởi tạo ConfigTab: {e}", foreground="red").pack(anchor="w", padx=12, pady=12)
        self.nb.add(self.tab_cfg, text="CẤU HÌNH")

        # Tuỳ chọn: nút mở trình quản lý bản quyền trong tab cấu hình (nếu muốn)
        try:
            btn = ttk.Button(self.tab_cfg, text="BẢN QUYỀN…", command=lambda: show_license_manager(self))
            btn.pack(anchor="w", padx=12, pady=(6,12))
        except Exception:
            pass

        # ---- Tab: LOAD CASE (LC) ----
        try:
            self.tab_lc = LoadCaseTab(self)
        except Exception as e:
            self.tab_lc = ttk.Frame(self)
            ttk.Label(self.tab_lc, text=f"Lỗi khởi tạo LoadCaseTab: {e}", foreground="red").pack(anchor="w", padx=12, pady=12)
        self.nb.add(self.tab_lc, text="LC")

        # ---- Tab: PHÂN TÍCH (nếu có) ----
        if HAS_ANALYSIS and AnalysisTab is not None:
            try:
                self.tab_analysis = AnalysisTab(self)  # type: ignore
                self.nb.add(self.tab_analysis, text="PHÂN TÍCH")
            except Exception as e:
                # Không chặn app vì tab tuỳ chọn
                pane = ttk.Frame(self)
                ttk.Label(pane, text=f"Lỗi khởi tạo AnalysisTab: {e}", foreground="red").pack(anchor="w", padx=12, pady=12)
                self.nb.add(pane, text="PHÂN TÍCH")

        # ---- Tab: COMBO ----
        # Một số phiên bản ComboTab cần các callable từ LoadCaseTab; mình cố gắng truyền nếu khớp,
        # nếu không sẽ rớt về gọi với (parent) thuần.
        combo_tab = None
        _ctx = lambda: {
            "loadcases": getattr(getattr(self, "tab_lc", None), "view_rows", []),
            "raw_by_id": getattr(getattr(self, "tab_lc", None), "raw_by_id", {}),
        }
        try:
            # Cố gắng theo API mở rộng
            combo_tab = ComboTab(
                self,
                get_groups_callable=lambda: getattr(getattr(self.tab_lc, "grp_board", None), "snapshot", lambda: [])(),
                get_context_callable=_ctx,
            )
        except TypeError:
            try:
                # API đơn giản hơn: chỉ cần parent
                combo_tab = ComboTab(self)
            except Exception as e:
                combo_tab = ttk.Frame(self)
                ttk.Label(combo_tab, text=f"Lỗi khởi tạo ComboTab: {e}", foreground="red").pack(anchor="w", padx=12, pady=12)
        self.tab_combo = combo_tab
        self.nb.add(self.tab_combo, text="COMBO")

        # ---- style nhẹ nhàng ----
        try:
            style = ttk.Style(self)
            # dùng 'clam' nếu có, ít lỗi vặt hơn trên Windows
            style.theme_use("clam")
        except Exception:
            pass

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát ứng dụng?"):
            self.destroy()

# =========================
#   HÀM MAIN
# =========================
def _can_launch_tk() -> bool:
    """Return True if a Tk root window can be created in the current environment."""

    # Trên Windows và macOS luôn giả định có thể khởi tạo Tk (không dựa vào DISPLAY)
    if sys.platform.startswith("win") or sys.platform == "darwin":
        return True

    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    if display:
        return True

    return False


def main():
    utf8_console()

    if not _can_launch_tk():
        print("Không thể khởi chạy giao diện Tkinter vì thiếu biến môi trường DISPLAY.")
        return

    # 1) Cửa sổ tạm cho hộp thoại đăng nhập/kích hoạt
    _tmp_root = tk.Tk()
    _tmp_root.withdraw()
    ok = True
    try:
        if getattr(config, "ENABLE_LICENSE", True):
            ok = ensure_license(_tmp_root)
    finally:
        try:
            _tmp_root.destroy()
        except Exception:
            pass

    if not ok:
        # Người dùng hủy / kích hoạt thất bại
        return

    # 2) Mở ứng dụng chính
    try:
        app = RobotMainGUI()
        app.mainloop()
    except Exception:
        utf8_console()
        print("LỖI NGOẠI LỆ:\n", traceback.format_exc())

if __name__ == "__main__":
    main()
