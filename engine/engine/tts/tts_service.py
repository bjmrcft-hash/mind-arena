"""
TTS service — wraps edge-tts for Chinese speech synthesis.

Agent voice assignments:
- A: zh-CN-YunxiNeural (steady male)
- B: zh-CN-YunyangNeural (powerful male)
- C: zh-CN-XiaoxiaoNeural (intellectual female)
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Voice mapping per agent
VOICE_MAP = {
    "A": "zh-CN-YunxiNeural",
    "B": "zh-CN-YunyangNeural",
    "C": "zh-CN-XiaoxiaoNeural",
}


class TTSService:
    """
    Async TTS wrapper using edge-tts.

    Usage:
        svc = TTSService(audio_dir="./audio")
        path = await svc.synthesize("你好世界", role="A")
    """

    def __init__(self, audio_dir: str | Path = "./audio", enabled: bool = True) -> None:
        self.audio_dir = Path(audio_dir)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.enabled = enabled
        self._edge_tts = None

    def _get_edge_tts(self):
        """Lazy import edge_tts."""
        if self._edge_tts is None:
            import edge_tts
            self._edge_tts = edge_tts
        return self._edge_tts

    async def synthesize(self, text: str, role: str) -> str | None:
        """
        Synthesize text to audio file.

        Args:
            text: Text to speak.
            role: Agent role ("A", "B", or "C").

        Returns:
            File path to generated MP3, or None if TTS is disabled.
        """
        if not self.enabled:
            return None

        voice = VOICE_MAP.get(role, VOICE_MAP["A"])
        edge_tts = self._get_edge_tts()

        # Generate deterministic filename from content hash
        content_hash = hashlib.md5(text.encode()).hexdigest()[:12]
        filename = f"{role}_{content_hash}.mp3"
        filepath = self.audio_dir / filename

        if filepath.exists():
            return str(filepath)

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(filepath))
            logger.info("TTS generated: %s (%d chars)", filename, len(text))
            return str(filepath)
        except Exception:
            logger.exception("TTS generation failed for role %s", role)
            return None

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable TTS."""
        self.enabled = enabled
