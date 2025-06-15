from scapy.all import sniff, Packet, IP
from threading import Thread, Event, Lock

from typing import List


class PacketCapture:
    def __init__(self, iface: str = None, count: int = 0):
        self.iface = iface
        self.count = count
        self.packets: List[Packet] = []
        self._lock = Lock()
        self._stop_event = Event()
        self.thread: Thread | None = None

    def _append_packet(self, packet: Packet):
        with self._lock:
            self.packets.append(packet)

    def _sniff(self):
        """Continuously sniff packets checking for stop events regularly."""
        while not self._stop_event.is_set():
            with self._lock:
                captured = len(self.packets)
            remaining = self.count - captured if self.count else 0
            if self.count and remaining <= 0:
                break
            sniff(
                iface=self.iface,
                prn=self._append_packet,
                count=remaining,
                stop_filter=lambda _: self._stop_event.is_set(),
                timeout=1,
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
        with self._lock:
            return [p.summary() for p in self.packets]

    def get_summary_since(self, index: int) -> List[str]:
        """Return packet summaries starting from a given index."""
        with self._lock:
            return [p.summary() for p in self.packets[index:]]

    def get_connections(self) -> List[dict]:
        """Return a list of dicts with src and dst for IP packets."""
        connections = []
        with self._lock:
            for p in self.packets:
                if IP in p:
                    ip_layer = p[IP]
                    connections.append({"src": ip_layer.src, "dst": ip_layer.dst})
            return connections

    def get_connections_since(self, index: int) -> List[dict]:
        """Return src/dst dictionaries for packets since index."""
        connections = []
        with self._lock:
            for p in self.packets[index:]:
                if IP in p:
                    ip_layer = p[IP]
                    connections.append({"src": ip_layer.src, "dst": ip_layer.dst})
            return connections

    @property
    def size(self) -> int:
        with self._lock:
            return len(self.packets)
