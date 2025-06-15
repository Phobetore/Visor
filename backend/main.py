import asyncio
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager

from .host import get_public_ip

from .capture import PacketCapture
from .geo import async_geolocate_ip, is_local_ip
from . import geo

capture = PacketCapture()


server_geolocation: tuple[float | None, float | None, str | None, str | None] = (
    None,
    None,
    None,
    None,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    capture.start()
    global server_geolocation
    try:
        ip = await get_public_ip()
        if ip:
            server_geolocation = await async_geolocate_ip(ip)
    except Exception:
        pass
    try:
        yield
    finally:
        capture.stop()


app = FastAPI(title="Visor", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def read_index():
    return FileResponse("frontend/index.html")

traffic_count = defaultdict(int)
traffic_destinations = defaultdict(set)
dest_prev_counts = defaultdict(int)
dest_spike_reported = set()
port_scan_tracker = defaultdict(lambda: defaultdict(set))
reported_port_scans = set()
reported_unusual_protos = set()
reported_anomalies = set()


@app.get("/packets")
def get_packets():
    """Return all captured connections with port and protocol info."""
    return JSONResponse(capture.get_connections())


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    last = 0
    first_message = True
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
                slat, slon, scountry, scc = await async_geolocate_ip(src)
                dlat, dlon, dcountry, dcc = await async_geolocate_ip(dst)
                if is_local_ip(src) and server_geolocation[0] is not None:
                    slat, slon = server_geolocation[0], server_geolocation[1]
                if is_local_ip(dst) and server_geolocation[0] is not None:
                    dlat, dlon = server_geolocation[0], server_geolocation[1]

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
                    "src_country": scountry,
                    "src_country_code": scc,
                    "dst_lat": dlat,
                    "dst_lon": dlon,
                    "dst_country": dcountry,
                    "dst_country_code": dcc,
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
            if enriched or anomalies or first_message:
                message = {"packets": enriched, "anomalies": anomalies}
                if first_message:
                    message["server_location"] = {
                        "lat": server_geolocation[0],
                        "lon": server_geolocation[1],
                    }
                    first_message = False
                await ws.send_json(message)
    except WebSocketDisconnect:
        pass
