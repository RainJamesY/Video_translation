# code/run_tts_segments.py

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv

from code.tts.tts_api import ElevenLabsTTS


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate per-segment TTS audio files from a translations JSONL file using ElevenLabs."
    )
    parser.add_argument(
        "--jsonl",
        required=True,
        help="Path to translations JSONL file (e.g. data/output/caption_de/Tanzania-caption_translations_de.jsonl)",
    )
    parser.add_argument(
        "--out_dir",
        required=True,
        help="Directory to save per-segment audio files (mp3).",
    )
    parser.add_argument(
        "--max_segments",
        type=int,
        default=None,
        help="Optional: limit number of segments for debugging.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="If set, re-generate audio even if the mp3 file already exists.",
    )
    return parser.parse_args()


def load_translations_jsonl(path: Path) -> List[Dict[str, Any]]:
    segments: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            segments.append(obj)
    return segments


def main() -> None:
    load_dotenv()

    args = parse_args()
    jsonl_path = Path(args.jsonl)
    out_dir = Path(args.out_dir)

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL file not found: {jsonl_path}")

    api_key = os.getenv("ELEVENLABS_API_KEY", "")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set.")
    if not voice_id:
        raise RuntimeError("ELEVENLABS_VOICE_ID is not set.")

    tts = ElevenLabsTTS(
        api_key=api_key,
        voice_id=voice_id,
        base_url="https://api.elevenlabs.io",
        model_id="eleven_multilingual_v2",
    )

    print(f"[INFO] Loading translations from: {jsonl_path}")
    segments = load_translations_jsonl(jsonl_path)
    total = len(segments)
    print(f"[INFO] Loaded {total} segments.")

    if args.max_segments is not None:
        segments = segments[: args.max_segments]
        print(f"[INFO] Truncated to first {len(segments)} segments for this run.")

    out_dir.mkdir(parents=True, exist_ok=True)

    for i, seg in enumerate(segments, start=1):
        idx = seg.get("index", i)
        text_de = seg.get("text_de", "") or seg.get("text", "")

        out_path = out_dir / f"seg_{idx:04d}.mp3"
        if out_path.exists() and not args.overwrite:
            print(f"[SKIP] seg {idx:04d} already exists: {out_path}")
            continue

        print(f"[TTS ] ({i}/{len(segments)}) idx={idx} -> {out_path.name}")
        try:
            tts.synthesize_to_file(text_de, out_path)
        except Exception as e:
            print(f"[ERROR] Failed to synthesize idx={idx}: {e}")

    print("\n[DONE] TTS generation finished.")


if __name__ == "__main__":
    main()

'''
python -m code.tts.run_tts_segments \
  --jsonl data/output/caption_de/Tanzania-caption_translations_de.jsonl \
  --out_dir data/output/audio/de_segments \
'''