from scapy.all import sniff, Packet, IP, TCP, UDP
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

    def _packet_info(self, packet: Packet) -> dict | None:
        """Extract connection info from a packet."""
        if IP not in packet:
            return None
        ip_layer = packet[IP]
        proto = None
        src_port = None
        dst_port = None
        if TCP in packet:
            tcp = packet[TCP]
            src_port = tcp.sport
            dst_port = tcp.dport
            proto = "TCP"
        elif UDP in packet:
            udp = packet[UDP]
            src_port = udp.sport
            dst_port = udp.dport
            proto = "UDP"
        else:
            proto = packet.lastlayer().name
        return {
            "src": ip_layer.src,
            "dst": ip_layer.dst,
            "src_port": src_port,
            "dst_port": dst_port,
            "proto": proto,
        }

    def _format_summary(self, packet: Packet) -> str:
        info = self._packet_info(packet)
        if not info:
            return packet.summary()
        proto = info["proto"]
        src = info["src"]
        dst = info["dst"]
        if info["src_port"] is not None and info["dst_port"] is not None:
            return f"{proto} {src}:{info['src_port']} -> {dst}:{info['dst_port']}"
        return f"{proto} {src} -> {dst}"

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
            return [self._format_summary(p) for p in self.packets]

    def get_summary_since(self, index: int) -> List[str]:
        """Return packet summaries starting from a given index."""
        with self._lock:
            return [self._format_summary(p) for p in self.packets[index:]]

    def get_connections(self) -> List[dict]:
        """Return a list of connection dicts for IP packets."""
        connections = []
        with self._lock:
            for p in self.packets:
                info = self._packet_info(p)
                if info:
                    connections.append(info)
            return connections

    def get_connections_since(self, index: int) -> List[dict]:
        """Return connection dictionaries for packets since index."""
        connections = []
        with self._lock:
            for p in self.packets[index:]:
                info = self._packet_info(p)
                if info:
                    connections.append(info)
            return connections

    @property
    def size(self) -> int:
        with self._lock:
            return len(self.packets)
