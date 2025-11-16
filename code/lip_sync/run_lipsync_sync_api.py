# code/lip_sync/run_lipsync_sync_api.py

from __future__ import annotations

import argparse
import os
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

from sync import Sync  # pip install syncsdk
from sync.common import Audio, GenerationOptions, Video
from sync.core.api_error import ApiError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Call sync.so (Wav2Lip commercial) API to lipsync a video "
            "with a target audio track using public URLs."
        )
    )
    parser.add_argument(
        "--video_url",
        required=True,
        help="Public URL to the source video "
             "(e.g. https://.../Tanzania_de_final.mp4).",
    )
    parser.add_argument(
        "--audio_url",
        required=True,
        help="Public URL to the target audio "
             "(e.g. https://.../Tanzania_de_aligned_v2.wav).",
    )
    parser.add_argument(
        "--output_name",
        default="heygen_lipsync_demo",
        help="Output file name prefix on sync.so side (no extension).",
    )
    parser.add_argument(
        "--model",
        default="lipsync-2",
        help='Lipsync model name, e.g. "lipsync-2" or "lipsync-1.9.0-beta".',
    )
    parser.add_argument(
        "--sync_mode",
        default="cut_off",
        help='Sync mode option, e.g. "cut_off" (see sync.so docs).',
    )
    parser.add_argument(
        "--api_key",
        default=None,
        help="Sync API key. If not provided, falls back to SYNC_API_KEY env var.",
    )
    parser.add_argument(
        "--poll_interval",
        type=float,
        default=10.0,
        help="Polling interval in seconds when checking job status.",
    )
    parser.add_argument(
        "--output_dir",
        default="data/output/video",
        help="Directory to save the downloaded lip-synced video.",
    )
    return parser.parse_args()


def download_video(url: str, output_path: Path) -> None:
    """Download video from URL to local file."""
    print(f"[INFO] Downloading video from {url} to {output_path}...")
    
    # Create output directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Download the file
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Write to file
    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"[DONE] Video downloaded successfully to {output_path}")


def main() -> None:
    # Load environment variables from .env file
    load_dotenv()

    args = parse_args()

    api_key = args.api_key or os.getenv("SYNC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "No Sync API key provided. "
            "Please pass --api_key or set SYNC_API_KEY environment variable in .env file."
        )

    video_url = args.video_url
    audio_url = args.audio_url

    client = Sync(
        base_url="https://api.sync.so",
        api_key=api_key,
    ).generations

    print("[INFO] Submitting lipsync generation job (URLs)...")
    try:
        response = client.create(
            input=[
                Video(url=video_url),
                Audio(url=audio_url),
            ],
            model=args.model,
            options=GenerationOptions(sync_mode=args.sync_mode),
            output_file_name=args.output_name,
        )
    except ApiError as e:
        print(
            f"[ERROR] create() failed with status={e.status_code}, "
            f"body={e.body}"
        )
        return

    job_id = response.id
    print(f"[INFO] Generation submitted successfully, job id: {job_id}")

    status = None
    generation = None
    while status not in ("COMPLETED", "FAILED", "REJECTED"):
        print(f"[INFO] Polling status for generation {job_id} ...")
        time.sleep(args.poll_interval)
        try:
            generation = client.get(job_id)
            status = generation.status
            print(f"[INFO] Current status: {status}")
        except ApiError as e:
            print(
                f"[ERROR] get() failed with status={e.status_code}, "
                f"body={e.body}"
            )
            status = "FAILED"
            break

    if status == "COMPLETED":
        output_url = getattr(generation, "output_url", None)
        print("[SUCCESS] Lipsync generation completed.")
        print(f"[INFO] Output URL: {output_url}")
        
        # Download the generated video
        if output_url:
            output_path = Path(args.output_dir) / f"{args.output_name}_lip_sync.mp4"
            try:
                download_video(output_url, output_path)
            except Exception as e:
                print(f"[ERROR] Failed to download video: {e}")
    else:
        print(f"[ERROR] Lipsync generation {job_id} failed with status={status}.")


if __name__ == "__main__":
    main()



'''
python -m code.lip_sync.run_lipsync_sync_api \
  --video_url "https://raw.githubusercontent.com/RainJamesY/Video_translation/main/data/output/video/Tanzania_de_final_trim.mp4" \
  --audio_url "https://raw.githubusercontent.com/RainJamesY/Video_translation/main/data/output/audio/de_aligned/Tanzania_de_aligned_trim.wav" \
  --output_name "Tanzania_de_lipsynced_trim" \
  --model "lipsync-2"
'''