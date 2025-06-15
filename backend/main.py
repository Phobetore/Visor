import asyncio
from collections import defaultdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from .capture import PacketCapture
from .geo import async_geolocate_ip

app = FastAPI(title="Visor")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def read_index():
    return FileResponse("frontend/index.html")

capture = PacketCapture()
traffic_count = defaultdict(int)
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
            for pkt in new_packets:
                src = pkt.get("src")
                dst = pkt.get("dst")
                slat, slon, _ = await async_geolocate_ip(src)
                dlat, dlon, _ = await async_geolocate_ip(dst)
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
                enriched.append(info)
            if enriched or anomalies:
                await ws.send_json({"packets": enriched, "anomalies": anomalies})
    except WebSocketDisconnect:
        pass
