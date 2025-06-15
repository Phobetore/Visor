
from pathlib import Path
import sys
from collections import defaultdict

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
            assert data["packets"][0]["src"] == "1.1.1.1"
            websocket.close()


def test_get_packets(monkeypatch):
    dummy = DummyCapture()
    monkeypatch.setattr(main, "capture", dummy)
    with TestClient(main.app) as client:
        resp = client.get("/packets")
        assert resp.status_code == 200
        assert resp.json() == dummy.packets


def test_websocket_geolocation_and_anomaly(monkeypatch):
    dummy = DummyCapture()
    monkeypatch.setattr(main, "capture", dummy)
    monkeypatch.setattr(main, "geolocate_ip", lambda ip: (1.0, 2.0, "XX"))
    monkeypatch.setattr(geo, "geolocate_ip", lambda ip: (1.0, 2.0, "XX"))
    monkeypatch.setattr(main, "traffic_count", defaultdict(int, {"1.1.1.1": 50}))
    monkeypatch.setattr(main, "reported_anomalies", set())

    with TestClient(main.app) as client:
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            pkt = data["packets"][0]
            assert pkt["src_lat"] == 1.0
            assert pkt["dst_lat"] == 1.0
            assert "High traffic from 1.1.1.1" in data["anomalies"]
            websocket.close()


def test_packet_capture_stop(monkeypatch):
    from backend import capture as cap_module
    import time

    def dummy_sniff(**kwargs):
        stop_filter = kwargs.get("stop_filter")
        while not stop_filter(None):
            time.sleep(0.01)

    monkeypatch.setattr(cap_module, "sniff", dummy_sniff)

    cap = cap_module.PacketCapture()
    cap.start()
    assert cap.thread is not None and cap.thread.is_alive()
    cap.stop()
    assert cap.thread is None
    assert not cap._stop_event.is_set()
