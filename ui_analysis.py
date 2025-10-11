# -*- coding: utf-8 -*-
import math
import tkinter as tk
from tkinter import ttk, messagebox
import config
from sap_helper import connect_sap2000

FRAME_TYPE = 2  # CSI object type id for Frame elements

TYPE_LABELS = {
    1: "I-Section",
    7: "Pipe",
    8: "Rectangle",
    9: "Circle",
    6: "Tube/Box",
}

class AnalysisTab(ttk.Frame):
    """Tab PHÂN TÍCH: lấy kích thước (h_w, b_f, t_f, t_w) & tính đặc trưng hình học cơ bản."""
    def __init__(self, parent):
        super().__init__(parent)
        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", padx=8, pady=(8,4))

        ttk.Label(bar, text="PHÂN TÍCH – Lấy thông tin cấu kiện (SAP2000)", font=("Segoe UI", 10, "bold")).pack(side="left")
        btns = ttk.Frame(bar)
        btns.pack(side="right")
        ttk.Button(btns, text="LẤY THÔNG TIN CẤU KIỆN", command=self.fetch).pack(side="left", padx=(0,6))
        ttk.Button(btns, text="TT đặc trưng hình học", command=self.compute_props).pack(side="left")

        # Table frame with both scrollbars
        table_wrap = ttk.Frame(self)
        table_wrap.pack(fill="both", expand=True, padx=8, pady=(0,8))

        cols = ("frame","section","type","h_w","b_f","t_f","t_w",
                "A","Ix-x","Iy-y","Wx-x","Wy-y","rx-x","ry-y","Sx-x","Sy-y")
        widths = (100,220,110,90,90,90,90, 100,110,110,110,110,110,110,110,110)

        self.xscroll = ttk.Scrollbar(table_wrap, orient="horizontal")
        self.yscroll = ttk.Scrollbar(table_wrap, orient="vertical")
        self.tree = ttk.Treeview(
            table_wrap, columns=cols, show="headings", height=18,
            xscrollcommand=self.xscroll.set, yscrollcommand=self.yscroll.set
        )
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")

        self.xscroll.config(command=self.tree.xview)
        self.yscroll.config(command=self.tree.yview)
        self.xscroll.pack(side="bottom", fill="x")
        self.yscroll.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.status = ttk.Label(self, text="Sẵn sàng.", anchor="w")
        self.status.pack(fill="x", padx=8, pady=(0,8))

    def _set_status(self, msg):
        try: self.status.config(text=msg)
        except Exception: pass

    # ---------------- Core ----------------
    def fetch(self):
        eng = getattr(config, "SELECTED_ENGINE", "ROBOT").upper()
        if eng != "SAP2000":
            messagebox.showwarning("Sai phần mềm", "Tab này chỉ hoạt động với SAP2000.\nVui lòng chọn SAP2000 ở CẤU HÌNH.")
            return
        sap_model, _ = connect_sap2000(visible=False)
        if not sap_model:
            messagebox.showerror("Không kết nối", "Không kết nối được SAP2000. Hãy mở mô hình SAP2000 rồi thử lại.")
            return

        # selected frames
        try:
            res = sap_model.SelectObj.GetSelected()
            if isinstance(res, tuple):
                if len(res) == 4:
                    _ret, n, types, names = res
                elif len(res) == 3:
                    n, types, names = res
                else:
                    raise ValueError("GetSelected() trả về định dạng không hỗ trợ.")
            else:
                n, types, names = sap_model.SelectObj.GetSelected(0, [], [])
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không lấy được danh sách phần tử đang chọn.\n{e}")
            return

        frames = [str(nm) for t, nm in zip(list(types or []), list(names or [])) if int(t) == FRAME_TYPE]
        if not frames:
            messagebox.showinfo("Thông báo", "Không có phần tử FRAME nào đang được chọn trong SAP2000.")
            return

        # clear table
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        for fname in frames:
            sec_name = self._get_section_name(sap_model, fname)
            row = self._read_4fields(sap_model, sec_name)
            self.tree.insert("", "end", values=(
                fname, sec_name or "", row.get("type",""),
                self._fmt(row.get("h_w")), self._fmt(row.get("b_f")),
                self._fmt(row.get("t_f")), self._fmt(row.get("t_w")),
                "", "", "", "", "", "", "", "", ""
            ))
        self._set_status(f"Đã nạp {len(frames)} phần tử FRAME.")

    # ---- Compute properties for current table rows
    def compute_props(self):
        # iterate rows and compute based on type + dims
        updated = 0
        for iid in self.tree.get_children():
            vals = list(self.tree.item(iid, "values"))
            try:
                typ = (vals[2] or "").strip()
                hw = self._to_float(vals[3])
                bf = self._to_float(vals[4])
                tf = self._to_float(vals[5])
                tw = self._to_float(vals[6])
                # compute
                A, Ix, Iy, Wx, Wy, rx, ry, Sx, Sy = self._calc_props(typ, hw, bf, tf, tw)
                vals[7]  = self._fmt(A)
                vals[8]  = self._fmt(Ix)
                vals[9]  = self._fmt(Iy)
                vals[10] = self._fmt(Wx)
                vals[11] = self._fmt(Wy)
                vals[12] = self._fmt(rx)
                vals[13] = self._fmt(ry)
                vals[14] = self._fmt(Sx)
                vals[15] = self._fmt(Sy)
                self.tree.item(iid, values=vals)
                updated += 1
            except Exception:
                continue
        messagebox.showinfo("Xong", f"Đã tính đặc trưng hình học cho {updated} dòng.")
        self._set_status(f"Đã tính đặc trưng cho {updated} cấu kiện.")

    # ---------------- Helpers ----------------
    def _fmt(self, v):
        try:
            if v is None or v == "": return ""
            if isinstance(v, (int, float)): return f"{v:.6g}"
            return str(v)
        except Exception:
            return ""

    def _to_float(self, s):
        try:
            if s is None or s == "": return None
            return float(s)
        except Exception:
            return None

    def _get_section_name(self, sap_model, frame_name):
        try:
            res = sap_model.FrameObj.GetSection(frame_name)
            if isinstance(res, tuple):
                if len(res) >= 3: return res[-2]
                if len(res) == 2: return res[0]
            return str(res)
        except Exception:
            return None

    def _get_type_code(self, pf, sec_name):
        try:
            res = pf.GetTypeOAPI(sec_name)
            if isinstance(res, tuple):
                if len(res) == 2: return int(res[1])
                if len(res) >= 1: return int(res[-1])
            return int(res)
        except Exception:
            return None

    def _ok(self, tup):
        if not isinstance(tup, tuple): return False, 0
        if len(tup) == 0: return False, 0
        if isinstance(tup[0], (int, float)):
            return (tup[0] == 0), 1
        return True, 0

    def _read_4fields(self, sap_model, sec_name):
        pf = sap_model.PropFrame
        code = self._get_type_code(pf, sec_name)
        label = TYPE_LABELS.get(code, f"Type#{code}" if code is not None else "")

        if code == 1 or label == "I-Section":
            try:
                res = pf.GetISection(sec_name)
                ok, offset = self._ok(res if isinstance(res, tuple) else (res,))
                if ok:
                    tup = res
                    t3 = float(tup[2+offset])
                    tw = float(tup[3+offset])
                    tf = float(tup[4+offset])
                    tfb = float(tup[5+offset])
                    bf = float(tup[6+offset])
                    bfb = float(tup[7+offset])
                    b_f = bf if (bf is not None and bf != 0) else bfb
                    t_f = tf if (tf is not None and tf != 0) else tfb
                    return {"type":"I-Section", "h_w":t3, "b_f":b_f, "t_f":t_f, "t_w":tw}
            except Exception:
                pass

        if code == 8 or label == "Rectangle":
            try:
                res = pf.GetRectangle(sec_name)
                ok, offset = self._ok(res if isinstance(res, tuple) else (res,))
                if ok:
                    tup = res
                    t3 = float(tup[2+offset])
                    t2 = float(tup[3+offset])
                    return {"type":"Rectangle", "h_w":t3, "b_f":t2, "t_f":None, "t_w":None}
            except Exception:
                pass

        if code == 6 or label == "Tube/Box":
            try:
                res = pf.GetTube(sec_name)
                ok, offset = self._ok(res if isinstance(res, tuple) else (res,))
                if ok:
                    tup = res
                    t3 = float(tup[2+offset])
                    t2 = float(tup[3+offset])
                    tf = float(tup[4+offset])
                    tw = float(tup[5+offset])
                    return {"type":"Tube/Box", "h_w":t3, "b_f":t2, "t_f":tf, "t_w":tw}
            except Exception:
                pass

        if code == 7 or label == "Pipe":
            try:
                res = pf.GetPipe(sec_name)
                ok, offset = self._ok(res if isinstance(res, tuple) else (res,))
                if ok:
                    tup = res
                    D = float(tup[2+offset])
                    thk = float(tup[3+offset])
                    return {"type":"Pipe", "h_w":D, "b_f":None, "t_f":None, "t_w":thk}
            except Exception:
                pass

        if code == 9 or label == "Circle":
            try:
                res = pf.GetCircle(sec_name)
                ok, offset = self._ok(res if isinstance(res, tuple) else (res,))
                if ok:
                    tup = res
                    D = float(tup[2+offset])
                    return {"type":"Circle", "h_w":D, "b_f":None, "t_f":None, "t_w":None}
            except Exception:
                pass

        return {"type":label or "", "h_w":None, "b_f":None, "t_f":None, "t_w":None}

    # ---------- Section property formulas (elastic) ----------
    def _calc_props(self, typ, h, b, tf, tw):
        A = Ix = Iy = Wx = Wy = rx = ry = Sx = Sy = None
        if typ == "I-Section" and all(v is not None for v in (h,b,tf,tw)):
            bf = b
            A = 2*bf*tf + (h-2*tf)*tw
            Ix = 2*((bf*tf**3)/12 + bf*tf*(h/2 - tf/2)**2) + (tw*(h-2*tf)**3)/12
            Iy = 2*((bf**3*tf)/12) + (tw**3*(h-2*tf))/12
            Wx = Ix/(h/2) if h else None
            Wy = Iy/(bf/2) if bf else None
            rx = math.sqrt(Ix/A) if A and Ix is not None else None
            ry = math.sqrt(Iy/A) if A and Iy is not None else None
            Sx = bf*tf*(h - tf) + (h-2*tf)*tw*(h-2*tf)/4
            Sy = (bf**2*tf)/2 + (tw**2*(h-2*tf))/4
        elif typ == "Rectangle" and h is not None and b is not None:
            A = b*h
            Ix = b*h**3/12.0
            Iy = h*b**3/12.0
            Wx = Ix/(h/2) if h else None
            Wy = Iy/(b/2) if b else None
            rx = math.sqrt(Ix/A) if A and Ix is not None else None
            ry = math.sqrt(Iy/A) if A and Iy is not None else None
            Sx = b*h**2/4.0
            Sy = h*b**2/4.0
        elif typ == "Tube/Box" and all(v is not None for v in (h,b,tf,tw)):
            A = b*h - (b-2*tw)*(h-2*tf)
            Ix = (b*h**3 - (b-2*tw)*(h-2*tf)**3)/12.0
            Iy = (h*b**3 - (h-2*tf)*(b-2*tw)**3)/12.0
            Wx = Ix/(h/2) if h else None
            Wy = Iy/(b/2) if b else None
            rx = math.sqrt(Ix/A) if A and Ix is not None else None
            ry = math.sqrt(Iy/A) if A and Iy is not None else None
            Sx = (b*h**2 - (b-2*tw)*(h-2*tf)**2)/4.0
            Sy = (h*b**2 - (h-2*tf)*(b-2*tw)**2)/4.0
        elif typ == "Pipe" and h is not None and tw is not None:
            D = h; t = tw
            A = math.pi/4.0 * (D**2 - (D-2*t)**2)
            Ix = math.pi/64.0 * (D**4 - (D-2*t)**4)
            Iy = Ix
            Wx = Ix/(D/2) if D else None
            Wy = Wx
            rx = math.sqrt(Ix/A) if A and Ix is not None else None
            ry = rx
            Ro = D/2.0; Ri = Ro - t
            Sx = Sy = (4.0/3.0)*(Ro**3 - Ri**3)
        elif typ == "Circle" and h is not None:
            D = h
            A = math.pi/4.0 * D**2
            Ix = math.pi/64.0 * D**4
            Iy = Ix
            Wx = Ix/(D/2) if D else None
            Wy = Wx
            rx = math.sqrt(Ix/A) if A and Ix is not None else None
            ry = rx
            Sx = Sy = 4.0/3.0 * (D/2.0)**3
        return A, Ix, Iy, Wx, Wy, rx, ry, Sx, Sy
