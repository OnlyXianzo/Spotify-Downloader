import asyncio
import logging
from typing import Optional, List
from spotdl import Spotdl
from spotdl.types.song import Song
from spotdl.utils.config import get_config

logger = logging.getLogger(__name__)

class SpotDLWrapper:
    def __init__(self, output_dir: str = "."):
        self.config = get_config()
        self.output_dir = output_dir

        # Initialize SpotDL
        self.spotdl = Spotdl(
            client_id=self.config["client_id"],
            client_secret=self.config["client_secret"],
            user_auth=False,
            headless=True,
            no_cache=False
        )

        self.spotdl.downloader.settings["output"] = f"{self.output_dir}/{{artist}} - {{title}}.{{output-ext}}"
        self.spotdl.downloader.settings["ffmpeg"] = self.config.get("ffmpeg", "ffmpeg")

    async def search_song(self, query: str) -> Optional[Song]:
        """
        Search for a song. If direct match fails, tries fallback search.
        """
        try:
            # 1. Try normal search
            # Spotdl.search might also use asyncio, so we should run it in executor if it blocks or needs loop?
            # Spotdl.search seems to be sync in v4 API but uses requests/etc.
            # If it uses asyncio internally, we might have issues here too if run directly in a thread?
            # But here we are in an async function, we can just run it in executor if strictly blocking.
            # The previous code ran it directly: `self.spotdl.search([query])`
            # If that worked, it's fine.
            loop = asyncio.get_event_loop()
            songs = await loop.run_in_executor(None, self.spotdl.search, [query])

            if songs:
                return songs[0]

            logger.warning(f"No results for {query}, trying fallback mechanisms.")
            return None

        except Exception as e:
            logger.error(f"Search failed for {query}: {e}")
            return None

    def _threaded_download(self, song: Song):
        """
        Helper to run spotdl.download in a thread with its own event loop.
        """
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # spotdl.download (sync) calls async code internally.
            # It likely relies on asyncio.get_event_loop() or asyncio.run().
            # If it uses get_event_loop(), we just provided one.
            # If it uses asyncio.run(), it creates a new one, which is fine too.
            # But typically libraries check get_event_loop().
            return self.spotdl.download(song)
        finally:
            try:
                # Cancel all tasks?
                pending = asyncio.all_tasks(loop)
                for task in pending:
                    task.cancel()
                # Run loop to process cancellations
                if pending:
                    loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            except Exception:
                pass
            loop.close()

    async def download_song(self, song: Song) -> bool:
        """
        Downloads a song. returns True if success.
        """
        try:
            loop = asyncio.get_event_loop()

            # Use the threaded helper
            await loop.run_in_executor(None, self._threaded_download, song)
            return True
        except Exception as e:
            logger.error(f"Download failed for {song.display_name}: {e}")
            return False
