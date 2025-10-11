# -*- coding: utf-8 -*-
import time
try:
    import pythoncom, win32com.client
    from win32com.client import constants as _c
except Exception:
    pythoncom = None
    win32com = None
    _c = None

def connect_robot(visible=True):
    if pythoncom is None or win32com is None:
        return None, None
    try:
        pythoncom.CoInitialize()
    except Exception: pass
    Dispatch = getattr(win32com.client, "EnsureDispatch", win32com.client.Dispatch)
    for pid in ("Robot.Application", "Robot.Application.1", "RSA.Main"):
        try:
            rob = Dispatch(pid)
            try: rob.Visible = bool(visible)
            except Exception: pass
            return rob, pid
        except Exception:
            continue
    return None, None

def has_attr(o, n):
    try:
        getattr(o, n); return True
    except Exception:
        return False

def pick(o, *names):
    for n in names:
        try:
            v = getattr(o, n)
            if v not in (None, ""): return v
        except Exception: pass
    return None

def enumerate_case_indices(cases):
    for cand in ("GetAllNumbers", "GetAll", "Numbers"):
        if has_attr(cases, cand):
            try:
                col = getattr(cases, cand)()
                idxs = []
                if hasattr(col, "Count") and hasattr(col, "Get"):
                    for k in range(1, int(col.Count)+1):
                        try:
                            n = col.Get(k)
                            if isinstance(n, int): idxs.append(n)
                            else:
                                num = pick(n, "Number","No","Id","ID","Index")
                                if isinstance(num, int): idxs.append(num)
                        except Exception: pass
                else:
                    try:
                        for n in col:
                            if isinstance(n, int): idxs.append(n)
                    except Exception: pass
                if idxs: return sorted(set(idxs))
            except Exception: pass
    try:
        total = int(cases.Count)
    except Exception:
        total = 0
    idxs=[]
    for i in range(1, total+1):
        try:
            _ = cases.Get(i); idxs.append(i)
        except Exception: pass
    return sorted(set(idxs))

def iterate_cases(cases):
    for n in enumerate_case_indices(cases):
        try: yield cases.Get(n)
        except Exception: pass

def get_load_cases_robot(rob):
    cases = rob.Project.Structure.Cases
    view, raw = [], {}
    for c in iterate_cases(cases):
        try: _ = c.CaseFactors; is_combo=True
        except Exception: is_combo=False
        if is_combo: continue
        cid  = pick(c, "Number","No","Id","ID","Index")
        name = pick(c, "Name","Label","name")
        nat  = pick(c, "Nature","CaseNature")
        aty  = pick(c, "AnalizeType","AnalyzeType","AnalysisType","Type")
        view.append((str(cid), str(name), nat, aty))
        raw[str(cid)] = {"id": str(cid), "name": str(name), "nature": nat, "analysis": aty}
    return view, raw

def robot_delete_combos_by_names(cases, names_set, prog=None):
    to_delete = []
    for c in iterate_cases(cases):
        try: _ = c.CaseFactors
        except Exception: continue
        try: nm = str(getattr(c, "Name", ""))
        except Exception: nm = ""
        if nm and nm in names_set:
            n = pick(c, "Number","No","Id","ID","Index")
            if isinstance(n, int): to_delete.append(n)
    if to_delete:
        try: cases.BeginMultiOperation()
        except Exception: pass
        total = len(to_delete)
        for i, n in enumerate(sorted(set(to_delete), reverse=True), start=1):
            try: cases.Delete(n)
            except Exception:
                try: cases.DeleteCase(n)
                except Exception: pass
            if prog: prog.step(1, hint=f"Xóa combo #{n} ({i}/{total})")
        try: cases.EndMultiOperation()
        except Exception: pass
    return len(to_delete)

def robot_plan_numbers(cases, how_many):
    used=set(); max_noncombo=0
    for c in iterate_cases(cases):
        num = pick(c, "Number","No","Id","ID","Index")
        if not isinstance(num, int): continue
        try: _ = c.CaseFactors; is_combo=True
        except Exception: is_combo=False
        used.add(num)
        if not is_combo and num>max_noncombo: max_noncombo=num
    start = max_noncombo + 1
    plan=[]; n=start
    while len(plan) < how_many:
        if n not in used: plan.append(n)
        n += 1
    return plan

def robot_create_combo_with_number(cases, number, name_hint):
    comb_type = getattr(_c, "I_CBT_ULS", 0) if _c else 0
    case_nat  = getattr(_c, "I_CN_PERMANENT", 0) if _c else 0
    anal_type = getattr(_c, "I_CAT_COMB", 0) if _c else 0
    for attempt in range(4):
        try:
            if attempt==0:
                return cases.CreateCombination(int(number), str(name_hint or f"COMBO_{number}"),
                                               int(comb_type), int(case_nat), int(anal_type))
            elif attempt==1:
                cmb = cases.CreateCombination(int(number)); cmb.Name = str(name_hint or f"COMBO_{number}"); return cmb
            elif attempt==2:
                cmb = cases.CreateCombination(); cmb.Name = str(name_hint or f"COMBO_{number}"); return cmb
            else:
                case_type_comb = getattr(_c, "I_CT_COMBINATION", 1) if _c is not None else 1
                cmb = cases.Create(int(number), int(case_type_comb)); _ = cmb.CaseFactors; cmb.Name = str(name_hint or f"COMBO_{number}"); return cmb
        except Exception: pass
    return None

# ----- COM Guard -----
class COMGuard:
    def __init__(self): self.rob = None
    def connect(self, visible=True):
        rob,_ = connect_robot(visible=visible); self.rob = rob; return rob
    def retry(self, visible=True):
        try:
            if pythoncom is not None: pythoncom.CoUninitialize()
        except Exception: pass
        try:
            if pythoncom is not None: pythoncom.CoInitialize()
        except Exception: pass
        return self.connect(visible=visible)
    def safe(self, fn, retries=2, raise_final=False):
        last=None
        for t in range(retries+1):
            try: return fn()
            except Exception as e:
                last=e
                if t<retries: self.retry(); continue
                if raise_final: raise
                return None