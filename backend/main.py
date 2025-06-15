import asyncio
import ipaddress
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
reported_anomalies = set()


def is_private_ip(ip: str) -> bool:
    """Return True if the IP address is in a private range."""
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def classify_traffic(src: str, dst: str) -> str:
    """Classify traffic type based on IP ranges."""
    src_priv = is_private_ip(src)
    dst_priv = is_private_ip(dst)
    if src_priv and dst_priv:
        return "local"
    if src_priv and not dst_priv:
        return "outgoing"
    if not src_priv and dst_priv:
        return "incoming"
    return "external"


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
            for pkt in new_packets:
                src = pkt.get("src")
                dst = pkt.get("dst")
                traffic_count[src] += 1
                traffic_destinations[src].add(dst)
                slat, slon, _ = geolocate_ip(src)
                dlat, dlon, _ = geolocate_ip(dst)
                ttype = classify_traffic(src, dst)
                info = {
                    "src": src,
                    "dst": dst,
                    "src_lat": slat,
                    "src_lon": slon,
                    "dst_lat": dlat,
                    "dst_lon": dlon,
                    "type": ttype,
                }
                if traffic_count[src] > 50 and src not in reported_anomalies:
                    anomalies.append(f"High traffic from {src}")
                    reported_anomalies.add(src)
                if len(traffic_destinations[src]) > 20 and src not in reported_anomalies:
                    anomalies.append(f"Possible scanning from {src}")
                    reported_anomalies.add(src)
                enriched.append(info)
            if enriched or anomalies:
                await ws.send_json({"packets": enriched, "anomalies": anomalies})
    except WebSocketDisconnect:
        pass
