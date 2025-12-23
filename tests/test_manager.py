import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from app.core.manager import DownloadManager, DownloadTask
from app.core.spotdl_wrapper import SpotDLWrapper
from spotdl.types.song import Song

@pytest.mark.asyncio
async def test_download_retry_logic():
    # Mock wrapper
    mock_wrapper = MagicMock(spec=SpotDLWrapper)

    # Mock search to return a song
    mock_song = MagicMock(spec=Song)
    mock_song.name = "Retry Song"
    mock_song.artist = "Retry Artist"
    mock_song.cover_url = ""
    mock_wrapper.search_song = AsyncMock(return_value=mock_song)

    # Mock download to fail twice then succeed
    mock_wrapper.download_song = AsyncMock(side_effect=[False, False, True])

    manager = DownloadManager(mock_wrapper, max_retries=3)

    # Add task
    task_id = await manager.add_download("test_retry")

    # Wait time must be small/zero for test
    # We can patch asyncio.sleep to be instant
    with patch('asyncio.sleep', new_callable=AsyncMock):
        await manager.process_task(task_id)

    task = manager.tasks[task_id]

    assert task.status == "finished"
    assert task.retries == 2
    assert mock_wrapper.download_song.call_count == 3

@pytest.mark.asyncio
async def test_download_fail_max_retries():
    mock_wrapper = MagicMock(spec=SpotDLWrapper)

    # Fix: mock song attributes properly
    mock_song = MagicMock(spec=Song)
    mock_song.name = "Fail Song"
    mock_song.artist = "Fail Artist"
    mock_song.cover_url = ""
    mock_wrapper.search_song = AsyncMock(return_value=mock_song)

    # Always fail
    mock_wrapper.download_song = AsyncMock(return_value=False)

    manager = DownloadManager(mock_wrapper, max_retries=3)
    task_id = await manager.add_download("test_fail")

    with patch('asyncio.sleep', new_callable=AsyncMock):
        await manager.process_task(task_id)

    task = manager.tasks[task_id]
    assert task.status == "failed"
    assert task.retries == 3
    assert mock_wrapper.download_song.call_count == 3
