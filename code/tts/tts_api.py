# code/tts_api.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import requests


class ElevenLabsTTS:
    """
    Minimal wrapper around ElevenLabs text-to-speech API.

    Currently only responsible for:
      - Synthesizing speech with a fixed voice_id
      - Writing the result to an mp3 file

    Duration alignment, concatenation, and other logic are left to the higher-level code.
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str,
        base_url: str = "https://api.elevenlabs.io",
        model_id: str = "eleven_multilingual_v2",
    ) -> None:
        if not api_key:
            raise ValueError("ELEVENLABS_API_KEY is empty.")
        if not voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID is empty.")

        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = base_url.rstrip("/")
        self.model_id = model_id

    def synthesize_to_file(
        self,
        text: str,
        out_path: Path,
        stability: float = 0.6,
        similarity_boost: float = 0.85,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ) -> Path:
        """
        Call ElevenLabs TTS with the current voice_id and text, saving the audio to out_path (mp3).

        Returns:
            out_path
        """
        text = (text or "").strip()
        if not text:
            # For empty text, write an empty file to maintain consistent handling in higher-level logic
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(b"")
            return out_path

        url = f"{self.base_url}/v1/text-to-speech/{self.voice_id}"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            # Tell the server we expect mp3 (default is usually mp3, but this is more explicit)
            "Accept": "audio/mpeg",
        }

        body = {
            "text": text,
            "model_id": self.model_id,  # Multilingual model, automatically speaks German for German text
            "voice_settings": {
                "stability": stability,
                "similarity_boost": similarity_boost,
                "style": style,
                "use_speaker_boost": use_speaker_boost,
            },
        }

        resp = requests.post(url, headers=headers, json=body, timeout=60)
        resp.raise_for_status()

        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("wb") as f:
            f.write(resp.content)

        return out_path
