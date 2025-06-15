from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.capture import PacketCapture


def test_max_packets_drops_old():
    cap = PacketCapture(max_packets=2)
    cap._append_packet("one")
    cap._append_packet("two")
    cap._append_packet("three")
    with cap._lock:
        pkts = list(cap.packets)
    assert pkts == ["two", "three"]
    assert cap.size == 2
