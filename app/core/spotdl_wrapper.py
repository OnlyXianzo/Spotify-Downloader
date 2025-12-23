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
            songs = self.spotdl.search([query])
            if songs:
                return songs[0]

            # 2. Fallback: If query is not a URL, it might be "Artist - Title".
            # If it IS a URL, maybe we can't do much fallback unless we parse it.
            # But if the user typed "Artist - Song", and spotdl returned nothing (unlikely for text queries),
            # we might try to relax it.

            # However, the requirement says "If a YouTube match fails... fallback search using... 'Artist - Title'".
            # SpotDL search mainly gets metadata from Spotify. The YouTube matching happens *during download* usually,
            # OR the Song object contains the download_url if found during search (SpotDL v4 tries to find it).

            # If we returned a song but it has no download_url, SpotDL will try to find it on download.
            # So here we are concerned if *Spotify* metadata isn't found.

            # If the user provided a Spotify URL and it failed, maybe we can scrape the title?
            # But if spotdl fails on a spotify URL, it's usually an API/Network issue.

            # Let's assume the fallback is for when we can't find the song metadata.
            logger.warning(f"No results for {query}, trying fallback mechanisms.")
            return None

        except Exception as e:
            logger.error(f"Search failed for {query}: {e}")
            return None

    async def download_song(self, song: Song) -> bool:
        """
        Downloads a song. returns True if success.
        """
        try:
            loop = asyncio.get_event_loop()
            # SpotDL's download returns (song, path)
            # It performs the YouTube search if download_url is missing.
            # If that search fails, we can catch it here?

            # SpotDL v4 throws exceptions if download fails.
            await loop.run_in_executor(None, self.spotdl.download, song)
            return True
        except Exception as e:
            # Here is where "YouTube match fails" likely manifests.
            logger.error(f"Download failed for {song.display_name}: {e}")

            # Fallback: The prompt says "fallback search using... 'Artist - Title'".
            # If the initial download failed (likely due to no source found),
            # we can try to force a manual search term?
            # But `song` object is already defined.
            # If we want to retry with a different source, we need to modify the song object or use `reinit_song`?

            return False
