import pytest
import asyncio
from unittest.mock import MagicMock, patch
from app.core.spotdl_wrapper import SpotDLWrapper
from spotdl.types.song import Song

@pytest.mark.asyncio
async def test_search_song_found():
    # Mock spotdl.search
    with patch("spotdl.Spotdl.search") as mock_search:
        mock_song = MagicMock(spec=Song)
        mock_song.name = "Test Song"
        mock_search.return_value = [mock_song]

        wrapper = SpotDLWrapper()
        # We need to mock the internal spotdl instance because __init__ creates it real
        # But actually SpotDLWrapper creates self.spotdl.
        # So we should patch where SpotDLWrapper uses it.

        # Simpler: Mock Spotdl class in the module
        with patch("app.core.spotdl_wrapper.Spotdl") as MockSpotdl:
            instance = MockSpotdl.return_value
            instance.search.return_value = [mock_song]

            wrapper = SpotDLWrapper()
            result = await wrapper.search_song("some query")

            assert result == mock_song
            instance.search.assert_called_with(["some query"])

@pytest.mark.asyncio
async def test_search_song_not_found():
    with patch("app.core.spotdl_wrapper.Spotdl") as MockSpotdl:
        instance = MockSpotdl.return_value
        instance.search.return_value = [] # No results

        wrapper = SpotDLWrapper()
        result = await wrapper.search_song("impossible query")

        assert result is None
