
import asyncio
from pathlib import Path
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from backend import main

class DummyCapture:
    def __init__(self):
        self.packets = [{
            "src": "1.1.1.1",
            "dst": "2.2.2.2",
            "src_port": 1111,
            "dst_port": 2222,
            "proto": "TCP",
        }]
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
            pkt = data["packets"][0]
            assert pkt["src"] == "1.1.1.1"
            assert pkt["dst"] == "2.2.2.2"
            assert pkt["src_port"] == 1111
            assert pkt["dst_port"] == 2222
            assert pkt["proto"] == "TCP"
            websocket.close()


class PortScanCapture:
    def __init__(self):
        self.packets = [
            {"src": "5.5.5.5", "dst": "6.6.6.6", "dport": p, "sport": 1234, "proto": "TCP"}
            for p in range(20, 32)
        ]
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


def test_port_scan_detection(monkeypatch):
    dummy = PortScanCapture()
    monkeypatch.setattr(main, "capture", dummy)
    monkeypatch.setattr(main, "traffic_count", defaultdict(int))
    monkeypatch.setattr(main, "traffic_destinations", defaultdict(set))
    monkeypatch.setattr(main, "dest_prev_counts", defaultdict(int))
    monkeypatch.setattr(main, "dest_spike_reported", set())
    monkeypatch.setattr(main, "port_scan_tracker", defaultdict(lambda: defaultdict(set)))
    monkeypatch.setattr(main, "reported_port_scans", set())
    monkeypatch.setattr(main, "reported_unusual_protos", set())
    monkeypatch.setattr(main, "reported_anomalies", set())
    monkeypatch.setattr(geo, "geolocate_ip", lambda ip: (0, 0, ""))
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert any("Port scan" in a for a in data.get("anomalies", []))
            websocket.close()
