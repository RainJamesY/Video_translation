# code/run_clone_voice.py

from __future__ import annotations

import argparse
import os
from io import BytesIO
from pathlib import Path

from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone a voice with ElevenLabs Instant Voice Cloning and print voice_id."
    )
    parser.add_argument(
        "--ref",
        required=True,
        help="Path to speaker reference audio file (e.g. data/output/speaker_ref.wav)",
    )
    parser.add_argument(
        "--name",
        default="heygen_takehome_speaker",
        help="Name for the cloned voice in ElevenLabs.",
    )
    parser.add_argument(
        "--out",
        default=None,
        help=(
            "Optional path to save the voice_id "
            "(default: <ref_stem>_voice_id.txt in the same folder)."
        ),
    )
    return parser.parse_args()


def main() -> None:
    # 1) Read .env file to get API key
    load_dotenv()
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ELEVENLABS_API_KEY is not set. Please add it to your .env or export it."
        )

    args = parse_args()
    ref_path = Path(args.ref)
    if not ref_path.exists():
        raise FileNotFoundError(f"Speaker reference file not found: {ref_path}")

    # 2) Initialize ElevenLabs client
    client = ElevenLabs(api_key=api_key)

    # 3) Read reference audio as BytesIO (recommended approach from official cookbook)
    with ref_path.open("rb") as f:
        audio_bytes = BytesIO(f.read())

    print(f"[INFO] Creating Instant Voice Clone from: {ref_path}")
    voice = client.voices.ivc.create(
        name=args.name,
        files=[audio_bytes],  # Can pass multiple files, using one combined speaker_ref for now
    )

    voice_id = voice.voice_id
    print("\n[RESULT] New cloned voice created.")
    print(f"Name     : {args.name}")
    print(f"Voice ID : {voice_id}")

    # 4) Save voice_id to txt file
    if args.out is None:
        out_path = ref_path.with_name(f"{ref_path.stem}_voice_id.txt")
    else:
        out_path = Path(args.out)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(voice_id, encoding="utf-8")
    print(f"[INFO] Saved voice_id to: {out_path}")


if __name__ == "__main__":
    main()

'''
python -m code.voice_clone.run_clone_voice \
  --ref data/output/audio/speaker_ref/speaker_ref.wav \
  --name "heygen_takehome_speaker"

'''