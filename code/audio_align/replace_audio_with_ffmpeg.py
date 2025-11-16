# code/replace_audio_with_ffmpeg.py

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Replace the audio track of a video with a new audio file using ffmpeg."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to the original input video file (e.g. data/input/Tanzania.mp4).",
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to the new audio file (e.g. data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav).",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to the output video file (e.g. data/output/video/Tanzania_de_final.mp4).",
    )
    parser.add_argument(
        "--keep-original-audio",
        action="store_true",
        help=(
            "If set, keep the original audio as a second track instead of fully replacing it.\n"
            "Track 0 = new audio, Track 1 = original audio."
        ),
    )
    return parser.parse_args()


def run_ffmpeg(cmd: list[str]) -> None:
    print("[INFO] Running ffmpeg command:")
    print("       " + " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    # 打印一下 ffmpeg 输出（调试用）
    print(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed with return code {proc.returncode}")


def main() -> None:
    args = parse_args()

    video_path = Path(args.video)
    audio_path = Path(args.audio)
    out_path = Path(args.out)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.keep_original_audio:
        # 保留原音轨：输出里有两条 audio track
        # 0:v:0 = 原视频画面
        # 1:a:0 = 新德语音轨
        # 0:a:0 = 原音频，作为第二条音轨
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            # 映射：视频 + 新音频 + 原音频
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-map", "0:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(out_path),
        ]
    else:
        # 完全替换音轨，只保留新德语音轨
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(out_path),
        ]

    run_ffmpeg(cmd)
    print(f"[DONE] Saved video with replaced audio to: {out_path}")


if __name__ == "__main__":
    main()

'''
python -m code.audio_align.replace_audio_with_ffmpeg \
  --video data/input/Tanzania-2.mp4 \
  --audio data/output/audio/de_aligned/Tanzania_de_aligned_v2.wav \
  --out data/output/video/Tanzania_de_final.mp4

'''