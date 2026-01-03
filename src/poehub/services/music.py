"""Music service for TuneFree API integration and audio playback."""

from __future__ import annotations

import logging
from collections.abc import Callable

import discord
import httpx

log = logging.getLogger("red.poehub.music")


class MusicService:
    """Service for music search, queue management, and playback."""

    BASE_URL = "https://music-dl.sayqz.com/api/"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    def __init__(self):
        self._queues: dict[int, list[dict]] = {}  # guild_id -> song list
        self._last_search: dict[int, list[dict]] = {}  # user_id -> search results
        self._now_playing: dict[int, dict | None] = {}  # guild_id -> current song
        self._volumes: dict[int, float] = {}  # guild_id -> volume (0.0-1.0)
        self._queue_positions: dict[int, int] = {}  # guild_id -> current position in queue

    # --- Search API ---

    async def search(self, keyword: str, limit: int = 10) -> list[dict]:
        """Search for songs across all platforms (netease, qq, kuwo).

        Returns list of song dicts with keys: id, name, artist, album, platform, url
        """
        try:
            async with httpx.AsyncClient(headers=self.HEADERS, timeout=15.0) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "type": "aggregateSearch",
                        "keyword": keyword,
                        "limit": limit,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if data.get("code") == 200:
                    return data.get("data", {}).get("results", [])
                return []
        except Exception as e:
            log.error(f"Search failed: {e}")
            return []

    async def get_song_url(self, source: str, song_id: str, quality: str = "flac") -> str | None:
        """Get the audio URL for a song (follows 302 redirect).

        Returns the direct audio URL or None if failed.
        """
        try:
            async with httpx.AsyncClient(headers=self.HEADERS, timeout=15.0, follow_redirects=False) as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "source": source,
                        "id": song_id,
                        "type": "url",
                        "br": quality,
                    },
                )
                if response.status_code == 302:
                    return response.headers.get("location")
                return None
        except Exception as e:
            log.error(f"Failed to get song URL: {e}")
            return None

    # --- Search Result Cache ---

    def cache_search_results(self, user_id: int, results: list[dict]) -> None:
        """Cache search results for a user."""
        self._last_search[user_id] = results

    def get_cached_result(self, user_id: int, index: int) -> dict | None:
        """Get a cached search result by index (1-based)."""
        results = self._last_search.get(user_id, [])
        if 1 <= index <= len(results):
            return results[index - 1]
        return None

    # --- Queue Management ---

    def add_to_queue(self, guild_id: int, song: dict) -> int:
        """Add a song to the guild's queue. Returns queue position."""
        if guild_id not in self._queues:
            self._queues[guild_id] = []
        self._queues[guild_id].append(song)
        return len(self._queues[guild_id])

    def get_queue(self, guild_id: int) -> list[dict]:
        """Get the current queue for a guild."""
        return self._queues.get(guild_id, [])

    def clear_queue(self, guild_id: int) -> None:
        """Clear the queue for a guild."""
        self._queues[guild_id] = []
        self._now_playing[guild_id] = None
        self._queue_positions[guild_id] = 0

    def get_next(self, guild_id: int) -> dict | None:
        """Get the next song from the queue (loops back to start)."""
        queue = self._queues.get(guild_id, [])
        if not queue:
            return None
        
        pos = self._queue_positions.get(guild_id, 0)
        if pos >= len(queue):
            pos = 0  # Loop back to start
        
        song = queue[pos]
        self._queue_positions[guild_id] = pos + 1
        return song

    def get_queue_position(self, guild_id: int) -> int:
        """Get current position in queue (1-based for display)."""
        return self._queue_positions.get(guild_id, 0)

    def get_now_playing(self, guild_id: int) -> dict | None:
        """Get the currently playing song."""
        return self._now_playing.get(guild_id)

    def set_now_playing(self, guild_id: int, song: dict | None) -> None:
        """Set the currently playing song."""
        self._now_playing[guild_id] = song

    # --- Volume Control ---

    def get_volume(self, guild_id: int) -> float:
        """Get the volume for a guild (0.0-1.0). Default is 0.5 (50%)."""
        return self._volumes.get(guild_id, 0.5)

    def set_volume(self, guild_id: int, volume: int) -> float:
        """Set the volume for a guild (0-100). Returns the normalized volume."""
        normalized = max(0.0, min(1.0, volume / 100.0))
        self._volumes[guild_id] = normalized
        return normalized

    # --- Playback ---

    async def play_song(
        self,
        voice_client: discord.VoiceClient,
        song: dict,
        after_callback: Callable[[Exception | None], None] | None = None,
    ) -> bool:
        """Play a song on the voice client.

        Returns True if playback started successfully.
        """
        guild_id = voice_client.guild.id
        audio_url = await self.get_song_url(song["platform"], song["id"])

        if not audio_url:
            log.warning(f"Could not get audio URL for song: {song.get('name')}")
            return False

        try:
            # Create FFmpeg audio source
            ffmpeg_options = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                "options": "-vn",
            }
            source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_options)

            # Apply volume transformer
            volume = self.get_volume(guild_id)
            source = discord.PCMVolumeTransformer(source, volume=volume)

            # Stop current playback if any
            if voice_client.is_playing():
                voice_client.stop()

            # Play the audio
            voice_client.play(source, after=after_callback)
            self.set_now_playing(guild_id, song)
            return True

        except Exception as e:
            log.error(f"Playback failed: {e}")
            return False

    async def play_next(
        self,
        voice_client: discord.VoiceClient,
        after_callback: Callable[[Exception | None], None] | None = None,
    ) -> dict | None:
        """Play the next song in the queue.

        Returns the song that started playing, or None if queue is empty.
        """
        guild_id = voice_client.guild.id
        song = self.get_next(guild_id)

        if song:
            success = await self.play_song(voice_client, song, after_callback)
            if success:
                return song

        self.set_now_playing(guild_id, None)
        return None

    def skip(self, voice_client: discord.VoiceClient) -> bool:
        """Skip the current song. Returns True if there was something to skip."""
        if voice_client.is_playing() or voice_client.is_paused():
            voice_client.stop()  # This triggers the after callback
            return True
        return False
