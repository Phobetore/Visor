import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse

from .capture import PacketCapture

app = FastAPI(title="Visor")
app.mount("/static", StaticFiles(directory="frontend"), name="static")


@app.get("/")
def read_index():
    return FileResponse("frontend/index.html")

capture = PacketCapture()


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
            if new_packets:
                await ws.send_json(new_packets)
    except WebSocketDisconnect:
        pass
