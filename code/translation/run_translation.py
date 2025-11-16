# code/run_translation.py

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv  # added

import srt

from .translation_api import (
    TranslatorAPI,
    save_translations_jsonl,
)
from .subtitle_parser import load_subtitles


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run EN->DE translation on an SRT file using Gemini."
    )
    parser.add_argument(
        "--subs",
        required=True,
        help="Path to input subtitle file in SRT format (e.g. data/input/sample.srt)",
    )
    parser.add_argument(
        "--out_dir",
        default=None,
        help="Directory to store outputs (JSONL + translated SRT). "
             "Default: same directory as the input SRT.",
    )
    parser.add_argument(
        "--target_lang",
        default="de",
        help="Target language code (default: de).",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.5-flash",
        help="Gemini model name (default: gemini-2.5-flash).",
    )
    return parser.parse_args()


def segments_to_srt(
    segments: List[Dict[str, Any]],
    text_key: str = "text_de",
) -> str:
    """
    Convert translated segments back to SRT format.

    Assumes each segment dict has:
      - index (int)
      - start (timedelta)
      - end (timedelta)
      - text_de (or other field given by text_key)
    """
    srt_segments: List[srt.Subtitle] = []
    for seg in segments:
        content = seg.get(text_key, "") or ""
        srt_segments.append(
            srt.Subtitle(
                index=seg.get("index", 0),
                start=seg["start"],
                end=seg["end"],
                content=content,
            )
        )
    return srt.compose(srt_segments)


def main() -> None:
    args = parse_args()

    subs_path = Path(args.subs)
    if not subs_path.exists():
        raise FileNotFoundError(f"SRT file not found: {subs_path}")

    # Output directory: default to the same directory as the input
    if args.out_dir is None:
        out_dir = subs_path.parent
    else:
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

    # Get API key from environment variables
    api_key = (
        os.getenv("TRANSLATE_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or ""
    )
    if not api_key:
        raise RuntimeError(
            "No translation API key found. Please set TRANSLATE_API_KEY or GOOGLE_API_KEY."
        )

    print(f"[INFO] Loading subtitles from: {subs_path}")
    segments = load_subtitles(subs_path)
    print(f"[INFO] Loaded {len(segments)} segments.")

    translator = TranslatorAPI(
        api_key=api_key,
        model_name=args.model,
    )

    print(f"[INFO] Translating EN -> {args.target_lang} using {args.model} ...")
    translator.translate_segments(
        segments,
        src="en",
        tgt=args.target_lang,
        text_key="text_en",
        out_key="text_de",
    )

    # Save JSONL cache
    jsonl_path = out_dir / f"{subs_path.stem}_translations_{args.target_lang}.jsonl"
    save_translations_jsonl(segments, jsonl_path)
    print(f"[INFO] Saved translations JSONL to: {jsonl_path}")

    # Export new SRT (German)
    srt_out_path = out_dir / f"{subs_path.stem}_{args.target_lang}.srt"
    srt_text = segments_to_srt(segments, text_key="text_de")
    with srt_out_path.open("w", encoding="utf-8") as f:
        f.write(srt_text)
    print(f"[INFO] Saved translated SRT to: {srt_out_path}")

    # Print the first few entries to see the results
    print("\n[Preview] First 5 segments (EN -> DE):\n")
    for seg in segments[:5]:
        print(f"[{seg['index']}]")
        print(f"EN: {seg['text_en']}")
        print(f"DE: {seg['text_de']}")
        print("-" * 40)


if __name__ == "__main__":
    load_dotenv()
    print(f"GOOGLE_API_KEY = {os.getenv('GOOGLE_API_KEY')}")
    main()


'''
python -m code.translation.run_translation \
  --subs data/input/Tanzania-caption.srt \
  --out_dir data/output/caption_de
'''