import pytest
import asyncio
from backend.geo import async_geolocate_ip

def test_async_geolocate_ip_live():
    try:
        lat, lon, *_ = asyncio.run(async_geolocate_ip("8.8.8.8"))
    except Exception:
        pytest.skip("Network unreachable")
    if lat is None or lon is None:
        pytest.skip("API did not return location")
    assert isinstance(lat, float)
    assert isinstance(lon, float)
