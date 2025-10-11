
# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox
import config
from robot_helper import connect_robot
from sap_helper import connect_sap2000

class ConfigTab(ttk.Frame):
    """Tab CẤU HÌNH: chọn phần mềm (ROBOT/SAP2000), kiểm tra kết nối và lưu cấu hình dùng chung."""
    def __init__(self, parent):
        super().__init__(parent)
        self.engine_var = tk.StringVar(value=getattr(config, "SELECTED_ENGINE", "ROBOT"))

        header = ttk.Label(self, text="CẤU HÌNH PHẦN MỀM", style="Bold.TLabel")
        header.pack(anchor="w", padx=12, pady=(12,6))

        frm = ttk.Frame(self); frm.pack(fill="x", padx=12, pady=6)
        ttk.Label(frm, text="Chọn phần mềm:").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(frm, text="ROBOT", value="ROBOT", variable=self.engine_var).grid(row=0, column=1, sticky="w", padx=(8,0))
        ttk.Radiobutton(frm, text="SAP2000", value="SAP2000", variable=self.engine_var).grid(row=0, column=2, sticky="w", padx=(8,0))

        self.lbl_status = ttk.Label(frm, text="● Chưa kết nối", foreground="red")
        self.lbl_status.grid(row=0, column=3, sticky="e", padx=(16,0))

        btns = ttk.Frame(self); btns.pack(fill="x", padx=12, pady=(6,12))
        ttk.Button(btns, text="Kiểm tra kết nối", command=self._check_connection).pack(side="left")
        ttk.Button(btns, text="Lưu cấu hình", command=self._save).pack(side="left", padx=6)

        try:
            ttk.Style(self).configure("Bold.TLabel", font=("Segoe UI", 10, "bold"))
        except Exception:
            pass

    def _check_connection(self):
        eng = (self.engine_var.get() or "ROBOT").upper().strip()
        if eng == "ROBOT":
            rob, _ = connect_robot(visible=False)
            if rob:
                self.lbl_status.config(text="● Đã kết nối ROBOT", foreground="green")
                messagebox.showinfo("Kết nối", "Kết nối Autodesk Robot thành công.")
            else:
                self.lbl_status.config(text="● Chưa kết nối", foreground="red")
                messagebox.showerror("Lỗi kết nối", "Không thể kết nối tới Autodesk Robot.\nVui lòng mở Robot với quyền Quản trị (Admin) rồi thử lại.")
        else:
            sap_model, _ = connect_sap2000(visible=False)
            if sap_model:
                self.lbl_status.config(text="● Đã kết nối SAP2000", foreground="green")
                messagebox.showinfo("Kết nối", "Kết nối SAP2000 thành công.")
            else:
                self.lbl_status.config(text="● Chưa kết nối", foreground="red")
                messagebox.showerror("Lỗi kết nối", "Không thể kết nối tới SAP2000.\nVui lòng mở SAP2000 với quyền Quản trị (Admin) rồi thử lại.")

    def _save(self):
        val = (self.engine_var.get() or "ROBOT").upper().strip()
        if val not in ("ROBOT", "SAP2000"):
            messagebox.showerror("Giá trị không hợp lệ", "Vui lòng chọn ROBOT hoặc SAP2000.")
            return
        config.SELECTED_ENGINE = val
        messagebox.showinfo("Đã lưu", f"Đã lưu lựa chọn phần mềm: {val}")
