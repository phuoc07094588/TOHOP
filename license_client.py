# -*- coding: utf-8 -*-
"""
license_client.py
Client cho License Server (FastAPI) của bạn.
- /activate: POST { key, device_fingerprint } -> { access_token, plan, expires }
- /status:   GET  ?token=... -> { ok, plan, key, device }
Tài liệu server: xem server.py trong repo bạn.
"""
from __future__ import annotations
import os, json, time, platform, uuid, hashlib, sys
from typing import Optional, Tuple, Dict

# ---- HTTP helpers: ưu tiên requests, rớt về urllib nếu không có ----
try:
    import requests  # type: ignore
    _HAS_REQUESTS = True
except Exception:
    _HAS_REQUESTS = False
    import urllib.request, urllib.error  # type: ignore

def _http_post_json(url: str, payload: dict, timeout: int = 10) -> Tuple[int, str]:
    if _HAS_REQUESTS:
        r = requests.post(url, json=payload, timeout=timeout)
        return r.status_code, r.text
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)

def _http_get(url: str, timeout: int = 10) -> Tuple[int, str]:
    if _HAS_REQUESTS:
        r = requests.get(url, timeout=timeout)
        return r.status_code, r.text
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return 0, str(e)

# ---- Fingerprint máy ----
def _win_machine_guid() -> str:
    if platform.system().upper().startswith("WIN"):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
                val, _ = winreg.QueryValueEx(key, "MachineGuid")
                return str(val).strip()
        except Exception:
            return ""
    return ""

def machine_fingerprint() -> str:
    """
    Tạo mã vân tay thiết bị ổn định: hash của (MachineGuid/MAC/hostname/os/version)
    Độ dài >= 16 ký tự để khớp yêu cầu server.
    """
    parts = [
        _win_machine_guid(),
        hex(uuid.getnode())[2:],
        platform.node(),
        platform.system(),
        platform.version(),
        platform.machine(),
    ]
    raw = "|".join(p for p in parts if p)
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()
    return h  # 64 hex chars

# ---- Token storage ----
def _default_store_path() -> str:
    # ~/.tp_license.json
    home = os.path.expanduser("~")
    return os.path.join(home, ".tp_license.json")

def load_token(store_path: Optional[str] = None) -> Optional[Dict]:
    p = store_path or _default_store_path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def save_token(data: Dict, store_path: Optional[str] = None) -> None:
    p = store_path or _default_store_path()
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

# ---- API wrappers ----
def normalize_base(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    if u.endswith("/"):
        u = u[:-1]
    return u

class LicenseError(Exception):
    pass

def activate(base_url: str, license_key: str, device_fp: Optional[str] = None, timeout: int = 15) -> Dict:
    """
    Gọi POST {base_url}/activate -> trả dict JSON nếu thành công.
    Raise LicenseError nếu lỗi.
    """
    base = normalize_base(base_url)
    if not base:
        raise LicenseError("Thiếu địa chỉ máy chủ (Server URL).")
    if not license_key or len(license_key.strip()) < 8:
        raise LicenseError("License key không hợp lệ.")
    fp = device_fp or machine_fingerprint()
    payload = {"key": license_key.strip(), "device_fingerprint": fp}
    code, text = _http_post_json(base + "/activate", payload, timeout=timeout)
    try:
        data = json.loads(text)
    except Exception:
        data = {"detail": text}
    if code != 200:
        msg = data.get("detail") or data.get("message") or f"Lỗi kích hoạt (HTTP {code})"
        raise LicenseError(str(msg))
    # data: { access_token, plan, expires }
    out = {
        "server_url": base,
        "token": data["access_token"],
        "plan": data.get("plan"),
        "expires": data.get("expires"),
        "device": fp,
        "ts": int(time.time()),
    }
    return out

def status(base_url: str, token: str, timeout: int = 10) -> Dict:
    base = normalize_base(base_url)
    if not base:
        raise LicenseError("Thiếu địa chỉ máy chủ (Server URL).")
    code, text = _http_get(f"{base}/status?token={token}", timeout=timeout)
    try:
        data = json.loads(text)
    except Exception:
        data = {"detail": text}
    if code != 200:
        msg = data.get("detail") or data.get("message") or f"Lỗi kiểm tra trạng thái (HTTP {code})"
        raise LicenseError(str(msg))
    return data