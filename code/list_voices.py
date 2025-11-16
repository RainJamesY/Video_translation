# code/list_voices.py

from __future__ import annotations

import argparse
import os
from pathlib import Path

import requests
from dotenv import load_dotenv


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List available ElevenLabs voices and their voice_id."
    )
    parser.add_argument(
        "--search",
        default=None,
        help="Optional search term to filter voices by name/description.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of voices to show (client-side trim).",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv()

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set. Please add it to your .env or export it."
        )

    args = parse_args()

    # v2 voices search/list endpoint
    url = "https://api.elevenlabs.io/v2/voices"
    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key,
    }

    params = {}
    if args.search:
        params["search"] = args.search

    print(f"[INFO] Requesting voices from {url} ...")
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # 官方返回结构里有一个 'voices' 列表
    voices = data.get("voices", [])
    print(f"[INFO] Total voices returned by API: {len(voices)}")

    if not voices:
        print("[WARN] No voices available. Check if your API key is correct / has any voices.")
        return

    print("\n[Index]  Name                             | Voice ID                          | Category      | Lang")
    print("-" * 100)

    for idx, v in enumerate(voices[: args.limit], start=1):
        name = v.get("name", "")
        voice_id = v.get("voice_id", "")
        category = v.get("category", "") or "-"
        # v2 里通常会有 languages 或 language 字段，这里做个兼容
        langs = v.get("languages") or v.get("language") or []
        if isinstance(langs, list):
            lang_str = ",".join(str(x) for x in langs)
        else:
            lang_str = str(langs)

        print(f"[{idx:02d}] {name:<32} | {voice_id:<32} | {category:<12} | {lang_str}")


if __name__ == "__main__":
    main()

'''
python -m code.list_voices
'''