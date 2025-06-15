
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from backend import main
from backend import geo

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
    monkeypatch.setattr(main, "capture", dummy)
    monkeypatch.setattr(geo, "geolocate_ip", lambda ip: (0, 0, ""))
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert "packets" in data
            pkt = data["packets"][0]
            assert pkt["src"] == "1.1.1.1"
            assert pkt["type"] == "external"
            websocket.close()
