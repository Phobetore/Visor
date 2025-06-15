import requests
from functools import lru_cache


@lru_cache(maxsize=1024)
def geolocate_ip(ip: str):
    """Return (lat, lon, country) for an IP using ip-api.com."""
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=5)
        data = resp.json()
        if data.get("status") == "success":
            return data.get("lat"), data.get("lon"), data.get("country")
    except Exception:
        pass
    return None, None, None
