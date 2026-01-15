import asyncio
import logging
import uuid
from typing import Dict
from dataclasses import dataclass
from .spotdl_wrapper import SpotDLWrapper

logger = logging.getLogger(__name__)

@dataclass
class DownloadTask:
    id: str
    query: str
    status: str = "queued" # queued, downloading, finished, failed
    progress: int = 0
    message: str = ""
    song_name: str = "Unknown"
    artist: str = "Unknown"
    cover_url: str = ""
    retries: int = 0

class DownloadManager:
    def __init__(self, wrapper: SpotDLWrapper, max_concurrent=3, max_retries=3):
        self.wrapper = wrapper
        self.queue = asyncio.Queue()
        self.tasks: Dict[str, DownloadTask] = {}
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.max_retries = max_retries
        self.observers = []

    async def add_download(self, query: str) -> str:
        task_id = str(uuid.uuid4())
        task = DownloadTask(id=task_id, query=query)
        self.tasks[task_id] = task
        await self.queue.put(task_id)
        await self.notify_observers()
        return task_id

    async def start_workers(self):
        asyncio.create_task(self.worker_loop())

    async def worker_loop(self):
        logger.info("Worker loop started")
        while True:
            task_id = await self.queue.get()
            asyncio.create_task(self.process_task(task_id))

    async def process_task(self, task_id: str):
        async with self.semaphore:
            task = self.tasks[task_id]
            task.status = "processing_metadata"
            await self.notify_observers()

            try:
                # 1. Search/Fetch Metadata
                song = await self.wrapper.search_song(task.query)
                if not song:
                    task.status = "failed"
                    task.message = "Song not found"
                    await self.notify_observers()
                    return

                task.song_name = song.name
                task.artist = song.artist
                task.cover_url = song.cover_url
                task.status = "downloading"
                await self.notify_observers()

                # 2. Download with Retry Logic
                success = False
                while task.retries < self.max_retries:
                    success = await self.wrapper.download_song(song)
                    if success:
                        break

                    task.retries += 1
                    logger.warning(f"Task {task_id} failed. Retrying ({task.retries}/{self.max_retries})...")
                    task.message = f"Retrying ({task.retries})..."
                    await self.notify_observers()
                    await asyncio.sleep(2) # Backoff

                if success:
                    task.status = "finished"
                    task.progress = 100
                    task.message = ""
                else:
                    task.status = "failed"
                    task.message = "Download failed after retries"

            except Exception as e:
                task.status = "failed"
                task.message = str(e)
                logger.exception(f"Task {task_id} failed exception")

            await self.notify_observers()

    def add_observer(self, websocket):
        self.observers.append(websocket)

    def remove_observer(self, websocket):
        if websocket in self.observers:
            self.observers.remove(websocket)

    async def notify_observers(self):
        state = [
            {
                "id": t.id,
                "query": t.query,
                "status": t.status,
                "progress": t.progress,
                "name": t.song_name,
                "artist": t.artist,
                "cover": t.cover_url,
                "message": t.message,
                "retries": t.retries
            }
            for t in self.tasks.values()
        ]

        to_remove = []
        for ws in self.observers:
            try:
                await ws.send_json(state)
            except Exception:
                to_remove.append(ws)

        for ws in to_remove:
            self.remove_observer(ws)
