
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from backend import main

class DummyCapture:
    def __init__(self):
        self.packets = [{"src": "1.1.1.1", "dst": "2.2.2.2"}]
        self.size = len(self.packets)

    def start(self):
        pass

    def stop(self):
        pass

    def get_connections(self):
        return self.packets

    def get_connections_since(self, index):
        if index == 0:
            return self.packets
        return []

def test_websocket_close(monkeypatch):
    dummy = DummyCapture()
    async def dummy_geo(ip):
        return (0, 0, "")

    monkeypatch.setattr(main, "capture", dummy)
    monkeypatch.setattr(main, "async_geolocate_ip", dummy_geo)
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert "packets" in data
            assert data["packets"][0]["src"] == "1.1.1.1"
            assert "type" in data["packets"][0]
            websocket.close()
