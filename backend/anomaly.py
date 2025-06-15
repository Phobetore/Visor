class AnomalyRule:
    """Base class for anomaly detection rules."""

    def process(self, packet: dict) -> list[str]:
        """Process a packet and return a list of anomaly descriptions."""
        raise NotImplementedError


class HighTrafficRule(AnomalyRule):
    def __init__(self, threshold: int = 50):
        self.threshold = threshold
        self.count: dict[str, int] = {}
        self.reported: set[str] = set()

    def process(self, packet: dict) -> list[str]:
        src = packet.get("src")
        if not src:
            return []
        self.count[src] = self.count.get(src, 0) + 1
        if self.count[src] > self.threshold and src not in self.reported:
            self.reported.add(src)
            return [f"High traffic from {src}"]
        return []


class DestinationSpikeRule(AnomalyRule):
    def __init__(self, spike_threshold: int = 20):
        self.threshold = spike_threshold
        self.destinations: dict[str, set[str]] = {}
        self.prev_counts: dict[str, int] = {}
        self.reported: set[str] = set()

    def process(self, packet: dict) -> list[str]:
        src = packet.get("src")
        dst = packet.get("dst")
        if not src or not dst:
            return []
        dests = self.destinations.setdefault(src, set())
        changed = dst not in dests
        dests.add(dst)
        if changed:
            current = len(dests)
            prev = self.prev_counts.get(src, 0)
            if current - prev > self.threshold and src not in self.reported:
                self.reported.add(src)
                self.prev_counts[src] = current
                return [f"Spike in unique destinations from {src}"]
            self.prev_counts[src] = current
        return []


class PortScanRule(AnomalyRule):
    def __init__(self, threshold: int = 10):
        self.threshold = threshold
        self.tracker: dict[str, dict[str, set[int]]] = {}
        self.reported: set[tuple[str, str]] = set()

    def process(self, packet: dict) -> list[str]:
        src = packet.get("src")
        dst = packet.get("dst")
        port = packet.get("dst_port") or packet.get("dport")
        if not src or not dst or port is None:
            return []
        dsts = self.tracker.setdefault(src, {})
        ports = dsts.setdefault(dst, set())
        ports.add(port)
        if len(ports) > self.threshold and (src, dst) not in self.reported:
            self.reported.add((src, dst))
            return [f"Port scan from {src} to {dst}"]
        return []


class UnusualProtocolRule(AnomalyRule):
    def __init__(self):
        self.allowed = {"TCP", "UDP", "ICMP", 6, 17, 1}
        self.reported: set[str] = set()

    def process(self, packet: dict) -> list[str]:
        proto = packet.get("proto")
        src = packet.get("src")
        dst = packet.get("dst")
        if proto not in self.allowed and proto not in self.reported:
            self.reported.add(proto)
            return [f"Unusual protocol {proto} from {src} to {dst}"]
        return []


def default_rules() -> list[AnomalyRule]:
    return [
        HighTrafficRule(),
        DestinationSpikeRule(),
        PortScanRule(),
        UnusualProtocolRule(),
    ]


class AnomalyDetector:
    def __init__(self, rules: list[AnomalyRule] | None = None):
        self.rules = rules or default_rules()

    def add_rule(self, rule: AnomalyRule) -> None:
        self.rules.append(rule)

    def process(self, packet: dict) -> list[str]:
        anomalies: list[str] = []
        for rule in self.rules:
            anomalies.extend(rule.process(packet))
        return anomalies
