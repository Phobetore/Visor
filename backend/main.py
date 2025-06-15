import asyncio
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from ipaddress import ip_address
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from .capture import PacketCapture
from .geo import async_geolocate_ip
from . import geo

app = FastAPI(title="Visor")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def read_index():
    return FileResponse("frontend/index.html")

capture = PacketCapture()
traffic_count = defaultdict(int)
traffic_destinations = defaultdict(set)
dest_prev_counts = defaultdict(int)
dest_spike_reported = set()
port_scan_tracker = defaultdict(lambda: defaultdict(set))
reported_port_scans = set()
reported_unusual_protos = set()
reported_anomalies = set()


def is_local_ip(ip: str) -> bool:
    """Return True if the IP address is private or loopback."""
    try:
        ip_obj = ip_address(ip)
        return ip_obj.is_private or ip_obj.is_loopback
    except ValueError:
        return False


@app.on_event("startup")
def startup_event():
    capture.start()


@app.on_event("shutdown")
def shutdown_event():
    capture.stop()


@app.get("/packets")
def get_packets():
    """Return all captured connections with port and protocol info."""
    return JSONResponse(capture.get_connections())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    last = 0
    try:
        while True:
            await asyncio.sleep(1)
            new_packets = capture.get_connections_since(last)
            last = capture.size
            enriched = []
            anomalies = []
            dest_changed = set()
            for pkt in new_packets:
                src = pkt.get("src")
                dst = pkt.get("dst")
                src_port = pkt.get("src_port") or pkt.get("sport")
                dst_port = pkt.get("dst_port") or pkt.get("dport")
                proto = pkt.get("proto")
                slat, slon, _ = await async_geolocate_ip(src)
                dlat, dlon, _ = await async_geolocate_ip(dst)

                if is_local_ip(src) and is_local_ip(dst):
                    conn_type = "local-local"
                elif is_local_ip(src) and not is_local_ip(dst):
                    conn_type = "local-public"
                elif not is_local_ip(src) and is_local_ip(dst):
                    conn_type = "public-local"
                else:
                    conn_type = "public-public"

                info = {
                    "src": src,
                    "dst": dst,
                    "src_port": src_port,
                    "dst_port": dst_port,
                    "proto": proto,
                    "src_lat": slat,
                    "src_lon": slon,
                    "dst_lat": dlat,
                    "dst_lon": dlon,
                    "type": conn_type,
                }
                traffic_count[src] += 1
                if traffic_count[src] > 50 and src not in reported_anomalies:
                    anomalies.append(f"High traffic from {src}")
                    reported_anomalies.add(src)

                if dst not in traffic_destinations[src]:
                    dest_changed.add(src)
                traffic_destinations[src].add(dst)

                if dst_port is not None:
                    port_scan_tracker[src][dst].add(dst_port)
                    if len(port_scan_tracker[src][dst]) > 10 and (src, dst) not in reported_port_scans:
                        anomalies.append(f"Port scan from {src} to {dst}")
                        reported_port_scans.add((src, dst))

                if proto not in {"TCP", "UDP", "ICMP", 6, 17, 1} and proto not in reported_unusual_protos:
                    anomalies.append(f"Unusual protocol {proto} from {src} to {dst}")
                    reported_unusual_protos.add(proto)

                enriched.append(info)

            for src in dest_changed:
                prev = dest_prev_counts[src]
                current = len(traffic_destinations[src])
                if current - prev > 20 and src not in dest_spike_reported:
                    anomalies.append(f"Spike in unique destinations from {src}")
                    dest_spike_reported.add(src)
                dest_prev_counts[src] = current
            if enriched or anomalies:
                await ws.send_json({"packets": enriched, "anomalies": anomalies})
    except WebSocketDisconnect:
        pass
