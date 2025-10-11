# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from config import ATTR_PERM, ATTR_OPTIONS, is_crane_group, CRANE_VERT_NAME, CRANE_HORZ_NAME

class ScrollFrame(ttk.Frame):
    """Frame có thanh cuộn dọc, dùng để chứa nhiều panel nhóm."""
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.viewport = ttk.Frame(self.canvas)
        self._vp_id = self.canvas.create_window((0, 0), window=self.viewport, anchor="nw")

        self.viewport.bind("<Configure>", self._on_view_config)
        self.canvas.bind("<Configure>", self._on_canvas_config)

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-1, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(+1, "units"))

    def _on_view_config(self, _ev=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_config(self, ev):
        self.canvas.itemconfigure(self._vp_id, width=self.canvas.winfo_width())

    def _on_mousewheel(self, ev):
        w = self.winfo_containing(self.winfo_pointerx(), self.winfo_pointery())
        if w is self.canvas:
            delta = int(-1 * (getattr(ev, "delta", 0) / 120)) if hasattr(ev, "delta") else 0
            if delta:
                self.canvas.yview_scroll(delta, "units")
                return "break"

class GroupPanel(ttk.LabelFrame):
    """
    items:
      - nhóm thường: (cid, name)
      - cầu trục (ĐỨNG/NGANG): (cid, name, side) với side in {"L","R"}
    """
    def __init__(self, parent, name, get_selected_cases_callable, claim_case, on_rename, on_delete, set_drop_target):
        super().__init__(parent, text=name)
        self._name = name
        self.get_selected_cases = get_selected_cases_callable
        self.claim_case = claim_case
        self.on_rename = on_rename
        self.on_delete = on_delete
        self.set_drop_target = set_drop_target
        self.attr = ATTR_PERM
        self.items = []

        head = ttk.Frame(self); head.pack(fill="x", pady=(4,4), padx=6)
        head.grid_columnconfigure(4, weight=1)
        ttk.Label(head, text="Thuộc tính:").grid(row=0, column=0, sticky="w")
        self.cbo_attr = ttk.Combobox(head, values=ATTR_OPTIONS, state="readonly", width=28)
        self.cbo_attr.set(self.attr); self.cbo_attr.grid(row=0, column=1, sticky="w", padx=6)
        self.cbo_attr.bind("<<ComboboxSelected>>", lambda e: setattr(self, "attr", self.cbo_attr.get()))
        ttk.Button(head, text="Đổi tên", command=self._rename).grid(row=0, column=2, padx=(8,4))
        ttk.Button(head, text="Xóa nhóm", command=self._delete).grid(row=0, column=3, padx=(0,0), sticky="w")

        body = ttk.Frame(self); body.pack(fill="both", expand=True, padx=6, pady=(0,6))
        body.bind("<Enter>", lambda e: self.set_drop_target(self._name))
        body.bind("<Leave>", lambda e: self.set_drop_target(None))

        self.lst = tk.Listbox(body, selectmode="extended", height=10)
        self.lst.pack(side="left", fill="both", expand=True)
        self.lst.bind("<Enter>", lambda e: self.set_drop_target(self._name))
        self.lst.bind("<Leave>", lambda e: self.set_drop_target(None))
        sby = ttk.Scrollbar(body, orient="vertical", command=self.lst.yview)
        sby.pack(side="right", fill="y")
        self.lst.configure(yscrollcommand=sby.set)

        self._sidebar = None
        if is_crane_group(self._name):
            sidebar = ttk.Frame(self); sidebar.pack(fill="x", padx=6, pady=(0,6))
            ttk.Label(sidebar, text="Hướng (cho mục chọn):").pack(side="left")
            self.cbo_side = ttk.Combobox(sidebar, width=10, state="readonly",
                                         values=["← Trái", "→ Phải"])
            try: self.cbo_side.current(0)
            except Exception: self.cbo_side.set("← Trái")
            self.cbo_side.pack(side="left", padx=(6,0))
            ttk.Button(sidebar, text="Gán", command=self._apply_side_to_selected).pack(side="left", padx=(6,0))
            self._sidebar = sidebar

        btns = ttk.Frame(self); btns.pack(fill="x", padx=6, pady=(0,6))
        ttk.Button(btns, text="Thêm từ danh sách bên trái", command=self.add_selected).pack(side="left")
        ttk.Button(btns, text="Xóa mục chọn", command=self.remove_selected).pack(side="left", padx=6)
        ttk.Button(btns, text="Xóa hết", command=self.clear_all).pack(side="left")

    def _rename(self):
        new_name = simpledialog.askstring("Đổi tên nhóm", "Tên mới:", initialvalue=self._name, parent=self)
        if not new_name: return
        new_name = new_name.strip()
        if not new_name or new_name == self._name: return
        if not self.on_rename(self._name, new_name):
            messagebox.showwarning("Trùng tên", "Tên nhóm đã tồn tại."); return
        self._name = new_name; self.configure(text=new_name)
        if self._sidebar and not is_crane_group(self._name):
            try: self._sidebar.destroy()
            except Exception: pass
            self._sidebar = None
        elif (not self._sidebar) and is_crane_group(self._name):
            sidebar = ttk.Frame(self); sidebar.pack(fill="x", padx=6, pady=(0,6))
            ttk.Label(sidebar, text="Hướng (cho mục chọn):").pack(side="left")
            self.cbo_side = ttk.Combobox(sidebar, width=10, state="readonly",
                                         values=["← Trái", "→ Phải"])
            try: self.cbo_side.current(0)
            except Exception: self.cbo_side.set("← Trái")
            self.cbo_side.pack(side="left", padx=(6,0))
            ttk.Button(sidebar, text="Gán", command=self._apply_side_to_selected).pack(side="left", padx=(6,0))
            self._sidebar = sidebar

    def _delete(self):
        if messagebox.askyesno("Xóa nhóm", f"Xóa nhóm '{self._name}' ?"):
            self.on_delete(self._name)

    def add_selected(self):
        selected = self.get_selected_cases()
        if not selected:
            messagebox.showinfo("Chưa chọn tải","Chọn 1 hoặc nhiều Load Case ở danh sách nguồn."); return
        for (cid, nm) in selected:
            self.claim_case(self._name, cid, nm)
        self.reload()

    def remove_selected(self):
        sel = list(self.lst.curselection()); sel.reverse()
        for i in sel:
            try: self.items.pop(i)
            except Exception: pass
        self.reload()

    def clear_all(self):
        if messagebox.askyesno("Xóa hết","Xóa tất cả tải trong nhóm?"):
            self.items.clear(); self.reload()

    def _apply_side_to_selected(self):
        from config import is_crane_group  # tránh vòng import
        if not is_crane_group(self._name): return
        val = self.cbo_side.get() or "← Trái"
        side = "L" if "Trái" in val else "R"
        sel = list(self.lst.curselection())
        if not sel:
            messagebox.showinfo("Chưa chọn", "Hãy chọn các mục trong danh sách rồi bấm Gán.")
            return
        for i in sel:
            try:
                cid, nm = self.items[i][0], self.items[i][1]
                self.items[i] = (cid, nm, side)
            except Exception: pass
        self.reload()

    def reload(self):
        from config import is_crane_group
        self.lst.delete(0, "end")
        for item in self.items:
            cid, nm = item[0], item[1]
            if is_crane_group(self._name):
                side = (item[2] if len(item) >= 3 else "L")
                tag = "←" if side == "L" else "→"
                self.lst.insert("end", f"{cid} – {nm}  [{tag}]")
            else:
                self.lst.insert("end", f"{cid} – {nm}")

    @property
    def name(self): return self._name
    def snapshot(self): return {"attr": self.attr, "items": list(self.items)}

class GroupBoard(ttk.Frame):
    def __init__(self, parent, get_selected_cases_callable):
        super().__init__(parent)
        self.get_selected_cases = get_selected_cases_callable
        self.groups = {}
        self.panels = {}
        self.order = []
        self.current_drop = None

        bar = ttk.Frame(self); bar.pack(fill="x", pady=(0,6))
        ttk.Button(bar, text="Thêm nhóm", command=self.add_group_dialog).pack(side="left")
        ttk.Button(bar, text="Thêm nhóm cầu trục", command=self.add_crane_groups).pack(side="left", padx=6)

        ttk.Label(bar, text="Sắp xếp nhóm:").pack(side="left", padx=(12,0))
        ttk.Button(bar, text="⤒ Lên đầu", command=self.move_top).pack(side="left", padx=(4,2))
        ttk.Button(bar, text="↑ Lên", command=self.move_up).pack(side="left", padx=2)
        ttk.Button(bar, text="↓ Xuống", command=self.move_down).pack(side="left", padx=2)
        ttk.Button(bar, text="⤓ Xuống cuối", command=self.move_bottom).pack(side="left", padx=2)

        self.sel_group = tk.StringVar(value="")
        ttk.Label(bar, text="  Nhóm chọn:").pack(side="left", padx=(12,4))
        self.cbo_sel = ttk.Combobox(bar, textvariable=self.sel_group, state="readonly", width=28, values=[])
        self.cbo_sel.pack(side="left")

        self.scroll = ScrollFrame(self)
        self.scroll.pack(fill="both", expand=True)
        self.body = self.scroll.viewport
        self._cols = 2

    def add_crane_groups(self):
        created = 0
        for nm in (CRANE_VERT_NAME, CRANE_HORZ_NAME):
            if nm not in self.groups and nm not in self.panels:
                self.add_group(nm, attr="TẠM THỜI – NGẮN HẠN"); created += 1
        if created == 0:
            messagebox.showinfo("Nhóm cầu trục", "Hai nhóm đã tồn tại.")
        else:
            messagebox.showinfo("Nhóm cầu trục", f"Đã tạo {created} nhóm (mặc định 'TẠM THỜI – NGẮN HẠN').")

    def set_drop_target(self, name): self.current_drop = name
    def add_group_dialog(self):
        name = simpledialog.askstring("Thêm nhóm", "Tên nhóm:", parent=self)
        if not name: return
        self.add_group(name.strip())

    def add_group(self, name, attr="TẢI TRỌNG THƯỜNG XUYÊN"):
        if not name: return
        if name in self.groups:
            messagebox.showwarning("Trùng tên", "Tên nhóm đã tồn tại."); return
        self.groups[name] = {"attr": attr, "items": []}
        pnl = GroupPanel(self.body, name,
                         get_selected_cases_callable=self.get_selected_cases,
                         claim_case=self._claim_case,
                         on_rename=self._rename_group,
                         on_delete=self._delete_group,
                         set_drop_target=self.set_drop_target)
        pnl.attr = attr; pnl.cbo_attr.set(attr)
        self.panels[name] = pnl
        self.order.append(name)
        self._relayout(); pnl.reload(); self._refresh_combo_names()

    def _rename_group(self, old, new):
        if new in self.groups: return False
        self.groups[new] = self.groups.pop(old)
        pnl = self.panels.pop(old)
        self.panels[new] = pnl
        pnl.configure(text=new)
        self.order = [new if n==old else n for n in self.order]
        self._relayout(); self._refresh_combo_names(); return True

    def _delete_group(self, name):
        try:
            pnl = self.panels.pop(name); pnl.destroy()
        except Exception: pass
        self.groups.pop(name, None)
        self.order = [n for n in self.order if n != name]
        self._relayout(); self._refresh_combo_names()

    def _relayout(self):
        for w in self.body.winfo_children(): w.grid_forget()
        names = list(self.order)
        for idx, nm in enumerate(names):
            pnl = self.panels[nm]
            r = idx // self._cols; c = idx % self._cols
            pnl.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            self.body.grid_columnconfigure(c, weight=1)
        total_rows = (len(names)+self._cols-1)//self._cols or 1
        for r in range(total_rows):
            self.body.grid_rowconfigure(r, weight=1)
        self.body.update_idletasks()
        self.scroll.canvas.configure(scrollregion=self.scroll.canvas.bbox("all"))

    def _current_idx(self):
        name = self.sel_group.get().strip()
        if name and name in self.order:
            return self.order.index(name)
        return None

    def _refresh_combo_names(self):
        self.cbo_sel["values"] = list(self.order)
        if self.sel_group.get() not in self.order:
            self.sel_group.set(self.order[0] if self.order else "")

    def move_up(self):
        i = self._current_idx()
        if i is None or i<=0: return
        self.order[i-1], self.order[i] = self.order[i], self.order[i-1]
        self._relayout(); self._refresh_combo_names()

    def move_down(self):
        i = self._current_idx()
        if i is None or i>=len(self.order)-1: return
        self.order[i+1], self.order[i] = self.order[i], self.order[i+1]
        self._relayout(); self._refresh_combo_names()

    def move_top(self):
        i = self._current_idx()
        if i is None or i<=0: return
        name = self.order.pop(i)
        self.order.insert(0, name)
        self._relayout(); self._refresh_combo_names()

    def move_bottom(self):
        i = self._current_idx()
        if i is None or i>=len(self.order)-1: return
        name = self.order.pop(i)
        self.order.append(name)
        self._relayout(); self._refresh_combo_names()

    def _claim_case(self, target_group_name, cid, nm):
        owners = []
        for gname, pnl in self.panels.items():
            for it in pnl.items:
                if (isinstance(it, (list, tuple)) and len(it) >= 1 and it[0] == cid):
                    owners.append(gname); break

        if owners == [target_group_name]: return
        if owners and not (len(owners) == 1 and owners[0] == target_group_name):
            ok = messagebox.askyesno(
                "Đã tồn tại ở nhóm khác",
                f"Load Case {cid} – {nm} đang nằm trong nhóm: {', '.join(owners)}.\n"
                f"Chuyển sang '{target_group_name}'?",
                icon="warning"
            )
            if not ok: return

        for gname in owners:
            if gname == target_group_name: continue
            pnl = self.panels[gname]
            pnl.items = [it for it in pnl.items if not (len(it) >= 1 and it[0] == cid)]
            pnl.reload()

        tgt = self.panels[target_group_name]
        if cid not in {it[0] for it in tgt.items if isinstance(it, (list, tuple)) and len(it) >= 1}:
            from config import is_crane_group
            if is_crane_group(target_group_name):
                tgt.items.append((cid, nm, "L"))
            else:
                tgt.items.append((cid, nm))
            tgt.reload()

    def claim_to_group(self, gname, selection):
        if not gname or gname not in self.panels: return
        for (cid, nm) in selection: self._claim_case(gname, cid, nm)

    def snapshot(self):
        out = {}
        for name in self.order:
            pnl = self.panels[name]
            out[name] = pnl.snapshot()
        self.groups = out
        return out