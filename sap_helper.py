# -*- coding: utf-8 -*-
from config import SKIP_VERIFY_COUNT
try:
    import pythoncom, win32com.client
except Exception:
    pythoncom = None
    win32com = None

def connect_sap2000(visible=True):
    if pythoncom is None or win32com is None:
        return None, None
    try:
        pythoncom.CoInitialize()
    except Exception: pass
    helper = None
    sap_obj = None
    try:
        helper = win32com.client.Dispatch("SAP2000v1.Helper")
        try:
            sap_obj = helper.GetObject("CSI.SAP2000.API.SapObject")
        except Exception:
            sap_obj = None
    except Exception:
        helper = None
    if sap_obj is None:
        try:
            sap_obj = win32com.client.GetObject(None, "CSI.SAP2000.API.SapObject")
        except Exception:
            sap_obj = None
    if sap_obj is None:
        try:
            sap_obj = win32com.client.Dispatch("CSI.SAP2000.API.SapObject")
        except Exception:
            sap_obj = None
    if sap_obj is None:
        return None, None
    try:
        sap_model = sap_obj.SapModel
    except Exception:
        return None, None
    try:
        if hasattr(sap_obj, "VisibilitySet"):
            sap_obj.VisibilitySet(bool(visible))
    except Exception: pass
    return sap_model, "SAP2000"

def get_load_cases_sap(sap_model):
    view, raw = [], {}
    try:
        out = sap_model.LoadCases.GetNameList()
        if isinstance(out, tuple):
            if len(out) == 3: ret, n, names = out
            elif len(out) == 2: n, names = out; ret = 0
            else: ret, n, names = out[0], out[1], out[2]
        else:
            n, names = sap_model.LoadCases.GetNameList(); ret = 0
        names = names or []
        for i, nm in enumerate(names, start=1):
            cid = str(i); name = str(nm)
            nat = "SAP"; aty = "STATIC"
            view.append((cid, name, nat, aty))
            raw[cid] = {"id": cid, "name": name, "nature": nat, "analysis": aty}
    except Exception:
        view, raw = [], {}
    return view, raw

def _sap_count_combo_items(sap_model, combo_name):
    try:
        rc = getattr(sap_model, "RespCombo", None)
        if rc is not None:
            try:
                ret, n, eT, nm, sf = rc.GetCaseList(combo_name)
                if isinstance(n, int) and n >= 0: return int(n)
                if isinstance(nm, (list, tuple)): return len(nm)
            except Exception: pass
            try:
                n, eT, nm, sf, ret = rc.GetCaseList(0, [], [], [], combo_name)
                if isinstance(n, int) and n >= 0: return int(n)
                if isinstance(nm, (list, tuple)): return len(nm)
            except Exception: pass
    except Exception: pass
    try:
        lc = getattr(sap_model, "LoadCombinations", None)
        if lc is not None:
            try:
                ret, n, names, sfs, eType = lc.GetCaseList(combo_name)
                if isinstance(n, int) and n >= 0: return int(n)
                if isinstance(names, (list, tuple)): return len(names)
            except Exception: pass
            try:
                names, sfs, eType = lc.GetCaseList(combo_name)
                if isinstance(names, (list, tuple)): return len(names)
            except Exception: pass
    except Exception: pass
    return -1

def sap_delete_combos_by_names(sap_model, names_set, prog=None):
    deleted = 0; tried = False
    try:
        lc = sap_model.LoadCombinations; tried = True
        ret, n, c_names = lc.GetNameList()
        c_names = c_names or []
        total = len([nm for nm in c_names if nm in names_set]); i = 0
        for nm in c_names:
            if nm in names_set:
                i += 1
                try:
                    ok = lc.Delete(nm)
                    if ok in (0, None): deleted += 1
                except Exception:
                    try:
                        lc.SetSelected(nm, True); lc.DeleteSelected(); deleted += 1
                    except Exception: pass
                if prog: prog.step(1, hint=f"Xóa '{nm}' ({i}/{total})")
    except Exception: pass

    if deleted == 0:
        try:
            rc = sap_model.RespCombo; tried = True
            ret, n, c_names = rc.GetNameList()
            c_names = c_names or []
            total = len([nm for nm in c_names if nm in names_set]); i = 0
            for nm in c_names:
                if nm in names_set:
                    i += 1
                    try:
                        ok = rc.Delete(nm)
                        if ok in (0, None): deleted += 1
                    except Exception: pass
                    if prog: prog.step(1, hint=f"Xóa '{nm}' ({i}/{total})")
        except Exception: pass
    return deleted, tried

