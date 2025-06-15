import asyncio
import httpx

_cache: dict[str, tuple | None] = {}


async def async_geolocate_ip(ip: str):
    """Return ``(lat, lon, country, country_code)`` for an IP."""
    if ip in _cache:
        return _cache[ip]
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"https://ip-api.com/json/{ip}", timeout=5)
            data = resp.json()
            if data.get("status") == "success":
                result = (
                    data.get("lat"),
                    data.get("lon"),
                    data.get("country"),
                    data.get("countryCode"),
                )
            else:
                result = (None, None, None, None)
    except Exception:
        result = (None, None, None, None)
    _cache[ip] = result
    if len(_cache) > 1024:
        _cache.pop(next(iter(_cache)))
    return result


def geolocate_ip(ip: str):
    """Synchronous wrapper around :func:`async_geolocate_ip`."""
    return asyncio.run(async_geolocate_ip(ip))
