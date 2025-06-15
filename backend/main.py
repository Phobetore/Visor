import asyncio
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from .capture import PacketCapture
from .geo import geolocate_ip

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


@app.on_event("startup")
def startup_event():
    capture.start()


@app.on_event("shutdown")
def shutdown_event():
    capture.stop()


@app.get("/packets")
def get_packets():
    """Return all captured connections as src/dst dicts."""
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
                sport = pkt.get("sport")
                dport = pkt.get("dport")
                proto = pkt.get("proto")

                slat, slon, _ = geolocate_ip(src)
                dlat, dlon, _ = geolocate_ip(dst)
                info = {
                    "src": src,
                    "dst": dst,
                    "src_lat": slat,
                    "src_lon": slon,
                    "dst_lat": dlat,
                    "dst_lon": dlon,
                }
                traffic_count[src] += 1
                if traffic_count[src] > 50 and src not in reported_anomalies:
                    anomalies.append(f"High traffic from {src}")
                    reported_anomalies.add(src)

                if dst not in traffic_destinations[src]:
                    dest_changed.add(src)
                traffic_destinations[src].add(dst)

                if dport is not None:
                    port_scan_tracker[src][dst].add(dport)
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
