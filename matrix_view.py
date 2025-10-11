# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk

class MatrixView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.col_width = 120
        self.first_width = 160

        self.header = tk.Canvas(self, height=26, bg="#f7f1a6", highlightthickness=0)
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")

        table = ttk.Frame(self)
        table.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(table, show="headings", height=18)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.vsb = tk.Scrollbar(table, orient="vertical", command=self.tree.yview, width=16)
        self.vsb.grid(row=0, column=1, sticky="ns")
        table.grid_rowconfigure(0, weight=1)
        table.grid_columnconfigure(0, weight=1)

        def _on_tree_y(first, last):
            try:
                self.vsb.set(first, last)
                f, l = float(first), float(last)
                self.vsb.configure(state=("disabled" if l - f >= 1.0 - 1e-9 else "normal"))
            except Exception: pass
        self.tree.configure(yscrollcommand=_on_tree_y)

        self.hsb = ttk.Scrollbar(self, orient="horizontal", command=self._xscroll)
        self.hsb.grid(row=2, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=self._on_tree_x)

        self.tree.bind("<Configure>", lambda e: self._schedule_header())
        self.header.bind("<Configure>", lambda e: self._schedule_header())
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._schedule_header())
        self.tree.bind("<Expose>", lambda e: self._schedule_header())

        for w in (self.tree, self.header):
            w.bind("<MouseWheel>", self._mw_vertical)
            w.bind("<Shift-MouseWheel>", self._mw_horizontal)
            w.bind("<Button-4>", lambda e: self._mw_linux(+1))
            w.bind("<Button-5>", lambda e: self._mw_linux(-1))

        self._columns=[]; self._groups=[]
        self._header_job=None

    def _schedule_header(self):
        if self._header_job:
            try: self.after_cancel(self._header_job)
            except Exception: pass
        self._header_job = self.after_idle(self._rebuild_header_from_bbox)

    def _on_tree_x(self, first, last):
        self.hsb.set(first, last); self._schedule_header()

    def _xscroll(self, *args):
        self.tree.xview(*args); self._schedule_header()

    def _mw_vertical(self, e):
        delta = int(-1*(e.delta/120)) if getattr(e,'delta',0) else 0
        if delta: self.tree.yview_scroll(delta, "units"); return "break"

    def _mw_horizontal(self, e):
        delta = int(-1*(e.delta/120)) if getattr(e,'delta',0) else 0
        if delta: self.tree.xview_scroll(delta, "units")
        self._schedule_header(); return "break"

    def _mw_linux(self, direction):
        self.tree.yview_scroll(-direction, "units"); return "break"

    def build(self, columns_by_group, rows):
        self._groups=[]
        cols=["COMBO"]
        for g, lst in columns_by_group:
            self._groups.append((g, [k for (k,_lab) in lst]))
            cols += [k for (k,_lab) in lst]
        self._columns = cols

        self.tree["columns"] = cols
        self.tree.column("COMBO", width=self.first_width, anchor="w", stretch=False)
        we = self.tree
        self.tree.heading("COMBO", text="COMBO")
        for g, lst in columns_by_group:
            for key, label in lst:
                we.column(key, width=self.col_width, anchor="center", stretch=False)
                we.heading(key, text=label)

        for iid in self.tree.get_children():
            try: self.tree.delete(iid)
            except Exception: pass
        for r in rows: self.tree.insert("", "end", values=r)

        self.tree.yview_moveto(0.0)
        try: self.vsb.configure(state="normal")
        except Exception: pass
        self._schedule_header()

    def _rebuild_header_from_bbox(self):
        self.update_idletasks()
        cv = self.header; cv.delete("all")
        cols = self._columns
        if not cols: return
        children = self.tree.get_children()
        has_row = bool(children)
        iid = children[0] if has_row else None

        total_w = self.first_width + sum(int(self.tree.column(c, "width")) for c in cols[1:])
        start_frac = self.tree.xview()[0] if self.tree.xview() else 0.0
        start_offset = int(total_w * start_frac)

        x_positions = []
        if iid is not None:
            for c in cols:
                try:
                    b = self.tree.bbox(iid, column=c)
                except Exception:
                    b = None
                if b and len(b)>=4:
                    x, y, w, h = b
                else:
                    if not x_positions:
                        x = -start_offset; w = int(self.tree.column(c, "width"))
                    else:
                        x = x_positions[-1][0] + x_positions[-1][1]
                        w = int(self.tree.column(c, "width"))
                x_positions.append((x, w))
        else:
            x = -start_offset
            for c in cols:
                w = int(self.tree.column(c, "width"))
                x_positions.append((x, w)); x += w

        x0, w0 = x_positions[0]
        cv.create_rectangle(x0, 0, x0+w0, 26, fill="#f7f1a6", outline="")
        cv.create_text(x0 + w0/2, 13, text="COMBO", font=("Segoe UI", 9, "bold"))

        idx = 1
        for g, keys in self._groups:
            if not keys: continue
            start_x = x_positions[idx][0]
            w_sum = 0
            for _k in keys:
                w_sum += x_positions[idx][1]; idx += 1
            cv.create_rectangle(start_x, 0, start_x+w_sum, 26, fill="#f7f1a6", outline="")
            cv.create_text(start_x + w_sum/2, 13, text=g, font=("Segoe UI", 9, "bold"))
        cv.config(scrollregion=(0,0,total_w,26))
