"""Unit tests for MusicService."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from poehub.services.music import MusicService


@pytest.fixture
def music_service():
    return MusicService()


# --- Search Tests ---

@pytest.mark.asyncio
async def test_search_success(music_service):
    """Test successful search."""
    mock_response = {
        "code": 200,
        "data": {
            "results": [
                {"id": "123", "name": "Hello", "artist": "Adele", "platform": "netease"},
                {"id": "456", "name": "Hello", "artist": "OMFG", "platform": "kuwo"},
            ]
        }
    }

    with patch("poehub.services.music.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__.return_value = mock_client

        response = MagicMock()
        response.json.return_value = mock_response
        response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=response)

        results = await music_service.search("hello", limit=10)

        assert len(results) == 2
        assert results[0]["name"] == "Hello"
        assert results[0]["artist"] == "Adele"


@pytest.mark.asyncio
async def test_search_no_results(music_service):
    """Test search with no results."""
    mock_response = {"code": 200, "data": {"results": []}}

    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = client_instance

        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = mock_response
        response.raise_for_status = MagicMock()
        client_instance.get.return_value = response

        results = await music_service.search("nonexistent")

        assert results == []


@pytest.mark.asyncio
async def test_search_error(music_service):
    """Test search with network error."""
    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.side_effect = Exception("Network error")

        results = await music_service.search("hello")

        assert results == []


# --- Get Song URL Tests ---

@pytest.mark.asyncio
async def test_get_song_url_success(music_service):
    """Test successfully getting song URL."""
    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = client_instance

        response = AsyncMock()
        response.status_code = 302
        response.headers = {"location": "http://example.com/song.mp3"}
        client_instance.get.return_value = response

        url = await music_service.get_song_url("netease", "123", "320k")

        assert url == "http://example.com/song.mp3"


@pytest.mark.asyncio
async def test_get_song_url_not_found(music_service):
    """Test get song URL when not found."""
    with patch("httpx.AsyncClient") as MockClient:
        client_instance = AsyncMock()
        MockClient.return_value.__aenter__.return_value = client_instance

        response = AsyncMock()
        response.status_code = 404
        response.headers = {}
        client_instance.get.return_value = response

        url = await music_service.get_song_url("netease", "999")

        assert url is None


# --- Cache Tests ---

def test_cache_search_results(music_service):
    """Test caching search results."""
    results = [{"id": "1", "name": "Song1"}, {"id": "2", "name": "Song2"}]

    music_service.cache_search_results(12345, results)

    assert music_service.get_cached_result(12345, 1) == results[0]
    assert music_service.get_cached_result(12345, 2) == results[1]
    assert music_service.get_cached_result(12345, 3) is None
    assert music_service.get_cached_result(12345, 0) is None


def test_get_cached_result_no_cache(music_service):
    """Test getting cached result when no cache exists."""
    assert music_service.get_cached_result(99999, 1) is None


# --- Queue Tests ---

def test_add_to_queue(music_service):
    """Test adding songs to queue."""
    song1 = {"id": "1", "name": "Song1"}
    song2 = {"id": "2", "name": "Song2"}

    pos1 = music_service.add_to_queue(100, song1)
    pos2 = music_service.add_to_queue(100, song2)

    assert pos1 == 1
    assert pos2 == 2
    assert music_service.get_queue(100) == [song1, song2]


def test_get_queue_empty(music_service):
    """Test getting empty queue."""
    assert music_service.get_queue(999) == []


def test_clear_queue(music_service):
    """Test clearing queue."""
    music_service.add_to_queue(100, {"id": "1"})
    music_service.set_now_playing(100, {"id": "1"})

    music_service.clear_queue(100)

    assert music_service.get_queue(100) == []
    assert music_service.get_now_playing(100) is None


def test_get_next(music_service):
    """Test getting next song from queue (loops)."""
    song1 = {"id": "1"}
    song2 = {"id": "2"}
    music_service.add_to_queue(100, song1)
    music_service.add_to_queue(100, song2)

    # First call gets song1
    next1 = music_service.get_next(100)
    assert next1 == song1
    # Queue is unchanged
    assert music_service.get_queue(100) == [song1, song2]

    # Second call gets song2
    next2 = music_service.get_next(100)
    assert next2 == song2

    # Third call loops back to song1
    next3 = music_service.get_next(100)
    assert next3 == song1


def test_get_next_empty(music_service):
    """Test getting next from empty queue."""
    assert music_service.get_next(999) is None


# --- Now Playing Tests ---

def test_now_playing(music_service):
    """Test now playing tracking."""
    song = {"id": "1", "name": "Test"}

    music_service.set_now_playing(100, song)
    assert music_service.get_now_playing(100) == song

    music_service.set_now_playing(100, None)
    assert music_service.get_now_playing(100) is None


# --- Skip Tests ---

def test_skip_when_playing(music_service):
    """Test skip when music is playing."""
    voice_client = MagicMock()
    voice_client.is_playing.return_value = True
    voice_client.is_paused.return_value = False

    result = music_service.skip(voice_client)

    assert result is True
    voice_client.stop.assert_called_once()


def test_skip_when_paused(music_service):
    """Test skip when music is paused."""
    voice_client = MagicMock()
    voice_client.is_playing.return_value = False
    voice_client.is_paused.return_value = True

    result = music_service.skip(voice_client)

    assert result is True
    voice_client.stop.assert_called_once()


def test_skip_when_not_playing(music_service):
    """Test skip when nothing is playing."""
    voice_client = MagicMock()
    voice_client.is_playing.return_value = False
    voice_client.is_paused.return_value = False

    result = music_service.skip(voice_client)

    assert result is False
    voice_client.stop.assert_not_called()