def add_combo_batch(sap_model, combo_name, items, combo_type=0):
    items = [(str(nm).strip(), float(sf)) for (nm, sf) in (items or []) if str(nm).strip() and abs(float(sf))>1e-12]
    if not combo_name or not items: return 0
    added = 0
    rc = getattr(sap_model, "RespCombo", None)
    if rc is not None:
        try:
            try: rc.Delete(combo_name)
            except Exception: pass
            try:
                r = rc.Add(combo_name, int(combo_type))
                if r not in (0, None): rc.Add(combo_name)
            except Exception:
                rc.Add(combo_name)
            n = len(items)
            e_types = [0]*n; names = [nm for (nm,_sf) in items]; sfs = [float(sf) for (_nm,sf) in items]
            try:
                rc.SetCaseList(Name=combo_name, NumberItems=n, eCNameType=e_types, MyName=names, SF=sfs); added = n
            except Exception:
                rc.SetCaseList(combo_name, n, e_types, names, sfs); added = n
        except Exception:
            for (case_nm, coef) in items:
                ok = False
                for mname in ("SetCaseList", "SetCaseList_1", "SetCaseList_2"):
                    fn = getattr(rc, mname, None)
                    if fn is None: continue
                    try:
                        fn(Name=combo_name, eCNameType=0, MyName=str(case_nm), SF=float(coef)); ok=True; break
                    except Exception: pass
                    try:
                        fn(combo_name, 0, str(case_nm), float(coef)); ok=True; break
                    except Exception: pass
                if not ok:
                    addcase = getattr(rc, "AddCase", None)
                    if addcase is not None:
                        try:
                            addcase(combo_name, 0, str(case_nm), float(coef)); ok=True
                        except Exception: ok=False
                if ok: added += 1

    if added == 0:
        lc = getattr(sap_model, "LoadCombinations", None)
        if lc is not None:
            try:
                try: lc.Delete(combo_name)
                except Exception: pass
                try:
                    r = lc.Add(combo_name, int(combo_type))
                    if r not in (0, None): lc.Add(combo_name)
                except Exception:
                    lc.Add(combo_name)
                n = len(items); names = [nm for (nm,_sf) in items]; sfs = [float(sf) for (_nm,sf) in items]
                try:
                    lc.SetCaseList(combo_name, n, names, sfs, 0); added = n
                except Exception:
                    lc.SetCaseList(combo_name, names, sfs, 0); added = n
            except Exception:
                for (case_nm, coef) in items:
                    ok=False
                    try:
                        lc.AddCase(combo_name, case_nm, 0, float(coef)); ok=True
                    except Exception: pass
                    if not ok:
                        try:
                            lc.AddCaseFactor(combo_name, case_nm, float(coef)); ok=True
                        except Exception: ok=False
                    if ok: added += 1
    if not SKIP_VERIFY_COUNT:
        try:
            cnt = _sap_count_combo_items(sap_model, combo_name)
            if isinstance(cnt, int) and cnt >= 0: added = cnt
        except Exception: pass
    return added

def sap_create_combo_and_add_factors(sap_model, combo_name, factors_dict, case_name_resolver):
    if sap_model is None or not combo_name: return 0
    items = []
    for cid_str, cf in (factors_dict or {}).items():
        nm = case_name_resolver(str(cid_str)) or str(cid_str)
        try:
            coef = float(cf)
        except Exception:
            continue
        if nm and str(nm).strip() and abs(coef) > 1e-12:
            items.append((str(nm).strip(), float(coef)))
    if not items: return 0
    return add_combo_batch(sap_model, combo_name, items, combo_type=0)