# code/translation_api.py

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import List, Dict, Any

from google import genai  # pip install google-genai


@dataclass
class TranslatorConfig:
    api_key: str
    model_name: str = "gemini-2.5-flash"


class TranslatorAPI:
    """
    Thin wrapper around Gemini's generate_content for EN -> DE translation.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        if not api_key:
            raise ValueError("Translation API key is empty. Please set TRANSLATE_API_KEY / GOOGLE_API_KEY.")

        # Gemini SDK defaults to using GOOGLE_API_KEY environment variable, ensuring it's set here
        os.environ.setdefault("GOOGLE_API_KEY", api_key)

        self.api_key = api_key
        self.model_name = model_name or "gemini-2.5-flash"

        # Explicitly pass api_key for clarity
        self.client = genai.Client(api_key=self.api_key)

    def translate(self, text: str, src: str = "en", tgt: str = "de") -> str:
        """
        Translate a single string using Gemini. Returns target-language text only.
        """
        if not text.strip():
            return ""

        # Prompt: strongly constrain to return only the translation, avoid explanations
        prompt = (
            f"Translate the following {src.upper()} text to {tgt.upper()}.\n"
            f"Return ONLY the translated text, without quotes or any explanation.\n\n"
            f"{text}"
        )

        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )

        # resp.text is the simplified usage from official examples
        return (resp.text or "").strip()

    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        src: str = "en",
        tgt: str = "de",
        text_key: str = "text_en",
        out_key: str = "text_de",
    ) -> List[Dict[str, Any]]:
        """
        In-place translate a list of subtitle segments.

        segments: list of dicts from subtitle_parser.load_subtitles
        Each segment must contain `text_en` (by default).
        After calling, each segment will also have `text_de`.
        """
        for seg in segments:
            text = seg.get(text_key, "") or ""
            seg[out_key] = self.translate(text, src=src, tgt=tgt)
        return segments


# ---------- JSON/JSONL helpers for caching translations ----------

def _segment_to_serializable(seg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a segment dict (with timedelta) to JSON-serializable form.
    Keeps both EN and DE texts if present.
    """
    start = seg.get("start")
    end = seg.get("end")

    def _to_seconds(x):
        if isinstance(x, timedelta):
            return x.total_seconds()
        return x

    return {
        "index": seg.get("index"),
        "start_sec": _to_seconds(start),
        "end_sec": _to_seconds(end),
        "text_en": seg.get("text_en", ""),
        "text_de": seg.get("text_de", ""),
    }


def save_translations_jsonl(
    segments: List[Dict[str, Any]],
    path: Path,
) -> Path:
    """
    Save translated segments to JSONL file, one segment per line.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for seg in segments:
            obj = _segment_to_serializable(seg)
            line = json.dumps(obj, ensure_ascii=False)
            f.write(line + "\n")
    return path


def load_translations_jsonl(path: Path) -> List[Dict[str, Any]]:
    """
    Load segments from JSONL file. This returns a list of dicts with
    start/end in seconds; you can merge these into your subtitle segments
    by index if needed.
    """
    segments: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            segments.append(obj)
    return segments
