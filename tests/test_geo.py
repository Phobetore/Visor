from pathlib import Path
import sys
import pytest
import httpx
import asyncio
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.geo import async_geolocate_ip


def test_async_geolocate_ip_known_address():
    try:
        lat, lon, country, cc = asyncio.run(async_geolocate_ip("8.8.8.8"))
    except httpx.HTTPError:
        pytest.skip("Network not accessible")
    if lat is None or lon is None:
        pytest.skip("Geolocation service unavailable")
    assert -90 <= lat <= 90
    assert -180 <= lon <= 180
