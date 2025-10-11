# -*- coding: utf-8 -*-
# ====== Feature toggles ======
SELECTED_ENGINE = "ROBOT"  # Lựa chọn phần mềm mặc định (ROBOT hoặc SAP2000)
ENABLE_LICENSE = True          # True nếu bạn cần kích hoạt qua server
SKIP_VERIFY_COUNT = True
ENGINE_ALREADY_CLEAN = True
LICENSE_SERVER_URL = "https://thanh-phuoc.onrender.com/"

# ====== UI constants ======
import unicodedata

def _norm(s: str) -> str:
    if s is None:
        return ""
    s = unicodedata.normalize("NFKC", s).strip().upper()
    s = s.replace("—", "–").replace("-", "–")
    s = " ".join(s.split())
    return s

ATTR_PERM  = "TẢI TRỌNG THƯỜNG XUYÊN"
ATTR_SHORT = "TẠM THỜI – NGẮN HẠN"
ATTR_LONG  = "TẠM THỜI – DÀI HẠN"
ATTR_OPTIONS = [ATTR_PERM, ATTR_SHORT, ATTR_LONG]

CRANE_VERT_NAME = "CẦU TRỤC – ĐỨNG"
CRANE_HORZ_NAME = "CẦU TRỤC – NGANG"
CRANE_VERT_NORM = _norm(CRANE_VERT_NAME)
CRANE_HORZ_NORM = _norm(CRANE_HORZ_NAME)

def is_crane_group(name: str) -> bool:
    nm = _norm(name)
    return nm in (CRANE_VERT_NORM, CRANE_HORZ_NORM)

def same_crane_vert(name: str) -> bool:
    return _norm(name) == CRANE_VERT_NORM

def same_crane_horz(name: str) -> bool:
    return _norm(name) == CRANE_HORZ_NORM

def nature_text(val):
    try: v = int(val)
    except: return str(val)
    return {0:"DEAD",1:"LIVE",2:"WIND",3:"SNOW",4:"SEISMIC",5:"SEISMIC"}.get(v, str(v))

def analysis_text(val):
    try: v = int(val)
    except: return str(val)
    return {0:"UNSPEC",1:"STATIC",2:"MODAL",3:"HARMONIC",4:"RESP-SPEC",5:"TIME-HIST",6:"BUCKLING",7:"NL-STATIC",8:"NL-DYNAMIC"}.get(v, str(v))
