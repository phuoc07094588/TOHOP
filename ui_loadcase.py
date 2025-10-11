# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox

# Các text mô tả (không bắt buộc)
try:
    from config import nature_text, analysis_text  # noqa: F401
except Exception:
    pass

# COM helpers
try:
    from robot_helper import COMGuard, get_load_cases_robot
except Exception:
    COMGuard = None
    def get_load_cases_robot(_rob):
        return [], {}

try:
    from sap_helper import connect_sap2000, get_load_cases_sap
except Exception:
    def connect_sap2000():
        return None, None
    def get_load_cases_sap(_sap_model):
        return [], {}

# ==============================
#         LoadCaseTab
# ==============================
class LoadCaseTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.rob = None
        self.view_rows = []   # danh sách để hiển thị
        self.raw_by_id = {}   # dữ liệu thô theo id
        self._drag = {"active": False, "selection": []}

        # ========== LEFT PANE ==========
        left = ttk.Frame(self); left.pack(side="left", fill="y", padx=(8,4), pady=8)

        # Engine chọn nguồn
        eng_bar = ttk.Frame(left); eng_bar.pack(fill="x")
        ttk.Label(eng_bar, text="Nguồn:").pack(side="left")
        self.engine = tk.StringVar(value=self._default_engine())
        for name in ("SAP2000", "ROBOT"):
            ttk.Radiobutton(eng_bar, text=name, value=name, variable=self.engine).pack(side="left", padx=(6,0))

        # Thanh tìm kiếm + nút nạp
        srch = ttk.Frame(left); srch.pack(fill="x", pady=(2,6))
        ttk.Label(srch, text="Tìm:").pack(side="left")
        self.ent_find = ttk.Entry(srch, width=24); self.ent_find.pack(side="left", padx=6)
        ttk.Button(srch, text="Load Case", command=self.load_data).pack(side="left")
        ttk.Button(srch, text="Tự nhận diện", command=self.autodetect_and_load).pack(side="left", padx=6)
        self.ent_find.bind("<KeyRelease>", lambda _e: self.filter_source())

        # Tiêu đề + trạng thái
        self.lbl_src_title = ttk.Label(left, text="Danh sách Load Case", style="Bold.TLabel")
        self.lbl_src_title.pack(anchor="w", pady=(2,0))
        self.lbl_status = ttk.Label(left, text="Chưa nạp dữ liệu.", foreground="gray")
        self.lbl_status.pack(anchor="w", pady=(0,6))

        # List nguồn
        src_box = ttk.Frame(left); src_box.pack(fill="both", expand=True)
        self.lst_src = tk.Listbox(src_box, selectmode="extended", width=36, height=22)
        self.lst_src.pack(side="left", fill="both", expand=True)
        sbs = ttk.Scrollbar(src_box, orient="vertical", command=self.lst_src.yview)
        sbs.pack(side="right", fill="y")
        self.lst_src.configure(yscrollcommand=sbs.set)

        # Bind DnD
        self.lst_src.bind("<ButtonPress-1>", self._dnd_start)
        self.lst_src.bind("<B1-Motion>", self._dnd_motion)
        self.lst_src.bind("<ButtonRelease-1>", self._dnd_release)

        # ========== RIGHT PANE (Group board) ==========
        right = ttk.Frame(self); right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)
        ttk.Label(right, text="NHÓM (kéo-thả LC vào khung) – mỗi Load Case chỉ ở 1 nhóm", style="Bold.TLabel").pack(anchor="w")
        from ui_group import GroupBoard  # import ở đây để tránh vòng lặp
        self.grp_board = GroupBoard(right, get_selected_cases_callable=self.get_selected_from_source)
        self.grp_board.pack(fill="both", expand=True)

        # Style đậm
        ttk.Style(self).configure("Bold.TLabel", font=("Segoe UI", 9, "bold"))

    # -------- Helpers --------
    def _default_engine(self) -> str:
        try:
            import config
            return getattr(config, "SELECTED_ENGINE", "ROBOT").upper()
        except Exception:
            return "ROBOT"

    def _current_selection_pairs(self):
        """Trả [(id, name), ...] theo các item đang chọn trong listbox."""
        pairs = []
        idxs = self.lst_src.curselection()
        for i in idxs:
            try:
                item = self.view_rows[i]
                # cố gắng đọc id/name linh hoạt
                if isinstance(item, dict):
                    _id = item.get("id") or item.get("Id") or item.get("ID") or item.get("name") or f"LC_{i+1}"
                    _name = item.get("name") or item.get("Name") or str(_id)
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    _id, _name = item[0], item[1]
                else:
                    _id, _name = f"LC_{i+1}", str(item)
                pairs.append((_id, _name))
            except Exception:
                continue
        return pairs

    def get_selected_from_source(self):
        return self._current_selection_pairs()

    # -------- DnD --------
    def _dnd_start(self, _e):
        self._drag["active"] = True
        self._drag["selection"] = self._current_selection_pairs()

    def _dnd_motion(self, _e):
        pass

    def _dnd_release(self, _e):
        if not self._drag["active"]:
            return
        self._drag["active"] = False
        sel = self._drag["selection"] or self._current_selection_pairs()
        target = getattr(self.grp_board, "current_drop", None)
        if target and sel:
            self.grp_board.claim_to_group(target, sel)
            pnl = self.grp_board.panels.get(target)
            if pnl:
                pnl.reload()

    # -------- Data ops --------
    def load_data(self):
        eng = (self.engine.get() or "").upper().strip()
        if eng == "SAP2000":
            # Kết nối SAP2000
            try:
                self.lbl_status.config(text="Đang kết nối SAP2000…")
            except Exception:
                pass

            sap_model, _ = connect_sap2000()
            if not sap_model:
                try:
                    self.lbl_status.config(text="Không kết nối được SAP2000.")
                except Exception:
                    pass
                messagebox.showerror(
                    "Không kết nối",
                    ("Không kết nối được SAP2000.\n"
                     "• Hãy mở SAP2000 trước.\n"
                     "• Chạy Python và SAP2000 cùng quyền (Admin/Non-Admin).\n"
                     "• Bản 64-bit phù hợp, đã cài SAP2000 OAPI.")
                )
                return

            # Lấy load cases
            try:
                rows, raw = get_load_cases_sap(sap_model)
            except Exception as e:
                messagebox.showerror("Lỗi khi đọc SAP2000", str(e))
                return

            self.view_rows, self.raw_by_id = rows or [], raw or {}
            self.populate_source()
            self.lbl_src_title.config(text="Danh sách Load Case (nguồn: SAP2000)")
            try:
                self.lbl_status.config(text=f"Đã tải {len(self.view_rows)} LC từ SAP2000.")
            except Exception:
                pass
            return

        # ROBOT
        try:
            self.lbl_status.config(text="Đang kết nối ROBOT…")
        except Exception:
            pass

        try:
            guard = COMGuard() if COMGuard else None
            self.rob = guard.connect() if guard else None
        except Exception:
            self.rob = None

        if not self.rob:
            try:
                self.lbl_status.config(text="Không kết nối được ROBOT.")
            except Exception:
                pass
            messagebox.showerror(
                "Không kết nối",
                ("Không kết nối được ROBOT.\n"
                 "• Hãy mở Robot Structural Analysis trước.\n"
                 "• Chạy Python và ROBOT cùng quyền (Admin/Non-Admin).")
            )
            return

        try:
            rows, raw = get_load_cases_robot(self.rob)
        except Exception as e:
            messagebox.showerror("Lỗi khi đọc ROBOT", str(e))
            return

        self.view_rows, self.raw_by_id = rows or [], raw or {}
        self.populate_source()
        self.lbl_src_title.config(text="Danh sách Load Case (nguồn: ROBOT)")
        try:
            self.lbl_status.config(text=f"Đã tải {len(self.view_rows)} LC từ ROBOT.")
        except Exception:
            pass

    def autodetect_and_load(self):
        """Thử SAP2000 trước, nếu không được thì ROBOT."""
        # Thử SAP2000
        try:
            self.lbl_status.config(text="Đang thử kết nối SAP2000…")
        except Exception:
            pass

        sap_model, _ = connect_sap2000()
        if sap_model:
            try:
                rows, raw = get_load_cases_sap(sap_model)
                if rows:
                    self.engine.set("SAP2000")
                    self.view_rows, self.raw_by_id = rows or [], raw or {}
                    self.populate_source()
                    self.lbl_src_title.config(text="Danh sách Load Case (nguồn: SAP2000)")
                    try:
                        self.lbl_status.config(text=f"Đã tải {len(self.view_rows)} LC từ SAP2000.")
                    except Exception:
                        pass
                    return
            except Exception:
                pass

        # Thử ROBOT
        try:
            self.lbl_status.config(text="Đang thử kết nối ROBOT…")
        except Exception:
            pass

        try:
            guard = COMGuard() if COMGuard else None
            self.rob = guard.connect() if guard else None
        except Exception:
            self.rob = None
        if self.rob:
            try:
                rows, raw = get_load_cases_robot(self.rob)
                if rows:
                    self.engine.set("ROBOT")
                    self.view_rows, self.raw_by_id = rows or [], raw or {}
                    self.populate_source()
                    self.lbl_src_title.config(text="Danh sách Load Case (nguồn: ROBOT)")
                    try:
                        self.lbl_status.config(text=f"Đã tải {len(self.view_rows)} LC từ ROBOT.")
                    except Exception:
                        pass
                    return
            except Exception:
                pass

        try:
            self.lbl_status.config(text="Không kết nối được SAP2000/ROBOT. Hãy mở phần mềm & chạy cùng quyền (Admin/Non-Admin).")
        except Exception:
            pass

    # -------- UI refresh --------
    def populate_source(self):
        """Đổ dữ liệu vào listbox theo self.view_rows."""
        self.lst_src.delete(0, tk.END)
        q = (self.ent_find.get() or "").strip().lower()
        for i, item in enumerate(self.view_rows):
            if isinstance(item, dict):
                name = item.get("name") or item.get("Name") or str(item.get("id") or item.get("Id") or (i+1))
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                name = str(item[1])
            else:
                name = str(item)
            if q and q not in name.lower():
                continue
            self.lst_src.insert(tk.END, name)

    def filter_source(self):
        self.populate_source()

    # -------- Context for ComboTab --------
    def get_context(self):
        """Trả về ngữ cảnh để ComboTab dùng (engine, raw_by_id, groups)."""
        try:
            eng = (self.engine.get() or "").upper().strip()
        except Exception:
            try:
                import config
                eng = getattr(config, "SELECTED_ENGINE", "ROBOT")
            except Exception:
                eng = "ROBOT"
        raw = self.raw_by_id or {}
        try:
            groups = self.grp_board.snapshot()
        except Exception:
            groups = {}
        return {"engine": eng, "raw_by_id": raw, "groups": groups}
