import asyncio

from .anomaly import AnomalyDetector

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from contextlib import asynccontextmanager

from .host import get_public_ip

from .capture import PacketCapture
from .geo import async_geolocate_ip, is_local_ip
from . import geo

capture = PacketCapture()
detector = AnomalyDetector()


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

                anomalies.extend(detector.process(pkt))

                enriched.append(info)
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
