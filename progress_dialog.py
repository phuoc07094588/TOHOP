# -*- coding: utf-8 -*-
import time
import tkinter as tk
from tkinter import ttk

class ProgressDialog(tk.Toplevel):
    def __init__(self, parent, title="Đang xử lý", total=100):
        super().__init__(parent)
        self.title(title); self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind("<Escape>", lambda e: self.cancel())
        self.cancelled = False
        self.total = max(1, int(total))
        self.progress_val = 0
        self.start_ts = time.time()
        self.last_hint = ""

        frm = ttk.Frame(self); frm.pack(fill="both", expand=True, padx=10, pady=10)
        self.lbl = ttk.Label(frm, text="Bắt đầu...", anchor="w"); self.lbl.pack(fill="x", pady=(0,6))
        self.pb = ttk.Progressbar(frm, mode="determinate", maximum=self.total); self.pb.pack(fill="x")

        meta = ttk.Frame(frm); meta.pack(fill="x", pady=(6,0))
        self.lbl_eta = ttk.Label(meta, text="ETA: —"); self.lbl_eta.pack(side="left")
        self.lbl_pct = ttk.Label(meta, text="0%"); self.lbl_pct.pack(side="right")

        log_box = ttk.Frame(frm); log_box.pack(fill="both", expand=True, pady=(8,0))
        self.txt = tk.Text(log_box, height=10, wrap="word"); self.txt.pack(side="left", fill="both", expand=True)
        sby = ttk.Scrollbar(log_box, orient="vertical", command=self.txt.yview); sby.pack(side="right", fill="y")
        self.txt.configure(yscrollcommand=sby.set)

        btns = ttk.Frame(frm); btns.pack(fill="x", pady=(8,0))
        ttk.Button(btns, text="Hủy", command=self.cancel).pack(side="right")
        try:
            self.transient(parent.winfo_toplevel()); self.grab_set()
        except Exception: pass
        self._pump()

    def _pump(self):
        try: self.update()
        except Exception: pass
    def _on_close(self): self.cancel()
    def cancel(self):
        self.cancelled = True; self.log(">> ĐÃ NHẤN HỦY – sẽ dừng sau khi hoàn tất mục đang chạy.")
    def log(self, s):
        self.txt.insert("end", s + "\n"); self.txt.see("end"); self._pump()
    def set_status(self, s):
        self.lbl.config(text=s); self._pump()
    def _eta_text(self):
        elapsed = time.time() - self.start_ts
        done = max(1, self.progress_val)
        rate = elapsed / float(done)
        remain = max(0.0, (self.total - done) * rate)
        def _fmt(sec):
            if sec < 1: return "<1s"
            m, s = divmod(int(sec+0.5), 60)
            h, m = divmod(m, 60)
            if h: return f"{h}h{m:02d}m{s:02d}s"
            if m: return f"{m}m{s:02d}s"
            return f"{s}s"
        return f"Đã chạy: {_fmt(elapsed)}  |  Còn lại (ước tính): {_fmt(remain)}"
    def step(self, n=1, hint=""):
        self.progress_val += int(n)
        if self.progress_val > self.total: self.progress_val = self.total
        self.pb["value"] = self.progress_val
        pct = int(round(self.progress_val * 100 / self.total))
        self.lbl_pct.config(text=f"{pct}%")
        if hint and hint != self.last_hint:
            self.last_hint = hint; self.log(hint)
        self.lbl_eta.config(text="ETA: " + self._eta_text()); self._pump()
    def set_total(self, total):
        self.total = max(1, int(total)); self.pb.configure(maximum=self.total); self._pump()
    def close(self):
        try: self.grab_release()
        except Exception: pass
        self.destroy()