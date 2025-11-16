# code/utils/trim_last_seconds.py

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trim the last N seconds from an audio/video file using ffmpeg."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Input media file path (audio or video).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output media file path.",
    )
    parser.add_argument(
        "--trim_sec",
        type=float,
        default=1.0,
        help="How many seconds to trim from the end (default: 1.0).",
    )
    return parser.parse_args()


def get_duration_seconds(path: Path) -> float:
    """Use ffprobe to get media duration in seconds."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    out = subprocess.check_output(cmd, text=True).strip()
    return float(out)


def run_ffmpeg_trim(input_path: Path, output_path: Path, new_duration: float) -> None:
    """Call ffmpeg to trim media to new_duration seconds (copy codecs)."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-t",
        f"{new_duration:.3f}",
        "-c",
        "copy",
        str(output_path),
    ]
    print("[INFO] Running:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with return code {proc.returncode}")


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    duration = get_duration_seconds(input_path)
    print(f"[INFO] Original duration: {duration:.3f} s")

    new_duration = duration - args.trim_sec
    if new_duration <= 0:
        raise ValueError(
            f"Requested trim_sec={args.trim_sec} is too large for file duration={duration:.3f}s"
        )

    print(f"[INFO] Target duration after trimming: {new_duration:.3f} s")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg_trim(input_path, output_path, new_duration)
    print(f"[DONE] Saved trimmed file to: {output_path}")


if __name__ == "__main__":
    main()

'''
# trim audio
python -m code.utils.trim_last_seconds \
  --input  data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav \
  --output data/output/audio/de_aligned/Tanzania_de_aligned_trim.wav \
  --trim_sec 0.8

# trim video
python -m code.utils.trim_last_seconds \
  --input  data/output/video/Tanzania_de_final.mp4 \
  --output data/output/video/Tanzania_de_final_trim.mp4 \
  --trim_sec 0.8

'''