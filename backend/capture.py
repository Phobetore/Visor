from scapy.all import sniff, Packet, IP
from threading import Thread, Event

from typing import List


class PacketCapture:
    def __init__(self, iface: str = None, count: int = 0):
        self.iface = iface
        self.count = count
        self.packets: List[Packet] = []
        self._stop_event = Event()
        self.thread: Thread | None = None

    def _sniff(self):
        sniff(
            iface=self.iface,
            prn=self.packets.append,
            count=self.count,
            stop_filter=lambda _: self._stop_event.is_set(),
            store=False,
        )

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = Thread(target=self._sniff, daemon=True)
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        if self.thread:
            self.thread.join()
        self.thread = None
        self._stop_event.clear()

    def get_summary(self) -> List[str]:
        return [p.summary() for p in self.packets]

    def get_summary_since(self, index: int) -> List[str]:
        """Return packet summaries starting from a given index."""
        return [p.summary() for p in self.packets[index:]]

    def get_connections(self) -> List[dict]:
        """Return a list of dicts with src and dst for IP packets."""
        connections = []
        for p in self.packets:
            if IP in p:
                ip_layer = p[IP]
                connections.append({"src": ip_layer.src, "dst": ip_layer.dst})
        return connections

    def get_connections_since(self, index: int) -> List[dict]:
        """Return src/dst dictionaries for packets since index."""
        connections = []
        for p in self.packets[index:]:
            if IP in p:
                ip_layer = p[IP]
                connections.append({"src": ip_layer.src, "dst": ip_layer.dst})
        return connections

    @property
    def size(self) -> int:
        return len(self.packets)
