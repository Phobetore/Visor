
from pathlib import Path
import sys
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from backend import main
from backend import geo

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
        return (0, 0, "", "")

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
    monkeypatch.setattr(geo, "async_geolocate_ip", lambda ip: (0, 0, "", ""))
    with TestClient(main.app) as client:
        with client.websocket_connect("/ws") as websocket:
            data = websocket.receive_json()
            assert any("Port scan" in a for a in data.get("anomalies", []))
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
    async def dummy_geo_loc(ip):
        return (1.0, 2.0, "XX", "XX")
    monkeypatch.setattr(main, "async_geolocate_ip", dummy_geo_loc)
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
