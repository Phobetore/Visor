import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from backend.main import app
from unittest.mock import patch

class DummyCapture:
    def __init__(self):
        self.sent = False

    def start(self):
        pass

    def stop(self):
        pass

    def get_summary_since(self, index):
        if not self.sent:
            self.sent = True
            return ["packet"]
        return []

    @property
    def size(self):
        return 1


def test_read_index():
    dummy = DummyCapture()
    with patch("backend.main.capture", dummy):
        with TestClient(app) as client:
            resp = client.get("/")
            assert resp.status_code == 200


def test_websocket_endpoint_sends_data():
    dummy = DummyCapture()
    with patch("backend.main.capture", dummy):
        with TestClient(app) as client:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_json()
                assert data == ["packet"]

