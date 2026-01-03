from fastapi import FastAPI, WebSocket, Request, Form, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.core.manager import DownloadManager
from app.core.spotdl_wrapper import SpotDLWrapper
import os

app = FastAPI()

# Setup paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize Core
# Ensure downloads go to a specific folder
DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

wrapper = SpotDLWrapper(output_dir=DOWNLOAD_DIR)
manager = DownloadManager(wrapper)

@app.on_event("startup")
async def startup_event():
    await manager.start_workers()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/download")
async def add_download(url: str = Form(...)):
    await manager.add_download(url)
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    manager.add_observer(websocket)
    try:
        while True:
            # Keep connection open, maybe listen for client commands (cancel?)
            data = await websocket.receive_text()
    except Exception:
        manager.remove_observer(websocket)
