from scapy.all import sniff, Packet
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

    @property
    def size(self) -> int:
        return len(self.packets)
