# code/run_extract_speaker_ref.py

from __future__ import annotations

import argparse
from pathlib import Path

from code.subtitle_parser import load_subtitles
from code.utils.video_utils import extract_audio
from code.utils.audio_utils import extract_speaker_segments_from_audio


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract speaker reference audio segments from video and SRT."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to input video file (e.g. data/input/sample.mp4)",
    )
    parser.add_argument(
        "--subs",
        required=True,
        help="Path to input subtitle file in SRT format (e.g. data/input/sample.srt)",
    )
    parser.add_argument(
        "--out_dir",
        default="data/output",
        help="Directory to store extracted audio and speaker reference files.",
    )
    parser.add_argument(
        "--num_segments",
        type=int,
        default=3,
        help="Number of subtitle segments to use as speaker reference (>=2 recommended).",
    )
    parser.add_argument(
        "--min_duration",
        type=float,
        default=1.0,
        help="Minimum duration (in seconds) for a segment to be considered.",
    )
    parser.add_argument(
        "--sample_rate",
        type=int,
        default=16000,
        help="Sample rate for extracted audio (default: 16000).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    video_path = Path(args.video)
    subs_path = Path(args.subs)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not subs_path.exists():
        raise FileNotFoundError(f"SRT file not found: {subs_path}")

    # 1) Extract the full audio from video
    audio_path = out_dir / f"{video_path.stem}_en.wav"
    print(f"[INFO] Extracting audio from {video_path} -> {audio_path}")
    extract_audio(
        video_path=video_path,
        audio_path=audio_path,
        sample_rate=args.sample_rate,
    )

    # 2) Load SRT subtitles
    print(f"[INFO] Loading subtitles from {subs_path}")
    segments = load_subtitles(subs_path)
    print(f"[INFO] Loaded {len(segments)} subtitle segments.")

    # 3) Extract audio segments based on SRT timestamps for speaker reference
    print(
        f"[INFO] Selecting up to {args.num_segments} segments "
        f"(min duration {args.min_duration}s) for speaker reference."
    )
    seg_paths, speaker_ref_path = extract_speaker_segments_from_audio(
        audio_path=audio_path,
        segments=segments,
        out_dir=out_dir,
        num_segments=args.num_segments,
        min_duration=args.min_duration,
    )

    print("\n[RESULT] Extracted speaker reference segments:")
    for p in seg_paths:
        print(f" - {p}")

    print(f"\n[RESULT] Combined speaker reference written to: {speaker_ref_path}")


if __name__ == "__main__":
    main()



'''
python -m code.voice_clone.run_extract_speaker_ref \
  --video data/input/Tanzania-2.mp4 \
  --subs data/input/Tanzania-caption.srt \
  --out_dir data/output/audio/speaker_ref \
  --num_segments 3 \
  --min_duration 1.0
'''